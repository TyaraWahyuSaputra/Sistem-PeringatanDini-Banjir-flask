#!/usr/bin/env python3
"""
Google Sheets Debug & Test Script
Untuk mengecek koneksi dan test save ke Google Sheets

Usage: python debug_sheets.py
"""

import sys
import os

# Add parent directory to path if needed
if os.path.exists('models'):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.google_sheets_model import GoogleSheetsModel
from datetime import datetime
import time

def print_header(title):
    """Print fancy header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def test_connection():
    """Test Google Sheets connection"""
    print_header("TEST 1: GOOGLE SHEETS CONNECTION")
    
    print("Initializing Google Sheets Model...")
    gs = GoogleSheetsModel()
    
    if gs.is_connected():
        print("SUCCESS: Connected to Google Sheets!")
        
        # Get status
        status = gs.get_worksheet_status()
        if status:
            print("\nWorksheet Information:")
            print(f"  Total Rows:    {status.get('rows', 0)}")
            print(f"  Total Columns: {status.get('columns', 0)}")
            print(f"  Data Rows:     {status.get('data_rows', 0)}")
            print(f"  Headers:       {', '.join(status.get('headers', []))}")
        
        return gs
    else:
        print("ERROR: Failed to connect to Google Sheets")
        print("\nTroubleshooting:")
        print("  1. Check if credentials.json exists")
        print("  2. Verify spreadsheet ID in config.py")
        print("  3. Ensure spreadsheet is shared with service account:")
        print("     flood-sheets-access@flood-warning-system-481323.iam.gserviceaccount.com")
        print("  4. Check internet connection")
        return None

def test_read_data(gs):
    """Test reading data from Google Sheets"""
    print_header("TEST 2: READ DATA FROM GOOGLE SHEETS")
    
    if not gs or not gs.is_connected():
        print("ERROR: Not connected to Google Sheets")
        return False
    
    try:
        print("Reading all reports...")
        reports = gs.get_all_reports()
        
        print(f"\nTotal reports in Google Sheets: {len(reports)}")
        
        if reports:
            print("\nSample (last 5 reports):")
            for i, report in enumerate(reports[-5:], 1):
                print(f"\n  Report {i}:")
                print(f"    Timestamp:     {report.get('Timestamp', 'N/A')}")
                print(f"    Address:       {report.get('Alamat', 'N/A')[:40]}...")
                print(f"    Reporter:      {report.get('Nama Pelapor', 'N/A')}")
                print(f"    Flood Height:  {report.get('Tinggi Banjir', 'N/A')}")
        else:
            print("\nNo reports found in Google Sheets")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to read data: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_write_data(gs):
    """Test writing data to Google Sheets"""
    print_header("TEST 3: WRITE DATA TO GOOGLE SHEETS")
    
    if not gs or not gs.is_connected():
        print("ERROR: Not connected to Google Sheets")
        return False
    
    response = input("Do you want to test writing a report to Google Sheets? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("Test skipped by user")
        return True
    
    try:
        # Create test data
        test_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        test_data = {
            'address': 'TEST ADDRESS - Jl. Test No. 123, Jakarta',
            'flood_height': '25 cm',
            'reporter_name': 'TEST USER - Debug Script',
            'reporter_phone': '081234567890',
            'ip_address': '127.0.0.1',
            'photo_url': 'test_debug.jpg',
            'status': 'pending'
        }
        
        print("\nTest Data:")
        print(f"  Timestamp:     {test_timestamp}")
        print(f"  Address:       {test_data['address']}")
        print(f"  Flood Height:  {test_data['flood_height']}")
        print(f"  Reporter:      {test_data['reporter_name']}")
        
        print("\nSaving to Google Sheets...")
        success = gs.save_flood_report_with_timestamp(
            timestamp=test_timestamp,
            report_data=test_data
        )
        
        if success:
            print("\nSUCCESS: Test report saved to Google Sheets!")
            print("\nPlease check your Google Sheets to verify:")
            print("  1. Open the spreadsheet")
            print("  2. Look for the test report at the bottom")
            print("  3. Reporter name should contain 'TEST USER - Debug Script'")
            
            # Clean up option
            response = input("\nDo you want to delete this test report? (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                print("\nNOTE: Manual deletion required")
                print("  1. Open Google Sheets")
                print("  2. Find the row with 'TEST USER - Debug Script'")
                print("  3. Right-click and delete the row")
            
            return True
        else:
            print("\nERROR: Failed to save test report")
            return False
            
    except Exception as e:
        print(f"\nERROR: Failed to write data: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_duplicate_check(gs):
    """Test duplicate checking mechanism"""
    print_header("TEST 4: DUPLICATE CHECK MECHANISM")
    
    if not gs or not gs.is_connected():
        print("ERROR: Not connected to Google Sheets")
        return False
    
    try:
        print("Reading existing reports...")
        existing_reports = gs.get_all_reports()
        existing_timestamps = {r.get('Timestamp', '') for r in existing_reports}
        
        print(f"\nFound {len(existing_reports)} existing reports")
        print(f"Unique timestamps: {len(existing_timestamps)}")
        
        if existing_reports:
            # Test with last report's timestamp
            last_report = existing_reports[-1]
            test_timestamp = last_report.get('Timestamp', '')
            
            print(f"\nTesting duplicate detection with timestamp: {test_timestamp}")
            
            if test_timestamp in existing_timestamps:
                print("SUCCESS: Duplicate detection working correctly")
                print("  This timestamp would be skipped in sync")
                return True
            else:
                print("WARNING: Duplicate detection may not be working")
                return False
        else:
            print("INFO: No existing reports to test with")
            return True
            
    except Exception as e:
        print(f"ERROR: Failed to test duplicate check: {e}")
        return False

def check_database_sync():
    """Compare database and Google Sheets data"""
    print_header("TEST 5: DATABASE vs GOOGLE SHEETS COMPARISON")
    
    # Check database
    import sqlite3
    
    try:
        conn = sqlite3.connect('flood_system.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM flood_reports')
        db_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT Timestamp FROM flood_reports ORDER BY id DESC LIMIT 5')
        db_recent = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        print(f"Database reports: {db_count}")
        print(f"\nRecent database timestamps:")
        for i, ts in enumerate(db_recent, 1):
            print(f"  {i}. {ts}")
        
    except Exception as e:
        print(f"ERROR: Cannot read database: {e}")
        db_count = 0
        db_recent = []
    
    # Check Google Sheets
    gs = GoogleSheetsModel()
    
    if gs.is_connected():
        try:
            sheets_reports = gs.get_all_reports()
            sheets_count = len(sheets_reports)
            sheets_recent = [r.get('Timestamp', '') for r in sheets_reports[-5:]]
            
            print(f"\nGoogle Sheets reports: {sheets_count}")
            print(f"\nRecent sheets timestamps:")
            for i, ts in enumerate(sheets_recent, 1):
                print(f"  {i}. {ts}")
            
        except:
            sheets_count = 0
            sheets_recent = []
    else:
        print("\nERROR: Cannot connect to Google Sheets")
        sheets_count = 0
        sheets_recent = []
    
    # Comparison
    print("\n" + "-"*70)
    print("COMPARISON:")
    print(f"  Database count:      {db_count}")
    print(f"  Google Sheets count: {sheets_count}")
    print(f"  Difference:          {abs(db_count - sheets_count)}")
    
    if db_count == sheets_count:
        print("\nSTATUS: Fully synced!")
    elif db_count > sheets_count:
        print(f"\nWARNING: {db_count - sheets_count} reports missing from Google Sheets")
        print("RECOMMENDATION: Run 'python fix_sync.py' to sync missing reports")
    else:
        print(f"\nWARNING: Google Sheets has {sheets_count - db_count} more reports than database")
        print("This might indicate duplicate entries in Google Sheets")
    
    return db_count == sheets_count

def main():
    """Main test runner"""
    print("\n" + "="*70)
    print("  GOOGLE SHEETS DEBUG & TEST TOOL")
    print("  Flood Warning System - Version 2.0.1")
    print("="*70)
    
    # Test 1: Connection
    gs = test_connection()
    if not gs:
        print("\nERROR: Cannot proceed without Google Sheets connection")
        print("Please fix the connection issues first")
        return
    
    # Wait
    time.sleep(1)
    
    # Test 2: Read
    test_read_data(gs)
    time.sleep(1)
    
    # Test 3: Write (optional)
    test_write_data(gs)
    time.sleep(1)
    
    # Test 4: Duplicate check
    test_duplicate_check(gs)
    time.sleep(1)
    
    # Test 5: Database sync
    check_database_sync()
    
    # Summary
    print_header("TEST SUMMARY")
    print("All tests completed!")
    print("\nNext steps:")
    print("  1. If all tests passed: Your Google Sheets sync is working correctly")
    print("  2. If connection failed: Check credentials and permissions")
    print("  3. If read/write failed: Check Google Sheets API status")
    print("  4. If sync mismatch: Run 'python fix_sync.py'")
    print("\nFor detailed solution guide, see: SOLUSI_GOOGLE_SHEETS.md")
    print("="*70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTests cancelled by user")
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()