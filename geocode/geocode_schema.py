#!/usr/bin/env python3
"""
FIX DATABASE SCHEMA FOR GEOCODING
==================================

Script ini akan menambahkan kolom yang diperlukan untuk geocoding:
- geocode_confidence (TEXT): HIGH, MEDIUM, LOW
- geocode_method (TEXT): OSM, Manual, etc
- geocoded_at (DATETIME): Timestamp kapan geocoding dilakukan

BACKUP OTOMATIS:
- Database akan di-backup sebelum perubahan
- Backup disimpan dengan timestamp

CARA PENGGUNAAN:
  python fix_geocode_schema.py                    # Fix database
  python fix_geocode_schema.py --dry-run          # Preview tanpa changes
  python fix_geocode_schema.py --db custom.db     # Custom database path
"""

import sqlite3
import os
import sys
import shutil
import argparse
from datetime import datetime


class DatabaseFixer:
    """Fix database schema untuk geocoding"""
    
    def __init__(self, db_path='flood_system.db', dry_run=False):
        self.db_path = db_path
        self.dry_run = dry_run
        
        # Kolom yang harus ada
        self.required_columns = {
            'geocode_confidence': ('TEXT', 'Tingkat kepercayaan: HIGH, MEDIUM, LOW'),
            'geocode_method': ('TEXT', 'Metode geocoding: OSM, Manual, Google, etc'),
            'geocoded_at': ('DATETIME', 'Timestamp kapan geocoding dilakukan')
        }
    
    def print_header(self):
        """Print header"""
        print("\n" + "="*70)
        print("  DATABASE SCHEMA FIXER FOR GEOCODING")
        print("="*70 + "\n")
    
    def check_database(self):
        """Check apakah database ada"""
        if not os.path.exists(self.db_path):
            print(f"❌ Database tidak ditemukan: {self.db_path}")
            sys.exit(1)
        
        print(f"✅ Database ditemukan: {self.db_path}")
        
        # Get file size
        size = os.path.getsize(self.db_path)
        size_mb = size / (1024 * 1024)
        print(f"   📊 Size: {size_mb:.2f} MB")
    
    def backup_database(self):
        """Backup database"""
        if self.dry_run:
            print("\n🔍 DRY RUN - Database tidak akan di-backup")
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{self.db_path}.backup_{timestamp}"
        
        print(f"\n💾 Membuat backup database...")
        print(f"   Backup: {backup_path}")
        
        try:
            shutil.copy2(self.db_path, backup_path)
            backup_size = os.path.getsize(backup_path) / (1024 * 1024)
            print(f"   ✅ Backup berhasil ({backup_size:.2f} MB)")
            return backup_path
        except Exception as e:
            print(f"   ❌ Backup gagal: {e}")
            sys.exit(1)
    
    def get_current_columns(self):
        """Get kolom yang ada saat ini"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(flood_reports)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        conn.close()
        return columns
    
    def analyze_schema(self):
        """Analisa schema saat ini"""
        print("\n📋 ANALISIS SCHEMA SAAT INI")
        print("="*70)
        
        current_cols = self.get_current_columns()
        
        print(f"\n✅ Kolom yang sudah ada ({len(current_cols)}):")
        for col_name, col_type in sorted(current_cols.items()):
            print(f"   - {col_name} ({col_type})")
        
        # Check kolom yang diperlukan
        missing = []
        exists = []
        
        for col_name, (col_type, description) in self.required_columns.items():
            if col_name in current_cols:
                exists.append(col_name)
            else:
                missing.append((col_name, col_type, description))
        
        print(f"\n✅ Kolom geocoding yang sudah ada ({len(exists)}):")
        if exists:
            for col in exists:
                print(f"   - {col}")
        else:
            print("   (tidak ada)")
        
        print(f"\n❌ Kolom geocoding yang BELUM ada ({len(missing)}):")
        if missing:
            for col_name, col_type, description in missing:
                print(f"   - {col_name} ({col_type})")
                print(f"     → {description}")
        else:
            print("   (semua kolom sudah ada)")
        
        print("\n" + "="*70)
        
        return missing, exists
    
    def add_columns(self, missing_columns):
        """Tambahkan kolom yang hilang"""
        if not missing_columns:
            print("\n✅ Semua kolom sudah ada, tidak perlu perubahan!\n")
            return True
        
        if self.dry_run:
            print("\n🔍 DRY RUN - Kolom yang akan ditambahkan:")
            for col_name, col_type, description in missing_columns:
                print(f"   ALTER TABLE flood_reports ADD COLUMN {col_name} {col_type};")
                print(f"   → {description}")
            print("\n🔍 DRY RUN - Tidak ada perubahan dibuat\n")
            return True
        
        print("\n🔧 MENAMBAHKAN KOLOM")
        print("="*70)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        success_count = 0
        
        for col_name, col_type, description in missing_columns:
            try:
                sql = f"ALTER TABLE flood_reports ADD COLUMN {col_name} {col_type}"
                print(f"\n📝 {sql}")
                cursor.execute(sql)
                conn.commit()
                print(f"   ✅ Berhasil ditambahkan")
                print(f"   → {description}")
                success_count += 1
            except Exception as e:
                print(f"   ❌ Gagal: {e}")
                conn.rollback()
        
        conn.close()
        
        print("\n" + "="*70)
        print(f"\n✅ {success_count}/{len(missing_columns)} kolom berhasil ditambahkan\n")
        
        return success_count == len(missing_columns)
    
    def verify_changes(self):
        """Verifikasi perubahan"""
        print("🔍 VERIFIKASI PERUBAHAN")
        print("="*70)
        
        current_cols = self.get_current_columns()
        
        all_present = True
        for col_name, (col_type, description) in self.required_columns.items():
            if col_name in current_cols:
                print(f"✅ {col_name} ({current_cols[col_name]})")
            else:
                print(f"❌ {col_name} - MASIH BELUM ADA!")
                all_present = False
        
        print("="*70)
        
        if all_present:
            print("\n✅ SEMUA KOLOM BERHASIL DITAMBAHKAN!\n")
            print("🎉 Database siap untuk geocoding!\n")
        else:
            print("\n⚠️  Beberapa kolom masih belum ada\n")
        
        return all_present
    
    def run(self):
        """Jalankan perbaikan"""
        self.print_header()
        self.check_database()
        
        # Analisa
        missing, exists = self.analyze_schema()
        
        if not missing:
            print("\n✅ Schema sudah lengkap!\n")
            return True
        
        # Konfirmasi
        if not self.dry_run:
            print(f"\n⚠️  {len(missing)} kolom akan ditambahkan ke database")
            response = input("\nLanjutkan? (y/n): ").lower()
            if response != 'y':
                print("\n❌ Dibatalkan\n")
                return False
        
        # Backup
        backup_path = self.backup_database()
        
        # Add columns
        success = self.add_columns(missing)
        
        if not success:
            print("\n⚠️  Beberapa kolom gagal ditambahkan")
            if backup_path:
                print(f"   Backup tersedia di: {backup_path}")
            return False
        
        # Verify
        if not self.dry_run:
            verified = self.verify_changes()
            
            if verified:
                print("📚 LANGKAH SELANJUTNYA:")
                print("   1. Jalankan: python geocode_reports.py --dry-run")
                print("   2. Jika OK, jalankan: python geocode_reports.py")
                print()
                
                if backup_path:
                    print(f"💾 Backup disimpan di: {backup_path}")
                    print()
            
            return verified
        
        return True


def main():
    parser = argparse.ArgumentParser(
        description='Fix database schema untuk geocoding',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python fix_geocode_schema.py              # Fix database
  python fix_geocode_schema.py --dry-run    # Preview tanpa changes
  python fix_geocode_schema.py --db custom.db   # Custom database
        """
    )
    
    parser.add_argument('--dry-run', action='store_true', 
                    help='Preview mode (tidak membuat perubahan)')
    parser.add_argument('--db', type=str, default='flood_system.db',
                    help='Path ke database (default: flood_system.db)')
    
    args = parser.parse_args()
    
    fixer = DatabaseFixer(args.db, args.dry_run)
    
    try:
        success = fixer.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Dibatalkan oleh user\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()