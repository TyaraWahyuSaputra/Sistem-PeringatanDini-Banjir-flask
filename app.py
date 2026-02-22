from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory, flash
from config import Config
import os
import time
from datetime import datetime
import sys
import traceback
import sqlite3
import json
import secrets
import pytz

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ==================== IMPORT WIB HELPER ====================
from utils.wib_helper import get_wib_now, format_wib_datetime, format_wib_datetime_full

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']

# Import controllers
from controllers.flood_report_controller import FloodReportController
from controllers.realtime_data_controller import RealTimeDataController
# Import prediction models
from utils.model_ann import predict_flood_ann_with_temp_range
from utils.gumbel_distribution import predict_flood_gumbel
# Import geocoding helper
from utils.helpers import OSMGeocoder

# Initialize controllers
flood_controller = FloodReportController()
realtime_controller = RealTimeDataController()

# ==================== CONTEXT PROCESSOR FOR WIB ====================

@app.context_processor
def inject_wib_now():
    """Inject WIB datetime ke semua template"""
    return {
        'now': get_wib_now(),
        'format_wib': format_wib_datetime,
        'format_wib_full': format_wib_datetime_full
    }

# ==================== TEMPLATE FILTERS ====================

@app.template_filter('format_date')
def format_date_filter(date_str):
    """Format date string untuk tampilan yang lebih baik"""
    if not date_str:
        return 'N/A'
    
    try:
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']:
            try:
                from datetime import datetime as dt
                parsed_date = dt.strptime(str(date_str), fmt)
                months_id = [
                    '', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
                    'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
                ]
                return f"{parsed_date.day} {months_id[parsed_date.month]} {parsed_date.year}"
            except ValueError:
                continue
        return str(date_str)
    except:
        return str(date_str)

# ==================== GLOBAL ERROR HANDLER ====================

