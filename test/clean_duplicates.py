#!/usr/bin/env python3
"""
Script untuk membersihkan duplikasi data di database flood_system.db
ENHANCED VERSION: Lebih aman, detail, dan dengan backup otomatis

Usage: python fix_duplicates.py
"""

import sqlite3
from datetime import datetime
import shutil
import os

def print_header(title):
    """Print fancy header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def backup_database():
    """Buat backup sebelum cleaning"""
    if not os.path.exists('backups'):
        os.makedirs('backups')
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"backups/flood_system_before_cleanup_{timestamp}.db"
    
    try:
        shutil.copy2('flood_system.db', backup_file)
        print(f"SUCCESS: Backup created: {backup_file}")
        return backup_file
    except Exception as e:
        print(f"ERROR: Backup failed: {e}")
        return None

def analyze_duplicates():
    """Analisis duplikasi secara detail"""
    print_header("ANALISIS DUPLIKASI DATABASE")
    
    try:
        conn = sqlite3.connect('flood_system.db')
        cursor = conn.cursor()
        
        # Total records
        cursor.execute('SELECT COUNT(*) FROM flood_reports')
        total = cursor.fetchone()[0]
        print(f"Total records: {total}")
        
        # Method 1: Exact duplicates (same timestamp, address, reporter, height)
        cursor.execute('''
            SELECT 
                "Timestamp", "Alamat", "Nama Pelapor", "Tinggi Banjir",
                COUNT(*) as count,
                GROUP_CONCAT(id) as ids
            FROM flood_reports 
            GROUP BY "Timestamp", "Alamat", "Nama Pelapor", "Tinggi Banjir"
            HAVING count > 1
            ORDER BY count DESC, "Timestamp" DESC
        ''')
        
        exact_dups = cursor.fetchall()
        
        if exact_dups:
            print(f"\nFound {len(exact_dups)} groups of EXACT duplicates:")
            print("-" * 70)
            
            total_duplicate_records = 0
            for i, dup in enumerate(exact_dups[:10], 1):
                timestamp, alamat, nama, tinggi, count, ids = dup
                duplicate_count = count - 1  # Keep one, remove others
                total_duplicate_records += duplicate_count
                
                print(f"\n{i}. {count}x duplicates (will remove {duplicate_count}):")
                print(f"   Timestamp: {timestamp}")
                print(f"   Address: {alamat[:50]}...")
                print(f"   Reporter: {nama}")
                print(f"   Height: {tinggi}")
                print(f"   IDs: {ids}")
            
            if len(exact_dups) > 10:
                remaining = len(exact_dups) - 10
                for dup in exact_dups[10:]:
                    total_duplicate_records += (dup[4] - 1)
                print(f"\n   ... and {remaining} more duplicate groups")
            
            print("\n" + "-" * 70)
            print(f"SUMMARY:")
            print(f"  Total duplicate groups: {len(exact_dups)}")
            print(f"  Total records to remove: {total_duplicate_records}")
            print(f"  Records after cleanup: {total - total_duplicate_records}")
            
        else:
            print("\nNo exact duplicates found!")
        
        # Method 2: Similar reports (same address, reporter, height within 5 minutes)
        cursor.execute('''
            SELECT COUNT(*) FROM (
                SELECT 
                    "Alamat", "Nama Pelapor", "Tinggi Banjir",
                    COUNT(*) as count
                FROM flood_reports 
                GROUP BY "Alamat", "Nama Pelapor", "Tinggi Banjir"
                HAVING count > 1
            )
        ''')
        
        similar_groups = cursor.fetchone()[0]
        if similar_groups > 0:
            print(f"\nNote: Found {similar_groups} groups with same address+reporter+height")
            print("      (may have different timestamps)")
        
        conn.close()
        return len(exact_dups), total_duplicate_records
        
    except Exception as e:
        print(f"ERROR: Analysis failed: {e}")
        return 0, 0

def clean_exact_duplicates():
    """
    Bersihkan EXACT duplicates - keep only the FIRST one (lowest ID)
    Returns: number of records deleted
    """
    print_header("MEMBERSIHKAN EXACT DUPLICATES")
    
    try:
        conn = sqlite3.connect('flood_system.db')
        cursor = conn.cursor()
        
        # Get total before
        cursor.execute('SELECT COUNT(*) FROM flood_reports')
        total_before = cursor.fetchone()[0]
        
        print(f"Records before cleanup: {total_before}")
        
        # Delete duplicates, keep the one with LOWEST id (first inserted)
        print("\nRemoving duplicates (keeping first occurrence)...")
        cursor.execute('''
            DELETE FROM flood_reports 
            WHERE id NOT IN (
                SELECT MIN(id) 
                FROM flood_reports 
                GROUP BY "Timestamp", "Alamat", "Nama Pelapor", "Tinggi Banjir"
            )
        ''')
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        # Get total after
        cursor.execute('SELECT COUNT(*) FROM flood_reports')
        total_after = cursor.fetchone()[0]
        
        print(f"\nResults:")
        print(f"  Records before: {total_before}")
        print(f"  Records after:  {total_after}")
        print(f"  Removed:        {deleted_count}")
        
        conn.close()
        return deleted_count
        
    except Exception as e:
        print(f"ERROR: Cleanup failed: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return 0

def verify_cleanup():
    """Verifikasi bahwa tidak ada duplikat tersisa"""
    print_header("VERIFIKASI HASIL CLEANUP")
    
    try:
        conn = sqlite3.connect('flood_system.db')
        cursor = conn.cursor()
        
        # Check for remaining exact duplicates
        cursor.execute('''
            SELECT 
                "Timestamp", "Alamat", "Nama Pelapor", "Tinggi Banjir",
                COUNT(*) as count
            FROM flood_reports 
            GROUP BY "Timestamp", "Alamat", "Nama Pelapor", "Tinggi Banjir"
            HAVING count > 1
        ''')
        
        remaining = cursor.fetchall()
        
        if len(remaining) == 0:
            print("SUCCESS: No duplicates found!")
            print("Database is clean.")
            
            # Show statistics
            cursor.execute('SELECT COUNT(*) FROM flood_reports')
            total = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT "Alamat") FROM flood_reports')
            unique_addresses = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT "Nama Pelapor") FROM flood_reports')
            unique_reporters = cursor.fetchone()[0]
            
            print(f"\nDatabase Statistics:")
            print(f"  Total reports:     {total}")
            print(f"  Unique addresses:  {unique_addresses}")
            print(f"  Unique reporters:  {unique_reporters}")
            
            success = True
        else:
            print(f"WARNING: Still found {len(remaining)} duplicate groups:")
            for dup in remaining[:5]:
                print(f"  - {dup}")
            success = False
        
        conn.close()
        return success
        
    except Exception as e:
        print(f"ERROR: Verification failed: {e}")
        return False

def show_sample_reports():
    """Tampilkan sample reports setelah cleanup"""
    print_header("SAMPLE REPORTS (Last 5)")
    
    try:
        conn = sqlite3.connect('flood_system.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, "Timestamp", "Alamat", "Nama Pelapor", "Tinggi Banjir"
            FROM flood_reports 
            ORDER BY id DESC 
            LIMIT 5
        ''')
        
        reports = cursor.fetchall()
        
        if reports:
            for i, report in enumerate(reports, 1):
                print(f"\n{i}. ID: {report['id']}")
                print(f"   Time: {report['Timestamp']}")
                print(f"   Address: {report['Alamat'][:50]}...")
                print(f"   Reporter: {report['Nama Pelapor']}")
                print(f"   Height: {report['Tinggi Banjir']}")
        else:
            print("No reports found")
        
        conn.close()
        
    except Exception as e:
        print(f"ERROR: {e}")

def main():
    """Main execution"""
    print("\n" + "="*70)
    print("  DATABASE DUPLICATE CLEANUP TOOL")
    print("  Flood Warning System - Enhanced Version")
    print("="*70)
    
    # Check database exists
    if not os.path.exists('flood_system.db'):
        print("\nERROR: Database file 'flood_system.db' not found!")
        print("Make sure you're running this script from the project root directory.")
        return
    
    # Step 1: Analyze
    dup_groups, dup_records = analyze_duplicates()
    
    if dup_groups == 0:
        print("\n" + "="*70)
        print("No duplicates found! Database is already clean.")
        print("="*70)
        return
    
    # Step 2: Confirm
    print("\n" + "="*70)
    print("CONFIRMATION REQUIRED")
    print("="*70)
    print(f"This will remove {dup_records} duplicate records")
    print("A backup will be created automatically")
    response = input("\nProceed with cleanup? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("\nCleanup cancelled by user")
        return
    
    # Step 3: Backup
    backup_file = backup_database()
    if not backup_file:
        print("\nERROR: Cannot proceed without backup")
        return
    
    # Step 4: Clean
    deleted = clean_exact_duplicates()
    
    if deleted > 0:
        # Step 5: Verify
        is_clean = verify_cleanup()
        
        # Step 6: Show sample
        show_sample_reports()
        
        # Final summary
        print("\n" + "="*70)
        if is_clean:
            print("SUCCESS: DATABASE CLEANUP COMPLETED!")
        else:
            print("WARNING: CLEANUP COMPLETED WITH WARNINGS")
        print("="*70)
        print(f"  Backup file: {backup_file}")
        print(f"  Records removed: {deleted}")
        print("="*70)
        
        if is_clean:
            print("\nNext steps:")
            print("  1. Test your application: python app.py")
            print("  2. Submit a test report to verify no duplicates")
            print("  3. Check Google Sheets sync if enabled")
            print("\nIf everything works, you can delete the backup file later.")
        else:
            print("\nPlease review the warnings above.")
            print("You may want to manually check the remaining duplicates.")
    else:
        print("\nNo changes were made to the database")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCleanup cancelled by user")
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()