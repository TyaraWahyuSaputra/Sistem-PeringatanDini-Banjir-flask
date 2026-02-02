"""
Script untuk memperbaiki sync Google Sheets
Jalankan: python fix_sync.py

FIXED: 
- Changed get_worksheet_info() to get_worksheet_status()
- Added better error handling
- Added duplicate checking before sync
"""

import sqlite3
from datetime import datetime
from models.google_sheets_model import GoogleSheetsModel

def check_google_sheets_connection():
    """Cek koneksi Google Sheets"""
    print("Checking Google Sheets connection...")
    gs = GoogleSheetsModel()
    
    if gs.is_connected():
        print("SUCCESS: Google Sheets connected!")
        info = gs.get_worksheet_status()
        if info:
            print(f"  Rows: {info.get('rows', 0)}")
            print(f"  Columns: {info.get('columns', 0)}")
            print(f"  Data rows: {info.get('data_rows', 0)}")
        return gs
    else:
        print("ERROR: Google Sheets not connected")
        print("\nTroubleshooting:")
        print("  1. Check if credentials.json exists")
        print("  2. Check if Google Sheets is shared with service account")
        print("  3. Check internet connection")
        return None

def sync_all_to_google_sheets():
    """Sync semua data dari database ke Google Sheets"""
    print("\n" + "="*60)
    print("SYNC FROM DATABASE TO GOOGLE SHEETS")
    print("="*60 + "\n")
    
    gs = check_google_sheets_connection()
    if not gs:
        return
    
    # Connect to database
    try:
        conn = sqlite3.connect('flood_system.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
    except Exception as e:
        print(f"ERROR: Cannot connect to database: {e}")
        return
    
    # Get all reports
    try:
        cursor.execute('SELECT * FROM flood_reports ORDER BY id')
        reports = cursor.fetchall()
    except Exception as e:
        print(f"ERROR: Cannot read from database: {e}")
        conn.close()
        return
    
    print(f"Found {len(reports)} reports in database")
    
    # Get existing reports from Google Sheets
    try:
        existing_reports = gs.get_all_reports()
        existing_timestamps = {r.get('Timestamp', '') for r in existing_reports}
        print(f"Found {len(existing_reports)} existing reports in Google Sheets")
    except Exception as e:
        print(f"ERROR: Cannot read from Google Sheets: {e}")
        conn.close()
        return
    
    # Sync missing reports
    synced_count = 0
    failed_count = 0
    skipped_count = 0
    
    for idx, report in enumerate(reports, 1):
        timestamp = report['Timestamp']
        address = report['Alamat']
        
        print(f"\n[{idx}/{len(reports)}] Processing report #{report['id']}")
        print(f"  Timestamp: {timestamp}")
        print(f"  Address: {address[:40]}...")
        
        if timestamp in existing_timestamps:
            print(f"  SKIPPED: Already exists in Google Sheets")
            skipped_count += 1
            continue
        
        try:
            success = gs.save_flood_report_with_timestamp(
                timestamp=timestamp,
                report_data={
                    'address': report['Alamat'],
                    'flood_height': report['Tinggi Banjir'],
                    'reporter_name': report['Nama Pelapor'],
                    'reporter_phone': report['No HP'] or '',
                    'ip_address': report['IP Address'] or '',
                    'photo_url': report['Photo URL'] or '',
                    'status': report['Status'] or 'pending'
                }
            )
            
            if success:
                synced_count += 1
                print(f"  SUCCESS: Synced to Google Sheets")
            else:
                failed_count += 1
                print(f"  FAILED: Could not sync to Google Sheets")
                
        except Exception as e:
            failed_count += 1
            print(f"  ERROR: {e}")
    
    conn.close()
    
    # Summary
    print("\n" + "="*60)
    print("SYNC SUMMARY")
    print("="*60)
    print(f"  Total reports in database: {len(reports)}")
    print(f"  Already in Google Sheets:  {skipped_count}")
    print(f"  Successfully synced:       {synced_count}")
    print(f"  Failed to sync:            {failed_count}")
    print("="*60)
    
    if synced_count > 0:
        print(f"\nSUCCESS: {synced_count} new reports synced to Google Sheets")
    elif skipped_count == len(reports):
        print(f"\nINFO: All {len(reports)} reports already exist in Google Sheets")
    else:
        print(f"\nWARNING: Some reports failed to sync")

if __name__ == "__main__":
    try:
        sync_all_to_google_sheets()
    except KeyboardInterrupt:
        print("\n\nSync cancelled by user")
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()