import sqlite3
from datetime import datetime, timedelta
import os
import traceback
import pytz

class FloodReportModel:
    def __init__(self, db_path=None):
        """
        Initialize Flood Report Model with ABSOLUTE database path
        
        CRITICAL: Must use same absolute path in all environments
        """
        if db_path is None:
            # Get absolute path from config
            from config import Config
            self.db_path = Config.DATABASE_PATH
        else:
            # Ensure path is absolute
            self.db_path = os.path.abspath(db_path)
        
        self.tz_wib = pytz.timezone('Asia/Jakarta')
        print(f"📊 FloodReportModel initialized: {self.db_path}")
    
    def _get_connection(self):
        """
        Get database connection with proper error handling
        
        CRITICAL: Each request gets its own connection (WSGI-safe)
        """
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            conn.execute('PRAGMA journal_mode=WAL')
            return conn
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            traceback.print_exc()
            return None
    
    def create_report(self, data):
        """
        Create new flood report
        
        CRITICAL: This must work identically in local and PythonAnywhere
        
        Returns: report_id (int) if successful, None if failed
        """
        conn = None
        commit_successful = False
        
        try:
            # Handle timestamp
            if 'timestamp' in data and data['timestamp']:
                # Use provided timestamp (from sync)
                provided_timestamp = data['timestamp']
                
                try:
                    # Parse timestamp
                    for fmt in ["%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S"]:
                        try:
                            dt = datetime.strptime(provided_timestamp, fmt)
                            if dt.tzinfo is None:
                                dt = self.tz_wib.localize(dt)
                            timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                            report_date = dt.strftime("%Y-%m-%d")
                            report_time = dt.strftime("%H:%M:%S")
                            print(f"✅ [Model]: Using provided timestamp: {timestamp}")
                            break
                        except ValueError:
                            continue
                    else:
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
            
            # Get database connection
            conn = self._get_connection()
            if not conn:
                print(f"❌ [Model]: Failed to get database connection")
                print(f"   Database path: {self.db_path}")
                print(f"   Database exists: {os.path.exists(self.db_path)}")
                return None
            
            cursor = conn.cursor()
            
            print(f"📝 [Model]: Inserting report data: {data.get('alamat', '')[:30]}...")
            print(f"   Timestamp: {timestamp}")
            print(f"   Address: {data.get('alamat', '')}")
            print(f"   Reporter: {data.get('nama_pelapor', '')}")
            
            # Insert data
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
            
            # CRITICAL: Commit to database
            print(f"💾 [Model]: Committing to database...")
            conn.commit()
            commit_successful = True
            print(f"✅ [Model]: Data committed successfully")
            
            # Get the report ID
            report_id = cursor.lastrowid
            print(f"   lastrowid: {report_id}")
            
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
                    report_id = 1
                    print(f"⚠️ [Model]: Using fallback ID: 1")
            
            cursor.close()
            
            # Ensure we have a valid positive integer ID
            if not isinstance(report_id, (int, float)) or report_id < 1:
                report_id = 1
            
            final_id = int(report_id)
            print(f"✅ [Model]: Report created successfully - ID: {final_id}")
            return final_id
            
        except sqlite3.IntegrityError as e:
            print(f"❌ [Model]: Database integrity error: {e}")
            print(f"   This usually means duplicate data or constraint violation")
            if conn and not commit_successful:
                conn.rollback()
            return None
            
        except sqlite3.OperationalError as e:
            print(f"❌ [Model]: Database operational error: {e}")
            print(f"   This could mean: locked database, disk full, or permission issue")
            print(f"   Database path: {self.db_path}")
            if conn and not commit_successful:
                conn.rollback()
            return None
            
        except Exception as e:
            print(f"❌ [Model]: Unexpected error: {e}")
            traceback.print_exc()
            
            # CRITICAL: Only rollback if commit hasn't happened yet
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
                except Exception as inner_e:
                    print(f"❌ [Model]: Emergency ID retrieval also failed: {inner_e}")
                
                # Return a positive ID to signal success
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
            reports = [dict(row) for row in rows]
            cursor.close()
            
            return reports
            
        except Exception as e:
            print(f"❌ Error getting today's reports: {e}")
            traceback.print_exc()
            return []
        finally:
            if conn:
                conn.close()
    
    def get_daily_statistics(self, date=None):
        """Get statistics for a specific date"""
        conn = None
        try:
            if date is None:
                date = datetime.now(self.tz_wib).strftime("%Y-%m-%d")
            
            conn = self._get_connection()
            if not conn:
                return {}
            
            cursor = conn.cursor()
            
            # Total reports for the date
            cursor.execute('''
                SELECT COUNT(*) as count FROM flood_reports 
                WHERE report_date = ?
            ''', (date,))
            total_reports = cursor.fetchone()[0] or 0
            
            # Reports by hour
            cursor.execute('''
                SELECT 
                    substr(report_time, 1, 2) as hour,
                    COUNT(*) as count 
                FROM flood_reports 
                WHERE report_date = ?
                GROUP BY hour
                ORDER BY hour
            ''', (date,))
            hourly_data = cursor.fetchall()
            
            # Flood height distribution
            cursor.execute('''
                SELECT "Tinggi Banjir", COUNT(*) as count 
                FROM flood_reports 
                WHERE report_date = ?
                GROUP BY "Tinggi Banjir"
                ORDER BY count DESC
            ''', (date,))
            height_dist = cursor.fetchall()
            
            # Status distribution
            cursor.execute('''
                SELECT "Status", COUNT(*) as count 
                FROM flood_reports 
                WHERE report_date = ?
                GROUP BY "Status"
            ''', (date,))
            status_dist = cursor.fetchall()
            
            cursor.close()
            
            return {
                'date': date,
                'total_reports': total_reports,
                'hourly_data': [dict(row) for row in hourly_data],
                'height_distribution': [dict(row) for row in height_dist],
                'status_distribution': [dict(row) for row in status_dist]
            }
            
        except Exception as e:
            print(f"❌ Error getting daily statistics: {e}")
            traceback.print_exc()
            return {}
        finally:
            if conn:
                conn.close()
    
    def get_monthly_statistics(self, year_month=None):
        """Get statistics for a specific month"""
        conn = None
        try:
            if year_month is None:
                year_month = datetime.now(self.tz_wib).strftime("%Y-%m")
            
            conn = self._get_connection()
            if not conn:
                return {}
            
            cursor = conn.cursor()
            
            # Total reports for the month
            cursor.execute('''
                SELECT COUNT(*) as count FROM flood_reports 
                WHERE strftime('%Y-%m', report_date) = ?
            ''', (year_month,))
            total_reports = cursor.fetchone()[0] or 0
            
            # Daily breakdown
            cursor.execute('''
                SELECT 
                    report_date,
                    COUNT(*) as count 
                FROM flood_reports 
                WHERE strftime('%Y-%m', report_date) = ?
                GROUP BY report_date
                ORDER BY report_date
            ''', (year_month,))
            daily_data = cursor.fetchall()
            
            cursor.close()
            
            return {
                'year_month': year_month,
                'total_reports': total_reports,
                'daily_data': [dict(row) for row in daily_data]
            }
            
        except Exception as e:
            print(f"❌ Error getting monthly statistics: {e}")
            traceback.print_exc()
            return {}
        finally:
            if conn:
                conn.close()
    
    def get_yearly_statistics(self):
        """Get statistics for current year"""
        conn = None
        try:
            current_date = datetime.now(self.tz_wib)
            current_year = current_date.year
            
            conn = self._get_connection()
            if not conn:
                return {
                    'months_data': [],
                    'total_reports': 0,
                    'avg_per_month': 0,
                    'max_month': "Tidak ada data",
                    'max_count': 0,
                    'current_year_month': current_date.strftime("%Y-%m")
                }
            
            cursor = conn.cursor()
            
            # Get data for all months in current year
            cursor.execute('''
                SELECT 
                    strftime('%Y-%m', report_date) as year_month,
                    strftime('%m', report_date) as month,
                    COUNT(*) as count 
                FROM flood_reports 
                WHERE strftime('%Y', report_date) = ?
                GROUP BY year_month
                ORDER BY year_month
            ''', (str(current_year),))
            
            results = cursor.fetchall()
            
            # Month names in Indonesian
            month_names = {
                '01': 'Januari', '02': 'Februari', '03': 'Maret', '04': 'April',
                '05': 'Mei', '06': 'Juni', '07': 'Juli', '08': 'Agustus',
                '09': 'September', '10': 'Oktober', '11': 'November', '12': 'Desember'
            }
            
            months_data = []
            for row in results:
                months_data.append({
                    'year_month': row['year_month'],
                    'month_name': month_names.get(row['month'], row['month']),
                    'report_count': row['count']
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
            
            reports = [dict(row) for row in rows]
            cursor.close()
            
            return reports
            
        except Exception as e:
            print(f"❌ Error getting all reports: {e}")
            traceback.print_exc()
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
            traceback.print_exc()
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
                    # Check if report already exists
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
                            timestamp[:10] if timestamp else '',
                            timestamp[11:19] if len(timestamp) > 10 else ''
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
            traceback.print_exc()
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()