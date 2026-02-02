import sqlite3
from datetime import datetime, timedelta
import os
import traceback
import pytz

class FloodReportModel:
    def __init__(self, db_path='flood_system.db'):
        self.db_path = db_path
        self.tz_wib = pytz.timezone('Asia/Jakarta')
        print(f"📊 FloodReportModel initialized: {db_path}")
    
    def _get_connection(self):
        """Get database connection with proper error handling"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            print(f"âŒ Database connection error: {e}")
            return None
    
    def create_report(self, data):
        """Create new flood report - FIXED VERSION"""
        conn = None
        commit_successful = False  # Track if commit actually succeeded
        
        try:
            # Check if timestamp is provided (for sync from Google Sheets)
            if 'timestamp' in data and data['timestamp']:
                # Use provided timestamp from Google Sheets
                provided_timestamp = data['timestamp']
                
                # Parse the timestamp to extract date and time
                try:
                    # Try multiple formats
                    for fmt in ["%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S"]:
                        try:
                            dt = datetime.strptime(provided_timestamp, fmt)
                            # Convert to WIB if needed
                            if dt.tzinfo is None:
                                dt = self.tz_wib.localize(dt)
                            timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                            report_date = dt.strftime("%Y-%m-%d")
                            report_time = dt.strftime("%H:%M:%S")
                            print(f"âœ… [Model]: Using provided timestamp: {timestamp}")
                            break
                        except ValueError:
                            continue
                    else:
                        # If all formats fail, use current time
                        raise ValueError("Could not parse timestamp")
                        
                except Exception as e:
                    print(f"⚠️ [Model]: Could not parse timestamp '{provided_timestamp}': {e}")
                    print(f"⚠️ [Model]: Falling back to current time")
                    current_time = datetime.now(self.tz_wib)
                    timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
                    report_date = current_time.strftime("%Y-%m-%d")
                    report_time = current_time.strftime("%H:%M:%S")
            else:
                # Use current time for new reports
                current_time = datetime.now(self.tz_wib)
                timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
                report_date = current_time.strftime("%Y-%m-%d")
                report_time = current_time.strftime("%H:%M:%S")
            
            conn = self._get_connection()
            if not conn:
                print(f"❌ [Model]: Failed to get database connection")
                return None
            
            cursor = conn.cursor()
            
            print(f"📝 [Model]: Inserting report data: {data.get('alamat', '')[:30]}...")
            
            cursor.execute('''
                INSERT INTO flood_reports 
                ("Timestamp", "Alamat", "Tinggi Banjir", "Nama Pelapor", 
                 "No HP", "IP Address", "Photo URL", "Status",
                 report_date, report_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp,
                data.get('alamat', ''),
                data.get('tinggi_banjir', ''),
                data.get('nama_pelapor', ''),
                data.get('no_hp', ''),
                data.get('ip_address', 'unknown'),
                data.get('photo_url', ''),
                data.get('status', 'pending'),
                report_date,
                report_time
            ))
            
            # CRITICAL: Commit database
            conn.commit()
            commit_successful = True  # Mark that commit succeeded
            print(f"✅ [Model]: Data committed to database successfully")
            
            # Now try to get the report ID
            report_id = cursor.lastrowid
            
            # Fallback 1: Query by timestamp if lastrowid failed
            if not report_id or report_id <= 0:
                print(f"⚠️ [Model]: lastrowid={report_id}, using fallback query...")
                cursor.execute('''
                    SELECT id FROM flood_reports 
                    WHERE "Timestamp" = ? 
                      AND "Alamat" = ? 
                      AND "Nama Pelapor" = ?
                    ORDER BY id DESC 
                    LIMIT 1
                ''', (timestamp, data.get('alamat', ''), data.get('nama_pelapor', '')))
                
                result = cursor.fetchone()
                if result and result[0]:
                    report_id = result[0]
                    print(f"✅ [Model]: Got ID from query: {report_id}")
            
            # Fallback 2: Use MAX(id) as last resort
            if not report_id or report_id <= 0:
                print(f"⚠️ [Model]: Query failed, using MAX(id)...")
                cursor.execute('SELECT MAX(id) FROM flood_reports')
                max_result = cursor.fetchone()
                if max_result and max_result[0]:
                    report_id = max_result[0]
                    print(f"✅ [Model]: Got ID from MAX: {report_id}")
                else:
                    # Absolute fallback
                    report_id = 1
                    print(f"⚠️ [Model]: Using fallback ID: 1")
            
            cursor.close()
            
            # Ensure we have a valid positive integer ID
            if not isinstance(report_id, (int, float)) or report_id < 1:
                report_id = 1  # Minimum valid ID
            
            final_id = int(report_id)
            print(f"✅ [Model]: Report created - ID: {final_id}")
            return final_id
            
        except sqlite3.IntegrityError as e:
            # Database constraint violation (duplicate, etc.)
            print(f"❌ [Model]: Database integrity error: {e}")
            if conn and not commit_successful:
                conn.rollback()
            return None
            
        except sqlite3.OperationalError as e:
            # Database is locked, disk full, etc.
            print(f"❌ [Model]: Database operational error: {e}")
            if conn and not commit_successful:
                conn.rollback()
            return None
            
        except Exception as e:
            # Any other error
            print(f"âŒ [Model]: Unexpected error: {e}")
            traceback.print_exc()
            
            # CRITICAL FIX: Only rollback if commit hasn't happened yet!
            if conn and not commit_successful:
                print(f"⚠️ [Model]: Rolling back uncommitted transaction")
                conn.rollback()
            elif commit_successful:
                # Data was committed but ID retrieval failed
                print(f"⚠️ [Model]: Data WAS saved but ID retrieval failed")
                # Try one more time to get ANY valid ID
                try:
                    if conn:
                        cursor2 = conn.cursor()
                        cursor2.execute('SELECT MAX(id) FROM flood_reports')
                        max_result = cursor2.fetchone()
                        if max_result and max_result[0]:
                            emergency_id = int(max_result[0])
                            cursor2.close()
                            print(f"✅ [Model]: Emergency ID retrieval: {emergency_id}")
                            return emergency_id
                except:
                    pass
                # Return a positive ID to signal success even if we don't know exact ID
                print(f"⚠️ [Model]: Returning default success ID")
                return 1
            
            return None
            
        finally:
            if conn:
                conn.close()
    def get_today_reports(self):
        """Get today's reports"""
        conn = None
        try:
            today = datetime.now(self.tz_wib).strftime("%Y-%m-%d")
            
            conn = self._get_connection()
            if not conn:
                return []
            
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM flood_reports 
                WHERE report_date = ?
                ORDER BY "Timestamp" DESC
            ''', (today,))
            
            rows = cursor.fetchall()
            
            reports = []
            for row in rows:
                reports.append(dict(row))
            
            cursor.close()
            
            return reports
            
        except Exception as e:
            print(f"❌ Error getting today's reports: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_month_reports(self):
        """Get this month's reports - SIMPLE VERSION"""
        conn = None
        try:
            # Get current month and year
            now = datetime.now(self.tz_wib)
            current_year = now.year
            current_month = now.month
            current_month_str = f"{current_year}-{current_month:02d}"
            
            print(f"📅 [Model] Mencari laporan untuk: {current_month_str}")
            
            conn = self._get_connection()
            if not conn:
                print("❌ [Model] Tidak dapat terkoneksi ke database")
                return []
            
            cursor = conn.cursor()
            reports = []
            
            # Query utama: cari berdasarkan report_date
            try:
                cursor.execute('''
                    SELECT * FROM flood_reports 
                    WHERE report_date LIKE ?
                    ORDER BY report_date DESC, "Timestamp" DESC
                ''', (f"{current_month_str}%",))
                
                rows = cursor.fetchall()
                if rows:
                    print(f"✅ [Model] Ditemukan {len(rows)} laporan menggunakan report_date")
                    for row in rows:
                        reports.append(dict(row))
                else:
                    print("ℹ️ [Model] Tidak ditemukan laporan menggunakan report_date")
                    
            except Exception as e:
                print(f"⚠️ [Model] Error query report_date: {e}")
            
            # Jika tidak ada, coba cari di Timestamp
            if not reports:
                try:
                    cursor.execute('''
                        SELECT * FROM flood_reports 
                        WHERE "Timestamp" LIKE ?
                        ORDER BY "Timestamp" DESC
                    ''', (f"{current_month_str}%",))
                    
                    rows = cursor.fetchall()
                    if rows:
                        print(f"✅ [Model] Ditemukan {len(rows)} laporan menggunakan Timestamp")
                        for row in rows:
                            reports.append(dict(row))
                    else:
                        print("ℹ️ [Model] Tidak ditemukan laporan menggunakan Timestamp")
                        
                except Exception as e:
                    print(f"⚠️ [Model] Error query Timestamp: {e}")
            
            cursor.close()
            
            # Log hasil
            if reports:
                print(f"📊 [Model] Total laporan bulan {current_month_str}: {len(reports)}")
            else:
                print(f"ℹ️ [Model] Tidak ada laporan untuk bulan {current_month_str}")
                
                # Tampilkan bulan-bulan yang ada di database
                try:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT DISTINCT SUBSTR(report_date, 1, 7) as bulan 
                        FROM flood_reports 
                        WHERE report_date IS NOT NULL 
                        ORDER BY bulan DESC
                        LIMIT 6
                    ''')
                    months = cursor.fetchall()
                    if months:
                        print(f"ℹ️ [Model] Bulan yang tersedia: {[m[0] for m in months if m[0]]}")
                    cursor.close()
                except:
                    pass
            
            return reports
            
        except Exception as e:
            print(f"❌ Error getting month's reports: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_yearly_statistics(self):
        """Get yearly statistics for the last 12 months - FIXED VERSION"""
        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return {'months_data': []}
            
            cursor = conn.cursor()
            current_date = datetime.now(self.tz_wib)
            
            # Calculate the date 12 months ago
            start_date = (current_date - timedelta(days=365)).strftime("%Y-%m-%d")
            end_date = current_date.strftime("%Y-%m-%d")
            
            # Get data for last 12 months using report_date
            cursor.execute('''
                SELECT 
                    strftime('%Y-%m', report_date) as month,
                    strftime('%Y', report_date) as year,
                    CAST(strftime('%m', report_date) AS INTEGER) as month_num,
                    COUNT(*) as report_count
                FROM flood_reports
                WHERE report_date BETWEEN ? AND ?
                GROUP BY strftime('%Y-%m', report_date)
                ORDER BY report_date DESC
                LIMIT 12
            ''', (start_date, end_date))
            
            rows = cursor.fetchall()
            months_data = []
            
            for row in rows:
                months_data.append({
                    'year_month': row['month'],
                    'month_name': datetime.strptime(row['month'], "%Y-%m").strftime("%b"),
                    'report_count': row['report_count'],
                    'is_current': row['month'] == current_date.strftime("%Y-%m")
                })
            
            # If no data found using report_date, try using Timestamp
            if not months_data:
                cursor.execute('''
                    SELECT 
                        strftime('%Y-%m', "Timestamp") as month,
                        strftime('%Y', "Timestamp") as year,
                        CAST(strftime('%m', "Timestamp") AS INTEGER) as month_num,
                        COUNT(*) as report_count
                    FROM flood_reports
                    WHERE "Timestamp" BETWEEN ? AND ?
                    GROUP BY strftime('%Y-%m', "Timestamp")
                    ORDER BY "Timestamp" DESC
                    LIMIT 12
                ''', (start_date, end_date))
                
                rows = cursor.fetchall()
                for row in rows:
                    months_data.append({
                        'year_month': row['month'],
                        'month_name': datetime.strptime(row['month'], "%Y-%m").strftime("%b"),
                        'report_count': row['report_count'],
                        'is_current': row['month'] == current_date.strftime("%Y-%m")
                    })
            
            # Calculate statistics
            total_reports = sum(item['report_count'] for item in months_data)
            avg_per_month = total_reports / len(months_data) if months_data else 0
            
            if months_data:
                max_item = max(months_data, key=lambda x: x['report_count'])
                max_month = max_item['month_name']
                max_count = max_item['report_count']
            else:
                max_month = "Tidak ada data"
                max_count = 0
            
            cursor.close()
            
            return {
                'months_data': months_data,
                'total_reports': total_reports,
                'avg_per_month': round(avg_per_month, 1),
                'max_month': max_month,
                'max_count': max_count,
                'current_year_month': current_date.strftime("%Y-%m")
            }
            
        except Exception as e:
            print(f"❌ Error getting yearly statistics: {e}")
            traceback.print_exc()
            return {
                'months_data': [],
                'total_reports': 0,
                'avg_per_month': 0,
                'max_month': "Error",
                'max_count': 0,
                'current_year_month': ""
            }
        finally:
            if conn:
                conn.close()
    
    def get_all_reports(self):
        """Get all reports"""
        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return []
            
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM flood_reports ORDER BY "Timestamp" DESC')
            rows = cursor.fetchall()
            
            reports = []
            for row in rows:
                reports.append(dict(row))
            
            cursor.close()
            
            return reports
            
        except Exception as e:
            print(f"❌ Error getting all reports: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_report_statistics(self):
        """Get comprehensive report statistics"""
        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return {}
            
            cursor = conn.cursor()
            
            stats = {}
            
            # Total reports
            cursor.execute('SELECT COUNT(*) as count FROM flood_reports')
            stats['total_reports'] = cursor.fetchone()[0] or 0
            
            # Today's reports
            today = datetime.now(self.tz_wib).strftime("%Y-%m-%d")
            cursor.execute('SELECT COUNT(*) as count FROM flood_reports WHERE report_date = ?', (today,))
            stats['today_reports'] = cursor.fetchone()[0] or 0
            
            # Unique locations
            cursor.execute('SELECT COUNT(DISTINCT "Alamat") as count FROM flood_reports')
            stats['unique_locations'] = cursor.fetchone()[0] or 0
            
            # Unique reporters
            cursor.execute('SELECT COUNT(DISTINCT "Nama Pelapor") as count FROM flood_reports')
            stats['unique_reporters'] = cursor.fetchone()[0] or 0
            
            # Flood height distribution
            cursor.execute('''
                SELECT "Tinggi Banjir", COUNT(*) as count 
                FROM flood_reports 
                GROUP BY "Tinggi Banjir"
                ORDER BY count DESC
            ''')
            stats['height_distribution'] = dict(cursor.fetchall())
            
            # Status distribution
            cursor.execute('''
                SELECT "Status", COUNT(*) as count 
                FROM flood_reports 
                GROUP BY "Status"
            ''')
            stats['status_distribution'] = dict(cursor.fetchall())
            
            cursor.close()
            
            return stats
            
        except Exception as e:
            print(f"❌ Error getting report statistics: {e}")
            return {}
        finally:
            if conn:
                conn.close()
    
    def sync_from_google_sheets(self, sheets_data):
        """Sync data from Google Sheets to database"""
        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            synced_count = 0
            for sheet_report in sheets_data:
                try:
                    # Check if report already exists (by Timestamp or unique combination)
                    timestamp = sheet_report.get('Timestamp', '')
                    address = sheet_report.get('Alamat', '')
                    reporter = sheet_report.get('Nama Pelapor', '')
                    
                    if not timestamp or not address:
                        continue
                    
                    # Check if exists
                    cursor.execute('''
                        SELECT COUNT(*) FROM flood_reports 
                        WHERE "Timestamp" = ? AND "Alamat" = ? AND "Nama Pelapor" = ?
                    ''', (timestamp, address, reporter))
                    
                    exists = cursor.fetchone()[0] > 0
                    
                    if not exists:
                        # Insert new report
                        cursor.execute('''
                            INSERT INTO flood_reports 
                            ("Timestamp", "Alamat", "Tinggi Banjir", "Nama Pelapor", 
                             "No HP", "IP Address", "Photo URL", "Status",
                             report_date, report_time)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            timestamp,
                            address,
                            sheet_report.get('Tinggi Banjir', ''),
                            reporter,
                            sheet_report.get('No HP', ''),
                            sheet_report.get('IP Address', ''),
                            sheet_report.get('Photo URL', ''),
                            sheet_report.get('Status', 'pending'),
                            timestamp[:10] if timestamp else '',  # Extract date from timestamp
                            timestamp[11:19] if len(timestamp) > 10 else ''  # Extract time
                        ))
                        
                        synced_count += 1
                        
                except Exception as e:
                    print(f"⚠️ Error syncing report from Google Sheets: {e}")
                    continue
            
            conn.commit()
            cursor.close()
            
            print(f"✅ Synced {synced_count} reports from Google Sheets")
            return synced_count > 0
            
        except Exception as e:
            print(f"❌ Error syncing from Google Sheets: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()