"""
Google Sheets Model for Flood Warning System
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json
import pytz
import traceback
import time

class GoogleSheetsModel:
    def __init__(self, credentials_path=None):
        self.client = None
        self.spreadsheet = None
        self.worksheet = None
        self.tz_wib = pytz.timezone('Asia/Jakarta')
        self.connected = False
        
        print("Initializing Google Sheets Model...")
        
        if credentials_path:
            self.setup_connection(credentials_path)
        else:
            self.setup_connection()
    
    def setup_connection(self, credentials_path=None):
        """Setup Google Sheets connection with better error handling"""
        try:
            print("Setting up Google Sheets connection...")
            
            # Try multiple credential loading methods
            creds_dict = None
            
            # 1. Try loading from specified path
            if credentials_path and os.path.exists(credentials_path):
                print(f"   Trying credentials from: {credentials_path}")
                creds_dict = self._load_credentials(credentials_path)
            
            # 2. Try default credentials.json
            elif os.path.exists('credentials.json'):
                print("   Trying default credentials.json")
                creds_dict = self._load_credentials('credentials.json')
            
            # 3. Try environment variable
            elif os.getenv('GOOGLE_SHEETS_CREDENTIALS'):
                print("   Trying credentials from environment variable")
                try:
                    creds_dict = json.loads(os.getenv('GOOGLE_SHEETS_CREDENTIALS'))
                    print("   Loaded credentials from environment variable")
                except:
                    pass
            
            if not creds_dict:
                print("No Google Sheets credentials found - running in offline mode")
                self.client = None
                self.connected = False
                return
            
            # Define scope
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/spreadsheets'
            ]
            
            print("Creating credentials object...")
            # Create credentials object
            try:
                creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
                self.client = gspread.authorize(creds)
                print("Google Sheets API authorized")
            except Exception as e:
                print(f"Authorization failed: {e}")
                self.client = None
                self.connected = False
                return
            
            # Get spreadsheet ID from environment or use default
            spreadsheet_id = os.getenv('SPREADSHEET_ID', '1wdys3GzfDfl0ohCQjUHRyJVbKQcM0VSIMgCryHB0-mc')
            print(f"Attempting to open spreadsheet: {spreadsheet_id}")
            
            try:
                # Open spreadsheet
                self.spreadsheet = self.client.open_by_key(spreadsheet_id)
                print(f"Spreadsheet opened: {self.spreadsheet.title}")
                
                # Try to get 'flood_reports' worksheet
                try:
                    self.worksheet = self.spreadsheet.worksheet('flood_reports')
                    print(f"Worksheet found: {self.worksheet.title}")
                except gspread.exceptions.WorksheetNotFound:
                    print("Worksheet 'flood_reports' not found, creating new one...")
                    try:
                        self.worksheet = self.spreadsheet.add_worksheet(
                            title='flood_reports',
                            rows=1000,
                            cols=10
                        )
                        print("New worksheet 'flood_reports' created")
                        # Add headers
                        headers = ['Timestamp', 'Alamat', 'Tinggi Banjir', 'Nama Pelapor', 
                                'No HP', 'IP Address', 'Photo URL', 'Status']
                        self.worksheet.append_row(headers)
                        print("Headers added to new worksheet")
                    except Exception as e:
                        print(f"Error creating worksheet: {e}")
                        print("Trying first available worksheet...")
                        self.worksheet = self.spreadsheet.get_worksheet(0)
                
                if self.worksheet:
                    print(f"Using worksheet: {self.worksheet.title}")
                    
                    # Ensure headers exist
                    self.create_header_if_needed([
                        'Timestamp', 'Alamat', 'Tinggi Banjir', 'Nama Pelapor',
                        'No HP', 'IP Address', 'Photo URL', 'Status'
                    ])
                    
                    self.connected = True
                    print("Google Sheets connection successful")
                    
                    # Print current status
                    self.get_worksheet_status()
                    
                else:
                    print("No worksheets found")
                    self.client = None
                    self.connected = False
                
            except Exception as e:
                print(f"Error opening spreadsheet: {e}")
                print("Make sure:")
                print("   1. Spreadsheet ID is correct")
                print("   2. Spreadsheet is shared with: flood-sheets-access@flood-warning-system-481323.iam.gserviceaccount.com")
                print("   3. Internet connection is available")
                self.client = None
                self.connected = False
            
        except Exception as e:
            print(f"Google Sheets connection failed: {e}")
            traceback.print_exc()
            self.client = None
            self.connected = False
    
    def _load_credentials(self, filepath):
        """Load credentials from file with improved error handling"""
        try:
            if not os.path.exists(filepath):
                print(f"Credentials file not found: {filepath}")
                return None
            
            print(f"Reading credentials from {filepath}...")
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try to parse as JSON first
            try:
                creds_dict = json.loads(content)
                print(f"Loaded JSON credentials from: {filepath}")
                return creds_dict
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                print("   Trying to fix JSON format...")
                return self._fix_json_format(content)
                
        except Exception as e:
            print(f"Error loading credentials from {filepath}: {e}")
            return None
    
    def _fix_json_format(self, content):
        """Fix common JSON formatting issues"""
        try:
            # Remove BOM if present
            if content.startswith('\ufeff'):
                content = content[1:]
            
            # Fix escaped newlines in private key
            lines = content.split('\n')
            fixed_lines = []
            in_private_key = False
            private_key_lines = []
            
            for line in lines:
                if '"private_key":' in line and '-----BEGIN PRIVATE KEY-----' in line:
                    in_private_key = True
                    # Extract the start of private key
                    key_start = line.find('-----BEGIN PRIVATE KEY-----')
                    if key_start > 0:
                        before_key = line[:key_start]
                        key_content = line[key_start:]
                        fixed_lines.append(before_key + key_content.replace('\\n', '\n'))
                        in_private_key = False
                elif in_private_key:
                    if '-----END PRIVATE KEY-----' in line:
                        fixed_lines.append(line.replace('\\n', '\n'))
                        in_private_key = False
                    else:
                        fixed_lines.append(line.replace('\\n', '\n'))
                else:
                    fixed_lines.append(line.replace('\\n', '\n'))
            
            fixed_content = '\n'.join(fixed_lines)
            
            # Parse the fixed JSON
            creds_dict = json.loads(fixed_content)
            print("Fixed and loaded credentials")
            return creds_dict
            
        except Exception as e:
            print(f"Error fixing JSON format: {e}")
            return None
    
    def get_worksheet_status(self):
        """Get and display worksheet status"""
        try:
            if not self.connected or not self.worksheet:
                return None
            
            row_count = self.worksheet.row_count
            col_count = self.worksheet.col_count
            
            print(f"Worksheet Status:")
            print(f"   Rows: {row_count}, Columns: {col_count}")
            
            # Get first row (headers)
            headers = self.worksheet.row_values(1)
            print(f"   Headers: {headers}")
            
            # Get row count (excluding header)
            data_rows = max(0, row_count - 1)
            print(f"   Data rows: {data_rows}")
            
            return {
                'rows': row_count,
                'columns': col_count,
                'headers': headers,
                'data_rows': data_rows
            }
            
        except Exception as e:
            print(f"Error getting worksheet status: {e}")
            return None
    
    def save_flood_report(self, report_data):
        """Save flood report to Google Sheets with robust error handling"""
        if not self.connected or not self.worksheet:
            print("Google Sheets not connected - skipping")
            return False
        
        try:
            current_time = datetime.now(self.tz_wib)
            timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"Saving to Google Sheets...")
            print(f"   Address: {report_data.get('address', 'N/A')}")
            print(f"   Reporter: {report_data.get('reporter_name', 'N/A')}")
            
            # Ensure headers exist
            self.create_header_if_needed([
                'Timestamp', 'Alamat', 'Tinggi Banjir', 'Nama Pelapor',
                'No HP', 'IP Address', 'Photo URL', 'Status'
            ])
            
            # Prepare row data
            row = [
                timestamp,
                report_data.get('address', ''),
                report_data.get('flood_height', ''),
                report_data.get('reporter_name', ''),
                report_data.get('reporter_phone', ''),
                report_data.get('ip_address', ''),
                report_data.get('photo_url', ''),
                'pending'
            ]
            
            print(f"   Row data prepared")
            
            # Get current status before append
            try:
                row_count_before = self.worksheet.row_count
                print(f"   Rows before append: {row_count_before}")
            except:
                row_count_before = 1
            
            # Append row with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    print(f"   Attempt {attempt + 1}/{max_retries}...")
                    
                    # Append the row
                    self.worksheet.append_row(row, value_input_option='RAW')
                    print(f"   Row appended successfully")
                    
                    # Wait for Google Sheets to update
                    time.sleep(1)
                    
                    # Verify append
                    try:
                        row_count_after = self.worksheet.row_count
                        print(f"   Rows after append: {row_count_after}")
                        
                        if row_count_after > row_count_before:
                            print(f"Report successfully saved to Google Sheets (Row {row_count_after})")
                            return True
                        else:
                            print(f"Row count didn't increase. Retrying...")
                    except:
                        print(f"Row appended (verification skipped)")
                        return True
                    
                except Exception as e:
                    print(f"   Attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        print(f"   Waiting 2 seconds before retry...")
                        time.sleep(2)
                        # Refresh connection
                        try:
                            self.worksheet = self.spreadsheet.worksheet(self.worksheet.title)
                            print("   Worksheet connection refreshed")
                        except:
                            pass
                    else:
                        raise
            
        except Exception as e:
            print(f"Error saving to Google Sheets: {e}")
            traceback.print_exc()
            return False
    
    def get_all_reports(self):
        """Get all reports from Google Sheets"""
        if not self.connected or not self.worksheet:
            print("Google Sheets not connected")
            return []
        
        try:
            # Get all values
            all_values = self.worksheet.get_all_values()
            
            if len(all_values) <= 1:  # Only headers or empty
                return []
            
            # Convert to list of dictionaries
            headers = all_values[0]
            records = []
            
            for row in all_values[1:]:
                if any(cell for cell in row):  # Skip empty rows
                    record = {}
                    for i, header in enumerate(headers):
                        if i < len(row):
                            record[header] = row[i]
                        else:
                            record[header] = ''
                    records.append(record)
            
            print(f"Retrieved {len(records)} records from Google Sheets")
            return records
            
        except Exception as e:
            print(f"Error reading from Google Sheets: {e}")
            return []
    
    def save_flood_report_with_timestamp(self, timestamp, report_data):
        """Save report with specific timestamp"""
        if not self.connected or not self.worksheet:
            print("Google Sheets not connected")
            return False
        
        try:
            # Ensure headers exist
            self.create_header_if_needed([
                'Timestamp', 'Alamat', 'Tinggi Banjir', 'Nama Pelapor',
                'No HP', 'IP Address', 'Photo URL', 'Status'
            ])
            
            # Prepare row data
            row = [
                timestamp,
                report_data.get('address', ''),
                report_data.get('flood_height', ''),
                report_data.get('reporter_name', ''),
                report_data.get('reporter_phone', ''),
                report_data.get('ip_address', ''),
                report_data.get('photo_url', ''),
                report_data.get('status', 'pending')
            ]
            
            # Append to Google Sheets
            self.worksheet.append_row(row, value_input_option='RAW')
            print(f"Report saved to Google Sheets: {report_data.get('address', '')[:30]}...")
            return True
            
        except Exception as e:
            print(f"Error saving to Google Sheets: {e}")
            return False
    
    def append_report(self, report_data):
        """Alias for save_flood_report_with_timestamp (for backward compatibility)"""
        timestamp = report_data.get('timestamp', '')
        if not timestamp:
            # Create timestamp if not provided
            from datetime import datetime
            timestamp = datetime.now(self.tz_wib).strftime("%Y-%m-%d %H:%M:%S")
        
        return self.save_flood_report_with_timestamp(timestamp, report_data)
    
    def create_header_if_needed(self, headers):
        """Create headers if worksheet is empty"""
        if not self.connected or not self.worksheet:
            return False
        
        try:
            # Get first row
            first_row = self.worksheet.row_values(1)
            
            # If worksheet is empty, add headers
            if not first_row or len(first_row) == 0 or all(cell == '' for cell in first_row):
                self.worksheet.append_row(headers)
                print("Added headers to Google Sheets")
                return True
            
            # Check if headers match
            if first_row != headers:
                print(f"Headers mismatch. Found: {first_row}, Expected: {headers}")
                return False
                
            return False
            
        except Exception as e:
            print(f"Error checking/creating headers: {e}")
            return False
    
    def is_connected(self):
        """Check if Google Sheets is connected"""
        return self.connected