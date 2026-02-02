#!/usr/bin/env python3
"""
Database Check & Verification Script
Untuk mengecek status database flood_system.db

Usage: python check_database.py
"""

import sqlite3
import os
from datetime import datetime, timedelta

def print_header(title):
    """Print fancy header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def check_database_file():
    """Check if database file exists"""
    print_header("DATABASE FILE CHECK")
    
    db_path = 'flood_system.db'
    
    if os.path.exists(db_path):
        file_size = os.path.getsize(db_path)
        file_size_mb = file_size / (1024 * 1024)
        
        print(f"SUCCESS: Database file found")
        print(f"  Path: {db_path}")
        print(f"  Size: {file_size_mb:.2f} MB ({file_size:,} bytes)")
        return True
    else:
        print(f"ERROR: Database file not found: {db_path}")
        print("\nTo create database, run: python models/database.py")
        return False

def check_table_structure():
    """Check database table structure"""
    print_header("TABLE STRUCTURE CHECK")
    
    try:
        conn = sqlite3.connect('flood_system.db')
        cursor = conn.cursor()
        
        # Get table list
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"Found {len(tables)} table(s):")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Check flood_reports table
        if ('flood_reports',) in tables:
            print("\nFlood Reports Table Structure:")
            cursor.execute("PRAGMA table_info(flood_reports)")
            columns = cursor.fetchall()
            
            print(f"  Total columns: {len(columns)}")
            print("\n  Column Details:")
            for col in columns:
                col_id, col_name, col_type, not_null, default, pk = col
                print(f"    {col_id+1}. {col_name} ({col_type})")
            
            # Check if geocoding columns exist
            col_names = [col[1] for col in columns]
            required_cols = ['latitude', 'longitude', 'is_geocoded']
            
            print("\n  Geocoding Columns Check:")
            for req_col in required_cols:
                if req_col in col_names:
                    print(f"    SUCCESS: {req_col} exists")
                else:
                    print(f"    MISSING: {req_col}")
        else:
            print("\nERROR: flood_reports table not found!")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def check_data_count():
    """Check data count in database"""
    print_header("DATA COUNT CHECK")
    
    try:
        conn = sqlite3.connect('flood_system.db')
        cursor = conn.cursor()
        
        # Total reports
        cursor.execute("SELECT COUNT(*) FROM flood_reports")
        total = cursor.fetchone()[0]
        print(f"Total reports: {total}")
        
        if total == 0:
            print("\nINFO: Database is empty")
            conn.close()
            return True
        
        # Reports with coordinates
        cursor.execute("""
            SELECT COUNT(*) FROM flood_reports 
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """)
        geocoded = cursor.fetchone()[0]
        print(f"Geocoded reports: {geocoded}")
        
        # Reports without coordinates
        pending_geocode = total - geocoded
        print(f"Pending geocoding: {pending_geocode}")
        
        if total > 0:
            geocode_percentage = (geocoded / total) * 100
            print(f"Geocoding coverage: {geocode_percentage:.1f}%")
        
        # Today's reports
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) FROM flood_reports WHERE report_date = ?", (today,))
        today_count = cursor.fetchone()[0]
        print(f"\nToday's reports: {today_count}")
        
        # This week's reports
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT COUNT(*) FROM flood_reports 
            WHERE report_date >= ?
        """, (week_ago,))
        week_count = cursor.fetchone()[0]
        print(f"This week's reports: {week_count}")
        
        # This month's reports
        month_start = datetime.now().strftime("%Y-%m-01")
        cursor.execute("""
            SELECT COUNT(*) FROM flood_reports 
            WHERE report_date >= ?
        """, (month_start,))
        month_count = cursor.fetchone()[0]
        print(f"This month's reports: {month_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def check_recent_reports():
    """Check recent reports"""
    print_header("RECENT REPORTS (Last 5)")
    
    try:
        conn = sqlite3.connect('flood_system.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, Timestamp, Alamat, "Tinggi Banjir", "Nama Pelapor", 
                   latitude, longitude, is_geocoded
            FROM flood_reports 
            ORDER BY id DESC 
            LIMIT 5
        """)
        
        reports = cursor.fetchall()
        
        if not reports:
            print("No reports found")
        else:
            for i, report in enumerate(reports, 1):
                print(f"\n{i}. Report #{report['id']}")
                print(f"   Timestamp:     {report['Timestamp']}")
                print(f"   Address:       {report['Alamat'][:50]}...")
                print(f"   Flood Height:  {report['Tinggi Banjir']}")
                print(f"   Reporter:      {report['Nama Pelapor']}")
                
                if report['latitude'] and report['longitude']:
                    print(f"   Coordinates:   ({report['latitude']:.6f}, {report['longitude']:.6f})")
                    print(f"   Geocoded:      YES")
                else:
                    print(f"   Coordinates:   Not available")
                    geocode_status = report['is_geocoded']
                    if geocode_status == -1:
                        print(f"   Geocoded:      FAILED")
                    elif geocode_status == 0 or geocode_status is None:
                        print(f"   Geocoded:      PENDING")
                    else:
                        print(f"   Geocoded:      UNKNOWN")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_flood_height_distribution():
    """Check flood height distribution"""
    print_header("FLOOD HEIGHT DISTRIBUTION")
    
    try:
        conn = sqlite3.connect('flood_system.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT "Tinggi Banjir", COUNT(*) as count
            FROM flood_reports
            GROUP BY "Tinggi Banjir"
            ORDER BY count DESC
        """)
        
        distribution = cursor.fetchall()
        
        if not distribution:
            print("No data available")
        else:
            print(f"Found {len(distribution)} different flood heights:\n")
            for height, count in distribution:
                percentage = (count / sum(d[1] for d in distribution)) * 100
                bar = "█" * int(percentage / 2)
                print(f"  {height:20s} : {count:4d} ({percentage:5.1f}%) {bar}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def check_data_integrity():
    """Check data integrity issues"""
    print_header("DATA INTEGRITY CHECK")
    
    try:
        conn = sqlite3.connect('flood_system.db')
        cursor = conn.cursor()
        
        issues = []
        
        # Check for NULL required fields
        cursor.execute("""
            SELECT COUNT(*) FROM flood_reports 
            WHERE Alamat IS NULL OR Alamat = ''
        """)
        null_address = cursor.fetchone()[0]
        if null_address > 0:
            issues.append(f"{null_address} reports with missing address")
        
        cursor.execute("""
            SELECT COUNT(*) FROM flood_reports 
            WHERE "Nama Pelapor" IS NULL OR "Nama Pelapor" = ''
        """)
        null_reporter = cursor.fetchone()[0]
        if null_reporter > 0:
            issues.append(f"{null_reporter} reports with missing reporter name")
        
        cursor.execute("""
            SELECT COUNT(*) FROM flood_reports 
            WHERE "Tinggi Banjir" IS NULL OR "Tinggi Banjir" = ''
        """)
        null_height = cursor.fetchone()[0]
        if null_height > 0:
            issues.append(f"{null_height} reports with missing flood height")
        
        # Check for potential duplicates
        cursor.execute("""
            SELECT Timestamp, Alamat, COUNT(*) as count
            FROM flood_reports
            GROUP BY Timestamp, Alamat
            HAVING count > 1
        """)
        duplicates = cursor.fetchall()
        if duplicates:
            issues.append(f"{len(duplicates)} potential duplicate entries found")
        
        if issues:
            print("ISSUES FOUND:")
            for issue in issues:
                print(f"  - {issue}")
            
            if duplicates:
                print("\nDuplicate entries:")
                for dup in duplicates[:5]:
                    print(f"  {dup[0]} at {dup[1][:40]}... ({dup[2]} occurrences)")
                if len(duplicates) > 5:
                    print(f"  ... and {len(duplicates)-5} more")
        else:
            print("SUCCESS: No integrity issues found")
        
        conn.close()
        return len(issues) == 0
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    """Main check runner"""
    print("\n" + "="*70)
    print("  DATABASE CHECK & VERIFICATION TOOL")
    print("  Flood Warning System - Version 2.0.1")
    print("="*70)
    
    # Run all checks
    checks = [
        ("Database File", check_database_file),
        ("Table Structure", check_table_structure),
        ("Data Count", check_data_count),
        ("Recent Reports", check_recent_reports),
        ("Flood Height Distribution", check_flood_height_distribution),
        ("Data Integrity", check_data_integrity)
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"\nERROR in {check_name}: {e}")
            results.append((check_name, False))
    
    # Summary
    print_header("CHECK SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "SUCCESS" if result else "ERROR"
        print(f"  {symbol}: {check_name}")
    
    print(f"\nOverall: {passed}/{total} checks passed")
    
    if passed == total:
        print("\nSUCCESS: Database is healthy!")
    else:
        print("\nWARNING: Some checks failed. Please review the issues above.")
    
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCheck cancelled by user")
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()