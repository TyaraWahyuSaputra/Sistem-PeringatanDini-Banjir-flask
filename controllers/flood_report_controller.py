import os
import uuid
from datetime import datetime, timedelta
import sqlite3
import traceback
from werkzeug.utils import secure_filename
import pytz
import time
import logging

from models.flood_report_model import FloodReportModel
from models.google_sheets_model import GoogleSheetsModel
from config import Config

# Setup logger
logger = logging.getLogger(__name__)

class FloodReportController:
    def __init__(self):
        self.flood_model = FloodReportModel()
        self.sheets_model = GoogleSheetsModel()
        self.tz_wib = pytz.timezone('Asia/Jakarta')
        self.db_path = 'flood_system.db'
        
        # Initialize OSM geocoder (if enabled)
        self.geocoder = None
        
        if Config.GEOCODING_ENABLED and Config.GEOCODING_PROVIDER == 'osm':
            try:
                from utils.helpers import OSMGeocoder
                self.geocoder = OSMGeocoder(
                    user_agent=Config.OSM_USER_AGENT,
                    base_url=Config.OSM_BASE_URL
                )
                logger.info("✅ OSM Geocoder initialized")
                
                # Test connection
                if not self.geocoder.test_connection():
                    logger.warning("⚠️ OSM geocoder test failed, running in offline mode")
                    self.geocoder = None
                else:
                    logger.info("✅ OSM connection test successful")
            except Exception as e:
                logger.error(f"❌ Failed to initialize OSM geocoder: {e}")
                self.geocoder = None
        else:
            logger.info(f"ℹ️ Geocoding disabled or using different provider: {Config.GEOCODING_PROVIDER}")
        
        # Check Google Sheets connection
        if self.sheets_model.is_connected():
            logger.info("✅ Google Sheets connected")
        else:
            logger.warning("⚠️ Google Sheets not connected - running in offline mode")
        
        # Ensure upload folder exists
        self.upload_folder = 'uploads'
        self._ensure_upload_folder()
        
        logger.info("✅ FloodReportController fully initialized")
    
    def _ensure_upload_folder(self):
        """Create upload folder if not exists"""
        if not os.path.exists(self.upload_folder):
            os.makedirs(self.upload_folder)
            logger.info(f"✅ Created upload folder: {self.upload_folder}")
    
    def _allowed_file(self, filename):
        """Check if file extension is allowed"""
        if not filename:
            return False
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in allowed_extensions
    
    def save_uploaded_file(self, file):
        """Save uploaded file and return path"""
        if not file or file.filename == '':
            return None
        
        if not self._allowed_file(file.filename):
            logger.warning(f"⚠️ Invalid file extension: {file.filename}")
            return None
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
        file_path = os.path.join(self.upload_folder, unique_filename)
        
        try:
            file.save(file_path)
            logger.info(f"✅ File saved: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"❌ Error saving file: {e}")
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
            return None
    
    def _is_duplicate_report(self, address, reporter_name, flood_height):
        """
        Check if report is duplicate within last 2 minutes
        STRICTER duplicate checking to prevent POST resubmission
        """
        try:
            current_time = datetime.now(self.tz_wib)
            timestamp_check = current_time.strftime("%Y-%m-%d %H:%M:%S")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check for EXACT duplicate within last 2 minutes
            cursor.execute('''
                SELECT COUNT(*) FROM flood_reports 
                WHERE "Alamat" = ? 
                AND "Nama Pelapor" = ? 
                AND "Tinggi Banjir" = ?
                AND datetime("Timestamp") >= datetime(?, '-2 minutes')
            ''', (address, reporter_name, flood_height, timestamp_check))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            if count > 0:
                logger.warning(f"⚠️ Duplicate detected: {address[:30]}... by {reporter_name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error checking duplicate: {e}")
            # On error, allow submission but log it
            return False
    
    def submit_report(self, data):
        """
        Submit new flood report - FIXED with strict duplicate prevention
        Returns: (success: bool, message: str)
        """
        photo_path = None
        try:
            # Extract data
            address = data.get('address', '').strip()
            flood_height = data.get('flood_height', '').strip()
            reporter_name = data.get('reporter_name', '').strip()
            reporter_phone = data.get('reporter_phone', '').strip()
            photo_file = data.get('photo')
            
            # Debug logging
            logger.info(f"📝 Processing report: {reporter_name} at {address[:30]}...")
            
            # Validate required fields
            if not address:
                return False, "Alamat harus diisi"
            if not flood_height or flood_height == 'Pilih tinggi banjir':
                return False, "Pilih tinggi banjir"
            if not reporter_name:
                return False, "Nama pelapor harus diisi"
            if not photo_file or photo_file.filename == '':
                return False, "Foto harus diunggah"
            
            # CHECK 1: Check for duplicate BEFORE processing photo
            if self._is_duplicate_report(address, reporter_name, flood_height):
                logger.warning("⚠️ DUPLICATE BLOCKED: Report rejected as duplicate")
                return False, "Laporan duplikat terdeteksi. Anda baru saja melaporkan lokasi yang sama."
            
            # Handle photo upload
            photo_path = self.save_uploaded_file(photo_file)
            if not photo_path:
                return False, "Format foto tidak didukung atau file terlalu besar (max 5MB). Gunakan JPG, PNG, atau GIF"
            
            # Get client IP
            client_ip = self.get_client_ip()
            
            # Check daily limit
            if not self.check_daily_limit(client_ip):
                # Clean up uploaded file if validation fails
                if photo_path and os.path.exists(photo_path):
                    try:
                        os.remove(photo_path)
                    except:
                        pass
                return False, "Batas laporan harian telah tercapai (10 laporan/hari)"
            
            # CHECK 2: Double-check duplicate RIGHT before insert
            if self._is_duplicate_report(address, reporter_name, flood_height):
                logger.warning("⚠️ DUPLICATE BLOCKED (2nd check): Report rejected")
                if photo_path and os.path.exists(photo_path):
                    try:
                        os.remove(photo_path)
                    except:
                        pass
                return False, "Laporan duplikat terdeteksi. Silakan tunggu beberapa saat sebelum mengirim laporan baru."
            
            # Prepare data for database
            report_data = {
                'alamat': address,
                'tinggi_banjir': flood_height,
                'nama_pelapor': reporter_name,
                'no_hp': reporter_phone,
                'photo_url': photo_path,
                'ip_address': client_ip
            }
            
            # STEP 1: Save to database FIRST (PRIMARY SOURCE)
            logger.info("💾 Saving to database...")
            report_id = self.flood_model.create_report(report_data)
            
            # FIXED: Lebih strict - hanya None/False/0 yang dianggap gagal
            # Jika report_id >= 1, maka data PASTI sudah tersimpan
            if report_id is None or report_id is False or (isinstance(report_id, (int, float)) and report_id < 1):
                logger.error(f"âŒ Database save FAILED - report_id is {report_id}")
                if photo_path and os.path.exists(photo_path):
                    try:
                        os.remove(photo_path)
                    except:
                        pass
                return False, "Gagal menyimpan laporan ke database"
            
            logger.info(f"✅ Database save SUCCESS - report_id: {report_id}")
            
            # STEP 2: Try to sync to Google Sheets (SECONDARY - best effort)
            sheets_saved = False
            try:
                if self.sheets_model.is_connected():
                    logger.info("☁️ Syncing to Google Sheets...")
                    
                    # Get the timestamp that was actually saved
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT "Timestamp" FROM flood_reports WHERE id = ?
                    ''', (report_id,))
                    result = cursor.fetchone()
                    conn.close()
                    
                    if result:
                        actual_timestamp = result[0]
                        
                        # Prepare data for Google Sheets with actual timestamp
                        sheets_data = {
                            'address': address,
                            'flood_height': flood_height,
                            'reporter_name': reporter_name,
                            'reporter_phone': reporter_phone,
                            'ip_address': client_ip,
                            'photo_url': photo_path,
                            'status': 'pending'
                        }
                        
                        sheets_saved = self.sheets_model.save_flood_report_with_timestamp(
                            actual_timestamp, sheets_data
                        )
                        
                        if sheets_saved:
                            logger.info("✅ Google Sheets sync SUCCESS")
                        else:
                            logger.warning("⚠️ Google Sheets sync FAILED (non-critical)")
                    else:
                        logger.warning("⚠️ Could not retrieve timestamp for Google Sheets sync")
                else:
                    logger.info("ℹ️ Google Sheets not connected, skipping sync")
            except Exception as e:
                logger.error(f"❌ Error syncing to Google Sheets: {e}")
                # Don't fail the whole operation if Google Sheets fails
                pass
            
            # SUCCESS message
            success_message = f"✅ Laporan berhasil dikirim! (ID: {report_id})"
            if sheets_saved:
                success_message += " Data tersinkronisasi ke Google Sheets."
            
            return True, success_message
            
        except Exception as e:
            logger.error(f"❌ Error submitting report: {e}")
            logger.error(traceback.format_exc())
            
            # Clean up photo if exists
            if photo_path and os.path.exists(photo_path):
                try:
                    os.remove(photo_path)
                except:
                    pass
            
            return False, f"Terjadi kesalahan sistem: {str(e)}"
    
    def get_client_ip(self):
        """Get client IP from Flask request context"""
        try:
            from flask import request
            if request.headers.get('X-Forwarded-For'):
                return request.headers.get('X-Forwarded-For').split(',')[0].strip()
            elif request.headers.get('X-Real-IP'):
                return request.headers.get('X-Real-IP')
            else:
                return request.remote_addr or 'Unknown'
        except:
            return 'Unknown'
    
    def check_daily_limit(self, ip_address):
        """Check if IP has exceeded daily report limit"""
        try:
            today = datetime.now(self.tz_wib).strftime("%Y-%m-%d")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) FROM flood_reports 
                WHERE "IP Address" = ? AND report_date = ?
            ''', (ip_address, today))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            max_reports = Config.MAX_REPORTS_PER_DAY if hasattr(Config, 'MAX_REPORTS_PER_DAY') else 10
            
            if count >= max_reports:
                logger.warning(f"⚠️ Daily limit exceeded for IP: {ip_address} ({count}/{max_reports})")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error checking daily limit: {e}")
            return True  # Allow submission on error
    
    # ==================== NEW: COMBINED DATA RETRIEVAL ====================
    
    def get_all_reports_combined(self):
        """
        Get all reports from BOTH database and Google Sheets
        Merges data and removes duplicates
        Returns: list of report dictionaries
        """
        try:
            logger.info("📊 Fetching reports from all sources...")
            
            # Get reports from database
            db_reports = self.flood_model.get_all_reports()
            logger.info(f"  Database: {len(db_reports)} reports")
            
            # Get reports from Google Sheets
            sheets_reports = []
            try:
                if self.sheets_model.is_connected():
                    sheets_data = self.sheets_model.get_all_reports()
                    
                    # Convert Google Sheets data to standard format
                    for sheet_row in sheets_data:
                        try:
                            sheets_reports.append({
                                'Timestamp': sheet_row.get('Timestamp', ''),
                                'Alamat': sheet_row.get('Alamat', ''),
                                'Tinggi Banjir': sheet_row.get('Tinggi Banjir', ''),
                                'Nama Pelapor': sheet_row.get('Nama Pelapor', ''),
                                'No HP': sheet_row.get('No HP', ''),
                                'IP Address': sheet_row.get('IP Address', ''),
                                'Photo URL': sheet_row.get('Photo URL', ''),
                                'Status': sheet_row.get('Status', 'pending'),
                                'source': 'google_sheets'
                            })
                        except Exception as e:
                            logger.warning(f"⚠️ Error parsing sheet row: {e}")
                            continue
                    
                    logger.info(f"  Google Sheets: {len(sheets_reports)} reports")
            except Exception as e:
                logger.error(f"❌ Error fetching from Google Sheets: {e}")
            
            # Merge and deduplicate
            all_reports = self._merge_and_deduplicate_reports(db_reports, sheets_reports)
            
            logger.info(f"✅ Total combined reports: {len(all_reports)}")
            return all_reports
            
        except Exception as e:
            logger.error(f"❌ Error getting combined reports: {e}")
            logger.error(traceback.format_exc())
            return []
    
    def get_recent_activities(self, limit=10):
        """
        Get recent activities from both database and Google Sheets
        Returns: list of recent report dictionaries
        """
        try:
            all_reports = self.get_all_reports_combined()
            
            # Sort by timestamp (newest first)
            sorted_reports = sorted(
                all_reports,
                key=lambda x: x.get('Timestamp', ''),
                reverse=True
            )
            
            # Return limited number
            return sorted_reports[:limit]
            
        except Exception as e:
            logger.error(f"❌ Error getting recent activities: {e}")
            return []
    
    def _merge_and_deduplicate_reports(self, db_reports, sheets_reports):
        """
        Merge reports from database and Google Sheets, removing duplicates
        Priority: Database reports take precedence over Google Sheets
        """
        try:
            # Create a dictionary to track unique reports
            # Key: (timestamp, address, reporter)
            unique_reports = {}
            
            # Add database reports first (higher priority)
            for report in db_reports:
                key = (
                    report.get('Timestamp', ''),
                    report.get('Alamat', ''),
                    report.get('Nama Pelapor', '')
                )
                if key[0] and key[1]:  # Only if timestamp and address exist
                    unique_reports[key] = {**report, 'source': 'database'}
            
            # Add Google Sheets reports (only if not already in database)
            for report in sheets_reports:
                key = (
                    report.get('Timestamp', ''),
                    report.get('Alamat', ''),
                    report.get('Nama Pelapor', '')
                )
                if key[0] and key[1] and key not in unique_reports:
                    unique_reports[key] = report
            
            # Convert back to list
            merged_reports = list(unique_reports.values())
            
            return merged_reports
            
        except Exception as e:
            logger.error(f"❌ Error merging reports: {e}")
            return db_reports  # Return database reports on error
    
    def get_today_reports_combined(self):
        """Get today's reports from database - IMPROVED to use report_date"""
        try:
            # Get today's date in WIB timezone
            today = datetime.now(self.tz_wib).date()
            today_str = today.strftime("%Y-%m-%d")
            
            logger.info(f"🔍 Fetching reports for today: {today_str}")
            
            # Query database for today's reports only using report_date column
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    id,
                    "Timestamp",
                    "Alamat",
                    "Tinggi Banjir",
                    "Nama Pelapor",
                    "No HP",
                    "IP Address",
                    "Photo URL",
                    "Status",
                    report_date,
                    report_time,
                    latitude,
                    longitude
                FROM flood_reports 
                WHERE report_date = ?
                ORDER BY report_time DESC
            ''', (today_str,))
            
            reports_rows = cursor.fetchall()
            today_reports = [dict(row) for row in reports_rows]
            
            conn.close()
            
            logger.info(f"✅ Found {len(today_reports)} reports for today ({today_str})")
            
            return today_reports
            
        except Exception as e:
            logger.error(f"❌ Error getting today's reports: {e}")
            logger.error(traceback.format_exc())
            return []
    
    def get_month_reports_combined(self):
        """Get reports from last 12 months - IMPROVED for comprehensive analysis"""
        try:
            now = datetime.now(self.tz_wib)
            
            # Calculate date range (last 12 months)
            start_date = (now - timedelta(days=365)).strftime("%Y-%m-%d")
            end_date = now.strftime("%Y-%m-%d")
            
            logger.info(f"🔍 Fetching reports from {start_date} to {end_date}")
            
            # Query database for last 12 months
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    id,
                    "Timestamp",
                    "Alamat",
                    "Tinggi Banjir",
                    "Nama Pelapor",
                    "No HP",
                    "IP Address",
                    "Photo URL",
                    "Status",
                    report_date,
                    report_time,
                    latitude,
                    longitude,
                    strftime('%Y-%m', report_date) as month_year
                FROM flood_reports 
                WHERE report_date BETWEEN ? AND ?
                ORDER BY report_date DESC, report_time DESC
            ''', (start_date, end_date))
            
            reports_rows = cursor.fetchall()
            all_reports = [dict(row) for row in reports_rows]
            
            conn.close()
            
            logger.info(f"✅ Found {len(all_reports)} reports from last 12 months")
            
            return all_reports
            
        except Exception as e:
            logger.error(f"❌ Error getting month's combined reports: {e}")
            logger.error(traceback.format_exc())
            return []
    
    def get_monthly_statistics(self):
        """Get comprehensive statistics for last 12 months - FIXED VERSION"""
        try:
            now = datetime.now(self.tz_wib)
            # Start from the first day of the month 12 months ago
            start_date = (now - timedelta(days=365)).replace(day=1).strftime("%Y-%m-%d")
            end_date = now.strftime("%Y-%m-%d")
            
            logger.info(f"📈 Calculating monthly statistics from {start_date} to {end_date}")
            
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get monthly aggregates for the last 12 months
            cursor.execute('''
                SELECT 
                    strftime('%Y-%m', report_date) as month,
                    strftime('%Y', report_date) as year,
                    CAST(strftime('%m', report_date) AS INTEGER) as month_num,
                    COUNT(*) as report_count,
                    COUNT(DISTINCT "Alamat") as unique_locations
                FROM flood_reports
                WHERE report_date BETWEEN ? AND ?
                GROUP BY strftime('%Y-%m', report_date)
                ORDER BY report_date DESC
                LIMIT 12
            ''', (start_date, end_date))
            
            monthly_data_rows = cursor.fetchall()
            monthly_data = [dict(row) for row in monthly_data_rows]
            
            # Calculate total reports
            total_reports = sum(m['report_count'] for m in monthly_data)
            
            # Calculate average per month
            avg_per_month = total_reports / len(monthly_data) if monthly_data else 0
            
            # Find max and min months
            if monthly_data:
                max_month_data = max(monthly_data, key=lambda x: x['report_count'])
                min_month_data = min(monthly_data, key=lambda x: x['report_count'])
                max_month = max_month_data['month']
                max_count = max_month_data['report_count']
                min_month = min_month_data['month']
                min_count = min_month_data['report_count']
            else:
                max_month = "N/A"
                max_count = 0
                min_month = "N/A"
                min_count = 0
            
            # Calculate trend percentage (compare last month with previous month)
            trend_percentage = 0
            trend_direction = "STABIL"
            
            if len(monthly_data) >= 2:
                last_month = monthly_data[0]['report_count']
                previous_month = monthly_data[1]['report_count']
                
                if previous_month > 0:
                    trend_percentage = ((last_month - previous_month) / previous_month) * 100
                
                if trend_percentage > 10:
                    trend_direction = "MENINGKAT"
                elif trend_percentage < -10:
                    trend_direction = "MENURUN"
            
            # Get flood height distribution for the entire period
            cursor.execute('''
                SELECT "Tinggi Banjir" as height, COUNT(*) as count
                FROM flood_reports
                WHERE report_date BETWEEN ? AND ?
                GROUP BY "Tinggi Banjir"
            ''', (start_date, end_date))
            
            flood_heights_rows = cursor.fetchall()
            flood_heights = {row['height']: row['count'] for row in flood_heights_rows}
            
            # Get top 5 locations for the entire period
            cursor.execute('''
                SELECT "Alamat" as location, COUNT(*) as count
                FROM flood_reports
                WHERE report_date BETWEEN ? AND ?
                GROUP BY "Alamat"
                ORDER BY count DESC
                LIMIT 5
            ''', (start_date, end_date))
            
            top_locations_rows = cursor.fetchall()
            top_locations = [dict(row) for row in top_locations_rows]
            
            # Get status distribution
            cursor.execute('''
                SELECT "Status" as status, COUNT(*) as count
                FROM flood_reports
                WHERE report_date BETWEEN ? AND ?
                GROUP BY "Status"
            ''', (start_date, end_date))
            
            status_rows = cursor.fetchall()
            status_counts = {row['status']: row['count'] for row in status_rows}
            
            conn.close()
            
            # Format monthly data for chart — generate full 12-month sequence
            months_id = ['', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
                         'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']

            # Build a lookup: "2026-01" -> report_count
            monthly_lookup = {}
            for data in monthly_data:
                monthly_lookup[data['month']] = data['report_count']

            chart_labels = []
            chart_data = []


            # Display all 12 months of current year (January to December)
            current_year = now.year
            for month in range(1, 13):  # 1 to 12 for Jan to Dec
                key = f"{current_year}-{month:02d}"
                chart_labels.append(months_id[month])
                chart_data.append(monthly_lookup.get(key, 0))
            return {
                'total_reports': total_reports,
                'avg_per_month': round(avg_per_month, 1),
                'max_month': max_month,
                'max_count': max_count,
                'min_month': min_month,
                'min_count': min_count,
                'unique_locations': sum(m['unique_locations'] for m in monthly_data),
                'trend_direction': trend_direction,
                'trend_percentage': round(trend_percentage, 1),
                'chart_labels': chart_labels,
                'chart_data': chart_data,
                'flood_heights': flood_heights,
                'top_locations': top_locations,
                'status_counts': status_counts,
                'months_data': monthly_data  # Include raw monthly data for template
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting monthly statistics: {e}")
            logger.error(traceback.format_exc())
            return {
                'total_reports': 0,
                'avg_per_month': 0,
                'max_month': "N/A",
                'max_count': 0,
                'min_month': "N/A",
                'min_count': 0,
                'unique_locations': 0,
                'trend_direction': "STABIL",
                'trend_percentage': 0,
                'chart_labels': [],
                'chart_data': [],
                'flood_heights': {},
                'top_locations': [],
                'status_counts': {},
                'months_data': []
            }