@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler"""
    app.logger.error(f"Unhandled exception: {str(e)}")
    app.logger.error(traceback.format_exc())
    
    if request.path.startswith('/api/'):
        return jsonify({
            'success': False,
            'message': 'Internal server error',
            'error': str(e) if app.debug else 'An error occurred'
        }), 500
    
    flash(f"Terjadi kesalahan sistem: {str(e)}", 'error')
    return render_template('500.html', page_title='Kesalahan Server'), 500

# ==================== ROUTES ====================

@app.route('/')
def landing():
    try:
        return render_template('landing.html', 
                            page_title='Sistem Peringatan Dini Banjir', 
                            now=get_wib_now())
    except Exception as e:
        app.logger.error(f"Error in landing route: {e}")
        return render_template('500.html', page_title='Kesalahan Server')

@app.route('/index')
def index():
    try:
        return render_template('index.html', 
                            page_title='Dashboard', 
                            now=get_wib_now())
    except Exception as e:
        app.logger.error(f"Error in index route: {e}")
        return render_template('500.html', page_title='Kesalahan Server')

@app.route('/panduan')
def panduan():
    try:
        return render_template('panduan.html', 
                            page_title='Panduan', 
                            now=get_wib_now())
    except Exception as e:
        app.logger.error(f"Error in panduan route: {e}")
        flash(f"Terjadi kesalahan: {str(e)}", 'error')
        return redirect(url_for('index'))

@app.route('/lapor-banjir', methods=['GET', 'POST'])
def lapor_banjir():
    """Flood report form - dengan auto geocoding dan retry"""
    if request.method == 'POST':
        try:
            # STEP 1: CHECK SUBMISSION TOKEN
            form_token = request.form.get('form_token', '')
            session_token = session.get('form_token', '')
            
            if not form_token or form_token != session_token:
                app.logger.warning(f"Invalid or reused form token detected")
                flash("Laporan sudah dikirim atau token tidak valid. Silakan isi form baru.", 'warning')
                session['form_token'] = secrets.token_hex(16)
                return redirect(url_for('lapor_banjir'))
            
            # STEP 2: INVALIDATE TOKEN
            session.pop('form_token', None)
            
            # Get form data
            address = request.form.get('address', '').strip()
            flood_height = request.form.get('flood_height', '').strip()
            reporter_name = request.form.get('reporter_name', '').strip()
            reporter_phone = request.form.get('reporter_phone', '').strip()
            photo = request.files.get('photo')
            
            # Validate required fields
            errors = []
            if not address:
                errors.append("Alamat harus diisi")
            if not flood_height or flood_height == 'Pilih tinggi banjir':
                errors.append("Tinggi banjir harus dipilih")
            if not reporter_name:
                errors.append("Nama pelapor harus diisi")
            if not photo or photo.filename == '':
                errors.append("Foto harus diunggah")
            
            if errors:
                for error in errors:
                    flash(error, 'error')
                session['form_token'] = secrets.token_hex(16)
                return redirect(url_for('lapor_banjir'))
            
            # Validate file size
            photo.seek(0, os.SEEK_END)
            file_size = photo.tell()
            photo.seek(0)
            
            if file_size > app.config['MAX_CONTENT_LENGTH']:
                flash("Ukuran file terlalu besar. Maksimum 5MB", 'error')
                session['form_token'] = secrets.token_hex(16)
                return redirect(url_for('lapor_banjir'))
            
            # Validate file extension
            allowed_extensions = app.config['ALLOWED_EXTENSIONS']
            if '.' not in photo.filename or \
            photo.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
                flash("Format file tidak didukung. Gunakan JPG, PNG, atau GIF", 'error')
                session['form_token'] = secrets.token_hex(16)
                return redirect(url_for('lapor_banjir'))
            
            # ==================== AUTO GEOCODING ====================
            latitude = None
            longitude = None
            geocode_success = False
            geocode_confidence = None
            
            try:
                app.logger.info(f"Starting auto-geocoding for address: {address}")
                geocoder = OSMGeocoder(
                    user_agent=app.config.get('OSM_USER_AGENT', 'FloodReportSystem/1.0'),
                    base_url=app.config.get('OSM_BASE_URL', 'https://nominatim.openstreetmap.org')
                )
                
                # Attempt 1
                lat, lng, error = geocoder.geocode_address(address, lang="id")
                
                # Kalau gagal, retry sekali setelah jeda 2 detik
                if not lat or not lng:
                    app.logger.warning(f"Geocoding attempt 1 failed: {error}. Retrying...")
                    time.sleep(2)
                    lat, lng, error = geocoder.geocode_address(address, lang="id")
                
                if lat and lng:
                    latitude = lat
                    longitude = lng
                    geocode_success = True
                    geocode_confidence = 'HIGH'
                    app.logger.info(f"✅ Geocoding SUCCESS: ({lat:.6f}, {lng:.6f})")
                else:
                    app.logger.warning(f"⚠️ Geocoding failed after retry: {error}")
                    
            except Exception as e:
                app.logger.error(f"❌ Geocoding ERROR: {str(e)}")
                # Lanjutkan proses - geocoding gagal tidak boleh memblokir pengiriman laporan
            
            # ==================== END AUTO GEOCODING ====================
            
            # Prepare data
            data = {
                'address': address,
                'flood_height': flood_height,
                'reporter_name': reporter_name,
                'reporter_phone': reporter_phone,
                'photo': photo,
                'latitude': latitude,
                'longitude': longitude,
                'is_geocoded': 1 if geocode_success else 0,
                'geocode_confidence': geocode_confidence
            }
            
            # Submit report
            success, message = flood_controller.submit_report(data)
            app.logger.info(f"Report submission - success: {success}, message: {message}")
            
            # ==================== FLASH MESSAGES ====================
            if success:
                if geocode_success and latitude and longitude:
                    flash(f'✅ Laporan berhasil dikirim dan lokasi berhasil dipetakan!', 'success')
                    flash(f'📍 Koordinat: {latitude:.6f}, {longitude:.6f}', 'info')
                    flash(f'🗺️ <a href="/peta" class="alert-link"><strong>Klik di sini untuk melihat lokasi di Peta Banjir →</strong></a>', 'info')
                else:
                    flash(f'✅ Laporan berhasil dikirim!', 'success')
                    flash(f'⚠️ Lokasi belum dapat dipetakan secara otomatis', 'warning')
                    flash(f'📝 Alamat Anda: {address}', 'info')
                    flash(f'ℹ️ Tim kami akan memverifikasi lokasi secara manual', 'info')
            else:
                flash(message, 'error')
            # ==================== END FLASH MESSAGES ====================
            
            # STEP 3: REDIRECT (PRG Pattern)
            session['form_token'] = secrets.token_hex(16)
            return redirect(url_for('lapor_banjir'))
                
        except Exception as e:
            app.logger.error(f"Error in lapor_banjir: {str(e)}")
            app.logger.error(traceback.format_exc())
            flash(f"Terjadi kesalahan sistem: {str(e)}", 'error')
            session['form_token'] = secrets.token_hex(16)
            return redirect(url_for('lapor_banjir'))
    
    # GET request
    session['form_token'] = secrets.token_hex(16)
    return render_template('lapor_banjir.html', 
                        page_title='Lapor Banjir', 
                        now=get_wib_now(),
                        form_token=session['form_token'])


@app.route('/catatan-laporan')
def catatan_laporan():
    try:
        return render_template('catatan_laporan.html', 
                            page_title='Catatan Laporan', 
                            now=get_wib_now())
    except Exception as e:
        app.logger.error(f"Error in catatan_laporan: {e}")
        app.logger.error(traceback.format_exc())
        flash(f"Terjadi kesalahan: {str(e)}", 'error')
        return redirect(url_for('index'))

@app.route('/laporan/harian')
def laporan_harian():
    try:
        daily_reports = flood_controller.get_today_reports_combined()
        stats = flood_controller.flood_model.get_report_statistics()
        app.logger.info(f"Daily reports loaded: {len(daily_reports)} reports")
        return render_template('harian.html',
                            page_title='Laporan Harian',
                            reports=daily_reports,
                            stats=stats,
                            now=get_wib_now())
    except Exception as e:
        app.logger.error(f"Error in laporan_harian: {e}")
        app.logger.error(traceback.format_exc())
        flash(f"Terjadi kesalahan: {str(e)}", 'error')
        return redirect(url_for('catatan_laporan'))

@app.route('/laporan/bulanan')
def laporan_bulanan():
    try:
        all_reports = flood_controller.get_month_reports_combined()
        yearly_stats = flood_controller.get_monthly_statistics()
        
        tz = pytz.timezone('Asia/Jakarta')
        now = get_wib_now()
        current_month = now.strftime('%Y-%m')
        
        monthly_reports = [r for r in all_reports if r.get('month_year') == current_month]

        available_months = sorted(set(
            r.get('month_year') for r in all_reports if r.get('month_year')
        ), reverse=True)

        displayed_month = current_month
        if not monthly_reports and available_months:
            displayed_month = available_months[0]
            monthly_reports = [r for r in all_reports if r.get('month_year') == displayed_month]

        months_id = [
            '', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
            'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
        ]

        try:
            d_year, d_month = displayed_month.split('-')
            displayed_month_name = f"{months_id[int(d_month)]} {d_year}"
        except:
            displayed_month_name = months_id[now.month] + ' ' + str(now.year)

        current_month_name = displayed_month_name
        
        app.logger.info(f"Monthly analysis loaded: {len(all_reports)} total reports, {len(monthly_reports)} this month")
        
        return render_template('bulanan.html',
                            page_title='Laporan Bulanan',
                            monthly_reports=monthly_reports,
                            all_reports=all_reports,
                            yearly_stats=yearly_stats,
                            current_month=now.month,
                            current_month_name=current_month_name,
                            available_months=available_months,
                            displayed_month=displayed_month,
                            now=now)
    except Exception as e:
        app.logger.error(f"Error in laporan_bulanan: {e}")
        app.logger.error(traceback.format_exc())
        flash(f"Terjadi kesalahan: {str(e)}", 'error')
        return redirect(url_for('catatan_laporan'))

@app.route('/peta')
def peta():
    try:
        app.logger.info("Loading peta page...")
        
        all_reports = flood_controller.get_all_reports_combined()
        app.logger.info(f"Total combined reports: {len(all_reports)}")
        
        geocoded_reports = [
            report for report in all_reports 
            if report.get('latitude') and report.get('longitude')
        ]
        app.logger.info(f"Geocoded reports: {len(geocoded_reports)}")
        
        for report in geocoded_reports:
            if 'month_year' not in report and report.get('report_date'):
                try:
                    report['month_year'] = report['report_date'][:7]
                except:
                    report['month_year'] = None
        
        available_months = sorted(set(
            r.get('month_year') for r in geocoded_reports if r.get('month_year')
        ), reverse=True)
        
        map_config = {
            'center_lat': Config.DEFAULT_MAP_CENTER_LAT,
            'center_lng': Config.DEFAULT_MAP_CENTER_LNG,
            'zoom': Config.DEFAULT_MAP_ZOOM,
            'tile_url': Config.MAP_TILE_URL
        }
        
        return render_template('peta.html',
                            page_title='Peta Banjir',
                            reports=geocoded_reports,
                            available_months=available_months,
                            map_config=map_config,
                            now=get_wib_now())
    except Exception as e:
        app.logger.error(f"Error in peta route: {e}")
        app.logger.error(traceback.format_exc())
        flash(f"Terjadi kesalahan saat memuat peta: {str(e)}", 'error')
        return redirect(url_for('index'))

@app.route('/data-realtime')
def data_realtime():
    try:
        locations_data = realtime_controller.get_comprehensive_data()
        overall_status, status_color = realtime_controller.get_overall_risk_status(locations_data)
        weather_forecast = realtime_controller.get_weather_forecast()
        
        return render_template('data_realtime.html',
                            page_title='Data Real-Time',
                            locations=locations_data,
                            overall_status=overall_status,
                            status_color=status_color,
                            weather_forecast=weather_forecast,
                            now=get_wib_now())
    except Exception as e:
        app.logger.error(f"Error in data_realtime route: {e}")
        app.logger.error(traceback.format_exc())
        flash(f"Terjadi kesalahan: {str(e)}", 'error')
        return redirect(url_for('index'))

# ==================== SIMULASI PAGE ====================

@app.route('/simulasi', methods=['GET', 'POST'])
def simulasi():
    result = None
    timestamp = get_wib_now().strftime('%Y-%m-%d %H:%M:%S')
    
    if request.method == 'POST':
        try:
            rainfall = float(request.form.get('rainfall', 50.0))
            water_level = float(request.form.get('water_level', 100.0))
            humidity = float(request.form.get('humidity', 70.0))
            temp_min = float(request.form.get('temp_min', 25.0))
            temp_max = float(request.form.get('temp_max', 30.0))
            
            if temp_max < temp_min:
                flash('Suhu maksimum harus lebih besar dari suhu minimum', 'error')
                return render_template('simulasi.html', 
                                    page_title='Simulasi Prediksi', 
                                    now=get_wib_now(),
                                    result=None)
            
            try:
                ann_result = predict_flood_ann_with_temp_range(
                    rainfall=rainfall,
                    water_level=water_level,
                    humidity=humidity,
                    temp_min=temp_min,
                    temp_max=temp_max
                )
            except Exception as ann_error:
                app.logger.error(f"ANN Prediction error: {ann_error}")
                ann_result = {
                    'risk_score': min(1.0, (rainfall / 500 + (water_level - 60) / 90) / 2),
                    'status': 'MENENGAH' if rainfall > 100 else 'RENDAH',
                    'message': 'Prediksi menggunakan model sederhana',
                    'features': {
                        'rainfall': rainfall,
                        'water_level': water_level,
                        'humidity': humidity,
                        'temp_min': temp_min,
                        'temp_max': temp_max
                    }
                }
            
            result = {
                'status': ann_result.get('status', 'MENENGAH'),
                'risk_score': round(ann_result.get('risk_score', 0.5), 3),
                'message': ann_result.get('message', 'Hasil prediksi berdasarkan parameter input'),
                'features': ann_result.get('features', {
                    'rainfall': rainfall,
                    'water_level': water_level,
                    'humidity': humidity,
                    'temp_min': temp_min,
                    'temp_max': temp_max
                }),
                'timestamp': timestamp
            }
            
            if result['risk_score'] < 0.3:
                result['status'] = 'RENDAH'
                result['message'] = 'Risiko banjir rendah. Kondisi normal.'
            elif result['risk_score'] < 0.6:
                result['status'] = 'MENENGAH'
                result['message'] = 'Risiko banjir sedang. Perlu waspada.'
            else:
                result['status'] = 'TINGGI'
                result['message'] = 'Risiko banjir tinggi. Segera ambil tindakan!'
            
            app.logger.info(f"Simulation completed: {result['status']} (Score: {result['risk_score']})")
            
        except ValueError as e:
            flash('Masukkan nilai numerik yang valid untuk semua parameter', 'error')
            app.logger.error(f"ValueError in simulasi: {e}")
        except Exception as e:
            flash(f'Terjadi kesalahan dalam simulasi: {str(e)}', 'error')
            app.logger.error(f"Error in simulasi route: {e}")
            app.logger.error(traceback.format_exc())
    
    return render_template('simulasi.html', 
                        page_title='Simulasi Prediksi', 
                        now=get_wib_now(),
                        result=result)

# ==================== API ENDPOINTS ====================

@app.route('/api/simulate', methods=['POST'])
def api_simulate():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        try:
            rainfall = float(data.get('rainfall', 0))
            water_level = float(data.get('water_level', 0))
            humidity = float(data.get('humidity', 75))
            temp_min = float(data.get('temp_min', 25))
            temp_max = float(data.get('temp_max', 30))
            location = data.get('location', 'Ngadipiro')
        except (ValueError, TypeError) as e:
            return jsonify({'success': False, 'message': f'Invalid parameter value: {str(e)}'}), 400
        
        try:
            ann_result = predict_flood_ann_with_temp_range(
                rainfall=rainfall, water_level=water_level,
                humidity=humidity, temp_min=temp_min, temp_max=temp_max
            )
            gumbel_result = predict_flood_gumbel(rainfall=rainfall, location=location)
        except Exception as e:
            app.logger.error(f"Prediction error: {e}")
            app.logger.error(traceback.format_exc())
            return jsonify({'success': False, 'message': 'Prediction calculation failed',
                          'error': str(e) if app.debug else None}), 500
        
        return jsonify({
            'success': True,
            'ann_prediction': ann_result,
            'gumbel_prediction': gumbel_result,
            'input_parameters': {
                'rainfall': rainfall, 'water_level': water_level,
                'humidity': humidity, 'temp_min': temp_min,
                'temp_max': temp_max, 'location': location
            },
            'timestamp': get_wib_now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        app.logger.error(f"API Error in simulate: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': 'Simulation error',
                       'error': str(e) if app.debug else 'An error occurred'}), 500


@app.route('/api/get-recent-activities')
def get_recent_activities():
    try:
        limit = request.args.get('limit', 10, type=int)
        recent_activities = flood_controller.get_recent_activities(limit=limit)
        
        formatted_activities = []
        for activity in recent_activities:
            formatted_activities.append({
                'timestamp': activity.get('Timestamp', ''),
                'address': activity.get('Alamat', ''),
                'flood_height': activity.get('Tinggi Banjir', ''),
                'reporter': activity.get('Nama Pelapor', ''),
                'status': activity.get('Status', 'pending'),
                'source': activity.get('source', 'unknown')
            })
        
        return jsonify({
            'success': True,
            'activities': formatted_activities,
            'total': len(formatted_activities),
            'last_updated': get_wib_now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        app.logger.error(f"API Error in get-recent-activities: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': 'Failed to load recent activities',
                       'error': str(e) if app.debug else None}), 500

@app.route('/api/get-all-reports')
def get_all_reports():
    try:
        all_reports = flood_controller.get_all_reports_combined()
        
        formatted_reports = []
        for report in all_reports:
            formatted_reports.append({
                'timestamp': report.get('Timestamp', ''),
                'address': report.get('Alamat', ''),
                'flood_height': report.get('Tinggi Banjir', ''),
                'reporter': report.get('Nama Pelapor', ''),
                'phone': report.get('No HP', ''),
                'status': report.get('Status', 'pending'),
                'photo_url': report.get('Photo URL', ''),
                'source': report.get('source', 'unknown'),
                'latitude': report.get('latitude'),
                'longitude': report.get('longitude')
            })
        
        return jsonify({
            'success': True,
            'reports': formatted_reports,
            'total': len(formatted_reports),
            'last_updated': get_wib_now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        app.logger.error(f"API Error in get-all-reports: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': 'Failed to load reports',
                       'error': str(e) if app.debug else None}), 500

@app.route('/api/get-daily-reports')
def get_daily_reports():
    try:
        daily_reports = flood_controller.get_today_reports_combined()
        
        total_reports = len(daily_reports)
        unique_locations = len(set(r.get('Alamat', '') for r in daily_reports))
        unique_reporters = len(set(r.get('Nama Pelapor', '') for r in daily_reports))
        
        latest_time = '--:--'
        if daily_reports:
            timestamp = daily_reports[0].get('Timestamp', '')
            if timestamp and len(timestamp) >= 16:
                latest_time = timestamp[11:16]
        
        formatted_reports = []
        for report in daily_reports:
            formatted_reports.append({
                'timestamp': report.get('Timestamp', ''),
                'address': report.get('Alamat', ''),
                'flood_height': report.get('Tinggi Banjir', ''),
                'reporter': report.get('Nama Pelapor', ''),
                'phone': report.get('No HP', ''),
                'status': report.get('Status', 'pending'),
                'photo_url': report.get('Photo URL', ''),
                'source': report.get('source', 'unknown')
            })
        
        return jsonify({
            'success': True,
            'reports': formatted_reports,
            'statistics': {
                'total_reports': total_reports,
                'unique_locations': unique_locations,
                'unique_reporters': unique_reporters,
                'latest_time': latest_time
            },
            'date': get_wib_now().strftime('%Y-%m-%d'),
            'last_updated': get_wib_now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        app.logger.error(f"API Error in get-daily-reports: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': 'Failed to load daily reports',
                       'error': str(e) if app.debug else None}), 500

@app.route('/api/get-monthly-reports')
def get_monthly_reports():
    try:
        all_reports = flood_controller.get_month_reports_combined()
        current_month = get_wib_now().strftime('%Y-%m')
        monthly_reports = [r for r in all_reports if r.get('month_year') == current_month]
        
        formatted_reports = []
        for report in monthly_reports:
            formatted_reports.append({
                'timestamp': report.get('Timestamp', ''),
                'address': report.get('Alamat', ''),
                'flood_height': report.get('Tinggi Banjir', ''),
                'reporter': report.get('Nama Pelapor', ''),
                'status': report.get('Status', 'pending'),
                'source': report.get('source', 'unknown')
            })
        
        return jsonify({
            'success': True,
            'reports': formatted_reports,
            'total': len(formatted_reports),
            'month': current_month,
            'last_updated': get_wib_now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        app.logger.error(f"API Error in get-monthly-reports: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': 'Failed to load monthly reports',
                       'error': str(e) if app.debug else None}), 500

@app.route('/api/get-12-months-stats')
def get_12_months_stats():
    try:
        conn = sqlite3.connect(app.config['DATABASE_PATH'])
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                strftime('%Y-%m', report_date) as month,
                strftime('%Y', report_date) as year,
                CAST(strftime('%m', report_date) AS INTEGER) as month_num,
                COUNT(*) as report_count,
                COUNT(DISTINCT "Alamat") as unique_locations
            FROM flood_reports 
            WHERE report_date >= date('now', '-12 months')
            GROUP BY strftime('%Y-%m', report_date)
            ORDER BY report_date DESC
        ''')
        
        monthly_data_rows = cursor.fetchall()
        monthly_data = [dict(row) for row in monthly_data_rows]
        
        months_id = [
            '', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
            'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
        ]
        
        for item in monthly_data:
            month_num = item.get('month_num', 1)
            item['month_name'] = months_id[month_num] if 1 <= month_num <= 12 else 'Unknown'
        
        if len(monthly_data) >= 2:
            recent_month = monthly_data[0]['report_count'] if monthly_data else 0
            previous_month = monthly_data[1]['report_count'] if len(monthly_data) > 1 else 0
            
            if previous_month > 0:
                trend_percent = ((recent_month - previous_month) / previous_month) * 100
            else:
                trend_percent = 0
            
            if trend_percent > 10:
                trend = "MENINGKAT"
            elif trend_percent < -10:
                trend = "MENURUN"
            else:
                trend = "STABIL"
        else:
            trend = "INSUFFICIENT_DATA"
            trend_percent = 0
        
        total_reports = sum(m['report_count'] for m in monthly_data)
        avg_monthly = total_reports / len(monthly_data) if monthly_data else 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'monthly_data': monthly_data,
            'summary': {
                'total_reports_12_months': total_reports,
                'avg_monthly_reports': round(avg_monthly, 1),
                'trend': trend,
                'trend_percent': round(trend_percent, 1),
                'data_months': len(monthly_data)
            },
            'last_updated': get_wib_now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        app.logger.error(f"API Error in get-12-months-stats: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': 'Failed to load 12-month statistics',
                       'error': str(e) if app.debug else None}), 500

@app.route('/api/get-trend-data')
def get_trend_data():
    try:
        conn = sqlite3.connect(app.config['DATABASE_PATH'])
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_reports,
                COUNT(DISTINCT "Alamat") as unique_locations,
                COUNT(DISTINCT "Nama Pelapor") as unique_reporters
            FROM flood_reports
        ''')
        stats_row = cursor.fetchone()
        yearly_stats = dict(stats_row) if stats_row else {}
        
        cursor.execute('''
            SELECT report_date as date, COUNT(*) as report_count
            FROM flood_reports 
            WHERE report_date >= date('now', '-30 days')
            GROUP BY report_date
            ORDER BY report_date DESC
        ''')
        daily_trend = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute('''
            SELECT CAST(strftime('%H', report_time) AS INTEGER) as hour, COUNT(*) as report_count
            FROM flood_reports 
            WHERE report_date >= date('now', '-30 days')
            GROUP BY strftime('%H', report_time)
            ORDER BY hour
        ''')
        hourly_pattern = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute('''
            SELECT "Alamat" as location, COUNT(*) as report_count
            FROM flood_reports 
            WHERE report_date >= date('now', '-30 days')
            GROUP BY "Alamat"
            ORDER BY report_count DESC
            LIMIT 5
        ''')
        top_locations = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        total_reports_last_30 = sum(day['report_count'] for day in daily_trend)
        avg_daily_reports = total_reports_last_30 / len(daily_trend) if daily_trend else 0
        
        trend_direction = "STABIL"
        if len(daily_trend) >= 7:
            recent = daily_trend[:7]
            older = daily_trend[7:14] if len(daily_trend) >= 14 else daily_trend[7:]
            if recent and older:
                recent_avg = sum(d['report_count'] for d in recent) / len(recent)
                older_avg = sum(d['report_count'] for d in older) / len(older) if older else recent_avg
                if recent_avg > older_avg * 1.3:
                    trend_direction = "MENINGKAT"
                elif recent_avg < older_avg * 0.7:
                    trend_direction = "MENURUN"
        
        return jsonify({
            'success': True,
            'yearly_stats': yearly_stats,
            'daily_trend': daily_trend,
            'hourly_pattern': hourly_pattern,
            'top_locations': top_locations,
            'trend_stats': {
                'total_last_30_days': total_reports_last_30,
                'avg_daily': round(avg_daily_reports, 1),
                'trend_direction': trend_direction,
                'current_month_total': yearly_stats.get('total_reports', 0) if yearly_stats else 0
            },
            'last_updated': get_wib_now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        app.logger.error(f"API Error in get-trend-data: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': 'Internal server error',
                       'error': str(e) if app.debug else None}), 500


@app.route("/api/update-status/<int:report_id>", methods=["POST"])
def update_status(report_id):
    try:
        data = request.get_json()
        
        if not data or "status" not in data:
            return jsonify({"success": False, "message": "Status tidak ditemukan"}), 400
        
        new_status = data["status"].lower().strip()
        valid_statuses = ["pending", "terverifikasi", "selesai"]
        if new_status not in valid_statuses:
            return jsonify({
                "success": False,
                "message": f"Status tidak valid. Pilih: {', '.join(valid_statuses)}"
            }), 400
        
        conn = sqlite3.connect(app.config["DATABASE_PATH"])
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, \"Alamat\" FROM flood_reports WHERE id = ?", (report_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({"success": False, "message": f"Laporan #{report_id} tidak ditemukan"}), 404
        
        cursor.execute("UPDATE flood_reports SET \"Status\" = ? WHERE id = ?", (new_status, report_id))
        conn.commit()
        
        cursor.execute("SELECT \"Alamat\", \"Status\" FROM flood_reports WHERE id = ?", (report_id,))
        updated = cursor.fetchone()
        conn.close()
        
        app.logger.info(f"✅ Status updated: Report #{report_id} -> {new_status}")
        
        return jsonify({
            "success": True,
            "message": f"Status laporan #{report_id} berhasil diubah menjadi \"{new_status}\"",
            "report_id": report_id,
            "new_status": new_status,
            "address": updated[0] if updated else None
        })
        
    except Exception as e:
        app.logger.error(f"API Error in update-status: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({"success": False, "message": "Gagal mengubah status",
                       "error": str(e) if app.debug else None}), 500

# ==================== STATIC FILES ====================

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        app.logger.error(f"Error serving file {filename}: {e}")
        return '', 404

@app.route('/static/<path:filename>')
def static_files(filename):
    try:
        return send_from_directory('static', filename)
    except Exception as e:
        app.logger.error(f"Error serving static file {filename}: {e}")
        return '', 404

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', page_title='Halaman Tidak Ditemukan', now=get_wib_now()), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html', page_title='Kesalahan Server', now=get_wib_now()), 500

# ==================== CONTEXT PROCESSORS ====================

@app.context_processor
def utility_processor():
    def format_date(date_string, format='%d/%m/%Y'):
        from datetime import datetime
        try:
            if not date_string:
                return ""
            dt = datetime.strptime(date_string, '%Y-%m-%d')
            return dt.strftime(format)
        except Exception:
            return date_string
    
    def format_time(time_string):
        if not time_string:
            return ""
        if len(time_string) >= 5:
            return time_string[:5]
        return ""
    
    def format_number(number):
        try:
            num = float(number)
            return f"{num:,.2f}"
        except:
            return number
    
    def get_risk_color(risk_level):
        colors = {'RENDAH': 'success', 'MENENGAH': 'warning', 'TINGGI': 'danger'}
        return colors.get(risk_level, 'secondary')
    
    return dict(
        format_date=format_date,
        format_time=format_time,
        format_number=format_number,
        get_risk_color=get_risk_color,
        now=get_wib_now()
    )

# ==================== INITIALIZATION ====================

def init_app():
    try:
        print("Initializing application...")
        
        directories = ['uploads', 'logs', 'backups', 'static/uploads']
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"✅ Directory: {directory}")
            except Exception as e:
                print(f"⚠️ Warning: Could not create {directory}: {e}")
        
        from models.database import init_db
        init_db()
        
        print("✅ Application initialized successfully")
        
    except Exception as e:
        print(f"❌ Initialization failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

# ==================== RUN APPLICATION ====================

if __name__ == '__main__':
    try:
        os.makedirs('logs', exist_ok=True)
        os.makedirs('uploads', exist_ok=True)
        os.makedirs('backups', exist_ok=True)
        
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/flood_system.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        app.logger = logging.getLogger(__name__)
        
        init_app()
        
        print("\n" + "="*50)
        print(f"🌊 {app.config['APP_NAME']} v{app.config['APP_VERSION']}")
        print(f"📊 Database: {app.config['DATABASE_PATH']}")
        print(f"📁 Uploads: {app.config['UPLOAD_FOLDER']}")
        print(f"📝 Logs: logs/flood_system.log")
        print(f"🌐 Server: http://127.0.0.1:5000")
        print(f"🕐 Timezone: WIB (Asia/Jakarta)")
        print("="*50 + "\n")
        
        app.run(
            debug=True,
            port=5000,
            host='0.0.0.0',
            use_reloader=True
        )
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()