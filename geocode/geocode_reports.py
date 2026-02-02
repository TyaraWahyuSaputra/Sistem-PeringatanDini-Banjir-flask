#!/usr/bin/env python3
"""
BATCH GEOCODING SCRIPT FOR FLOOD REPORTS - IMPROVED
====================================================

PRINSIP UTAMA:
- TIDAK MEMAKSA geocoding jika alamat tidak valid
- Hanya menyimpan koordinat yang AKURAT dan TERVERIFIKASI
- Validasi hasil dalam batas Indonesia/Jawa Tengah
- Support format alamat administratif Indonesia (kelurahan, kecamatan, kabupaten, provinsi)

CARA PENGGUNAAN:
  python geocode_reports.py --dry-run       # Preview tanpa update
  python geocode_reports.py                 # Geocode semua
  python geocode_reports.py --interactive   # Konfirmasi manual setiap hasil
  python geocode_reports.py --limit 5       # Test 5 laporan
  python geocode_reports.py --ids 1,5,10    # Geocode laporan tertentu
"""

import sys
import os
import sqlite3
import time
import argparse
from datetime import datetime
import shutil
import requests

# KONFIGURASI
OSM_USER_AGENT = "FloodWarningSystem/2.0 (tyarawahyusaputra@gmail.com)"
OSM_BASE_URL = "https://nominatim.openstreetmap.org"
OSM_RATE_LIMIT = 1.1  # detik

# BATAS KOORDINAT (untuk validasi)
INDONESIA_BOUNDS = {'lat_min': -11.0, 'lat_max': 6.0, 'lng_min': 95.0, 'lng_max': 141.0}


class OSMGeocoder:
    """OSM Nominatim Geocoder dengan validasi ketat"""
    
    def __init__(self, user_agent=OSM_USER_AGENT, base_url=OSM_BASE_URL):
        self.user_agent = user_agent
        self.base_url = base_url
        self.rate_limit_delay = OSM_RATE_LIMIT
        self.last_request_time = 0
    
    def _respect_rate_limit(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    def test_connection(self):
        try:
            response = requests.get(f"{self.base_url}/status.php",
                                    headers={'User-Agent': self.user_agent}, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def geocode_address(self, address, country_code="id"):
        """
        Geocode alamat - TIDAK MEMAKSA jika tidak valid
        
        Returns: (lat, lng, confidence, error)
        """
        if not address or len(address.strip()) < 5:
            return None, None, None, "Alamat terlalu pendek (min 5 karakter)"
        
        try:
            self._respect_rate_limit()
            
            # Clean and format address for better OSM search
            formatted_address = self._format_address_for_osm(address)
            
            params = {
                'q': formatted_address,
                'format': 'json',
                'limit': 5,  # Get top 5 results for better accuracy
                'countrycodes': country_code,
                'addressdetails': 1
            }
            
            response = requests.get(
                f"{self.base_url}/search",
                params=params,
                headers={'User-Agent': self.user_agent},
                timeout=15
            )
            
            if response.status_code != 200:
                return None, None, None, f"HTTP {response.status_code}"
            
            data = response.json()
            
            if not data:
                return None, None, None, "❌ Alamat tidak ditemukan di OpenStreetMap"
            
            # Find best match from results
            best_result = self._select_best_result(data, address)
            
            if not best_result:
                return None, None, None, "❌ Tidak ada hasil yang sesuai"
            
            lat = float(best_result['lat'])
            lon = float(best_result['lon'])
            
            # VALIDASI: Harus dalam batas Indonesia
            if not self._is_valid_indonesia(lat, lon):
                return None, None, None, f"❌ Koordinat di luar Indonesia: ({lat:.4f}, {lon:.4f})"
            
            confidence = self._calculate_confidence(best_result)
            
            return lat, lon, confidence, None
            
        except requests.exceptions.Timeout:
            return None, None, None, "⏱️ Timeout (15 detik)"
        except requests.exceptions.ConnectionError:
            return None, None, None, "🌐 Koneksi error - periksa internet"
        except Exception as e:
            return None, None, None, f"⚠️ Error: {str(e)}"
    
    def _format_address_for_osm(self, address):
        """Format Indonesian address for better OSM search"""
        # Remove common prefixes
        address = address.lower().strip()
        address = address.replace('desa ', '').replace('kelurahan ', '')
        address = address.replace('kecamatan ', '').replace('kec. ', '')
        address = address.replace('kabupaten ', '').replace('kab. ', '')
        address = address.replace('kota ', '')
        address = address.replace('provinsi ', '').replace('prov. ', '')
        
        # Add "Indonesia" at the end if not present
        if 'indonesia' not in address:
            address = f"{address}, Indonesia"
        
        return address
    
    def _select_best_result(self, results, original_address):
        """Select best matching result from multiple results - untuk seluruh Indonesia"""
        if not results:
            return None
        
        # Extract key location terms from original address
        original_lower = original_address.lower()
        
        # Extract words from address (potential city/regency/province names)
        address_words = [word.strip() for word in original_lower.replace(',', ' ').split() if len(word.strip()) > 2]
        
        # Score each result
        scored_results = []
        for result in results:
            score = 0
            display_name = result.get('display_name', '').lower()
            address_dict = result.get('address', {})
            
            # Prefer results in Indonesia (should already be filtered by countrycodes)
            if 'indonesia' in display_name:
                score += 30
            
            # Match address words with display name
            matched_words = 0
            for word in address_words:
                if word in display_name:
                    matched_words += 1
                    score += 20
            
            # Bonus for matching multiple words
            if matched_words >= 3:
                score += 30
            elif matched_words >= 2:
                score += 15
            
            # Prefer more specific locations (village/district level)
            # This ensures we get the most specific match
            if address_dict.get('village') or address_dict.get('hamlet'):
                score += 40  # Desa/Dusun (paling spesifik)
            elif address_dict.get('suburb') or address_dict.get('neighbourhood'):
                score += 35  # Kelurahan/Lingkungan
            elif address_dict.get('city_district') or address_dict.get('district'):
                score += 30  # Kecamatan
            elif address_dict.get('city') or address_dict.get('town'):
                score += 20  # Kota/Kabupaten
            elif address_dict.get('county'):
                score += 15  # Kabupaten
            elif address_dict.get('state'):
                score += 10  # Provinsi
            
            # Higher OSM importance = better quality match
            importance = float(result.get('importance', 0))
            score += importance * 25
            
            # Prefer exact matches in address components
            province = address_dict.get('state', '').lower()
            city = address_dict.get('city', '').lower() or address_dict.get('town', '').lower()
            county = address_dict.get('county', '').lower()
            district = address_dict.get('city_district', '').lower()
            village = address_dict.get('village', '').lower() or address_dict.get('suburb', '').lower()
            
            for word in address_words:
                if word == province or word == city or word == county:
                    score += 25
                if word == district:
                    score += 30
                if word == village:
                    score += 35
            
            scored_results.append((score, result))
        
        # Sort by score (highest first)
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        # Return best result
        return scored_results[0][1] if scored_results else results[0]
    
    def _is_valid_indonesia(self, lat, lon):
        return (INDONESIA_BOUNDS['lat_min'] <= lat <= INDONESIA_BOUNDS['lat_max'] and
                INDONESIA_BOUNDS['lng_min'] <= lon <= INDONESIA_BOUNDS['lng_max'])
    
    def _calculate_confidence(self, result):
        """Hitung confidence: HIGH, MEDIUM, LOW"""
        address = result.get('address', {})
        
        # HIGH: alamat spesifik
        if any(k in address for k in ['house_number', 'building', 'shop', 'amenity']):
            return "HIGH"
        
        # MEDIUM: jalan/desa
        if any(k in address for k in ['road', 'village', 'suburb', 'hamlet']):
            return "MEDIUM"
        
        # LOW: kota/provinsi
        return "LOW"


class GeocodeBatchProcessor:
    """Batch processor dengan validasi ketat"""
    
    def __init__(self, db_path='flood_system.db', dry_run=False, interactive=False):
        self.db_path = db_path
        self.dry_run = dry_run
        self.interactive = interactive
        self.geocoder = OSMGeocoder()
        
        self.stats = {
            'total': 0, 'success': 0, 'failed': 0, 'skipped': 0,
            'already_geocoded': 0, 'not_found': 0, 'out_of_bounds': 0, 'invalid': 0
        }
        
        self._print_header()
        self._check_geocoder()
        self._check_database()
    
    def _print_header(self):
        print("\n" + "="*70)
        print("  FLOOD REPORT GEOCODING SYSTEM v2.0")
        print("  Prinsip: TIDAK memaksa jika alamat tidak valid")
        print("="*70 + "\n")
    
    def _check_geocoder(self):
        print("🌍 Testing OSM connection...", end=" ", flush=True)
        if self.geocoder.test_connection():
            print("✅ Connected")
        else:
            print("❌ Failed")
            response = input("\nContinue anyway? (y/n): ")
            if response.lower() != 'y':
                sys.exit(1)
    
    def _check_database(self):
        print("💾 Checking database...", end=" ", flush=True)
        
        if not os.path.exists(self.db_path):
            print(f"❌ Not found: {self.db_path}")
            sys.exit(1)
        
        # Check schema
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(flood_reports)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        
        has_lat = 'latitude' in columns
        has_lng = 'longitude' in columns
        
        if not has_lat or not has_lng:
            print("❌ Missing columns")
            if not self.dry_run:
                response = input("\nAdd latitude & longitude columns? (y/n): ")
                if response.lower() == 'y':
                    self._add_columns()
                else:
                    sys.exit(1)
        else:
            print("✅ Schema OK")
    
    def _add_columns(self):
        print("\n📝 Updating schema...")
        self._backup_database()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("ALTER TABLE flood_reports ADD COLUMN latitude REAL")
            print("   ✅ Added latitude")
        except:
            print("   ℹ️  latitude exists")
        
        try:
            cursor.execute("ALTER TABLE flood_reports ADD COLUMN longitude REAL")
            print("   ✅ Added longitude")
        except:
            print("   ℹ️  longitude exists")
        
        try:
            cursor.execute("ALTER TABLE flood_reports ADD COLUMN geocode_confidence TEXT")
            print("   ✅ Added geocode_confidence")
        except:
            print("   ℹ️  geocode_confidence exists")
        
        try:
            cursor.execute("ALTER TABLE flood_reports ADD COLUMN geocode_method TEXT")
            print("   ✅ Added geocode_method")
        except:
            print("   ℹ️  geocode_method exists")
        
        try:
            cursor.execute("ALTER TABLE flood_reports ADD COLUMN geocoded_at DATETIME")
            print("   ✅ Added geocoded_at")
        except:
            print("   ℹ️  geocoded_at exists")
        
        conn.commit()
        conn.close()
        print("   ✅ Schema updated\n")
    
    def _backup_database(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"backups/flood_system_backup_{timestamp}.db"
        
        os.makedirs('backups', exist_ok=True)
        
        try:
            shutil.copy2(self.db_path, backup_path)
            print(f"   💾 Backup: {backup_path}")
        except Exception as e:
            print(f"   ⚠️ Backup failed: {e}")
    
    def get_reports_to_geocode(self, force=False, ids=None):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if ids:
            placeholders = ','.join('?' * len(ids))
            cursor.execute(f'''
                SELECT id, "Alamat", latitude, longitude 
                FROM flood_reports 
                WHERE id IN ({placeholders})
            ''', ids)
        elif force:
            cursor.execute('SELECT id, "Alamat", latitude, longitude FROM flood_reports')
        else:
            cursor.execute('''
                SELECT id, "Alamat", latitude, longitude 
                FROM flood_reports 
                WHERE latitude IS NULL OR longitude IS NULL
            ''')
        
        reports = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return reports
    
    def update_report(self, report_id, lat, lng, confidence):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE flood_reports 
                SET latitude = ?, longitude = ?, geocode_confidence = ?, 
                    geocode_method = 'OSM', geocoded_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (lat, lng, confidence, report_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"   ❌ DB Error: {e}")
            return False
    
    def process_reports(self, force=False, limit=None, ids=None):
        print("\n" + "="*70)
        print("  PROCESSING REPORTS")
        print("="*70 + "\n")
        
        reports = self.get_reports_to_geocode(force=force, ids=ids)
        
        if not reports:
            print("ℹ️  No reports to geocode\n")
            return
        
        total = len(reports)
        if limit:
            reports = reports[:limit]
            total = len(reports)
        
        self.stats['total'] = total
        
        print(f"📊 Reports to process: {total}")
        if self.dry_run:
            print("🔍 DRY RUN - No database changes\n")
        if self.interactive:
            print("🤝 INTERACTIVE - Confirm each result\n")
        
        if not self.dry_run and not self.interactive:
            self._backup_database()
            print()
        
        # Process
        for idx, report in enumerate(reports, 1):
            report_id = report['id']
            address = report.get('Alamat', '').strip()
            
            # Skip if already geocoded
            if not force and report.get('latitude') and report.get('longitude'):
                self.stats['already_geocoded'] += 1
                self.stats['skipped'] += 1
                print(f"[{idx}/{total}] ⏭️  #{report_id} already geocoded")
                continue
            
            # Progress
            progress = (idx / total) * 100
            print(f"\n{'='*70}")
            print(f"[{idx}/{total}] ({progress:.1f}%) Report #{report_id}")
            print(f"{'='*70}")
            print(f"📍 Address: {address}")
            
            # Validate address
            if len(address) < 5:
                print(f"❌ Address too short")
                self.stats['invalid'] += 1
                self.stats['failed'] += 1
                continue
            
            # Geocode
            print(f"🌍 Geocoding...", end=" ", flush=True)
            lat, lng, confidence, error = self.geocoder.geocode_address(address)
            
            if lat and lng:
                print(f"✅")
                print(f"   📌 Coordinates: {lat:.6f}, {lng:.6f}")
                print(f"   🎯 Confidence: {confidence}")
                
                # Google Maps link
                maps_url = f"https://www.google.com/maps?q={lat},{lng}"
                print(f"   🗺️  View: {maps_url}")
                
                # Interactive confirmation
                if self.interactive:
                    response = input("\n   Accept this result? (y/n): ").lower()
                    if response != 'y':
                        print(f"   ⏭️  Skipped by user")
                        self.stats['skipped'] += 1
                        continue
                
                # Update database
                if not self.dry_run:
                    if self.update_report(report_id, lat, lng, confidence):
                        self.stats['success'] += 1
                        print(f"   💾 Database updated")
                    else:
                        self.stats['failed'] += 1
                else:
                    self.stats['success'] += 1
                    print(f"   ℹ️  [DRY RUN] Would update")
                    
            else:
                print(f"❌")
                print(f"   {error}")
                
                if "tidak ditemukan" in error or "not found" in error:
                    self.stats['not_found'] += 1
                elif "luar" in error or "bounds" in error:
                    self.stats['out_of_bounds'] += 1
                else:
                    self.stats['invalid'] += 1
                
                self.stats['failed'] += 1
            
            # Rate limit
            if idx < total:
                time.sleep(OSM_RATE_LIMIT)
        
        self._print_summary()
    
    def _print_summary(self):
        print("\n" + "="*70)
        print("  SUMMARY")
        print("="*70 + "\n")
        
        print(f"📊 Total:     {self.stats['total']}")
        print(f"✅ Success:   {self.stats['success']}")
        print(f"❌ Failed:    {self.stats['failed']}")
        
        if self.stats['failed'] > 0:
            print(f"\n   Breakdown:")
            if self.stats['not_found'] > 0:
                print(f"   - Not found:      {self.stats['not_found']}")
            if self.stats['out_of_bounds'] > 0:
                print(f"   - Out of bounds:  {self.stats['out_of_bounds']}")
            if self.stats['invalid'] > 0:
                print(f"   - Invalid:        {self.stats['invalid']}")
        
        if self.stats['skipped'] > 0:
            print(f"\n⏭️  Skipped:  {self.stats['skipped']}")
        
        # Success rate
        attempted = self.stats['total'] - self.stats['already_geocoded']
        if attempted > 0:
            rate = (self.stats['success'] / attempted) * 100
            print(f"\n📈 Success Rate: {rate:.1f}%")
        
        if self.dry_run:
            print(f"\n🔍 DRY RUN - No changes made")
        
        print("\n" + "="*70 + "\n")
        
        # Tips
        if self.stats['not_found'] > 0:
            print("💡 TIPS:")
            print("   - Check for typos in addresses")
            print("   - Make addresses more specific")
            print("   - Format: 'Desa/Kelurahan, Kecamatan, Kabupaten/Kota, Provinsi'")
            print()


def main():
    parser = argparse.ArgumentParser(
        description='Geocode flood reports (TIDAK memaksa jika invalid)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python geocode_reports.py --dry-run       # Preview
  python geocode_reports.py                 # Run
  python geocode_reports.py --interactive   # Confirm each
  python geocode_reports.py --limit 5       # Test 5
  python geocode_reports.py --ids 1,5,10    # Specific IDs
        """
    )
    
    parser.add_argument('--dry-run', action='store_true', help='Preview mode')
    parser.add_argument('--force', action='store_true', help='Re-geocode all')
    parser.add_argument('--limit', type=int, help='Limit count')
    parser.add_argument('--ids', type=str, help='Report IDs (e.g., 1,5,10)')
    parser.add_argument('--db', type=str, default='flood_system.db', help='DB path')
    parser.add_argument('--interactive', action='store_true', help='Confirm each')
    
    args = parser.parse_args()
    
    # Parse IDs
    ids = None
    if args.ids:
        try:
            ids = [int(x.strip()) for x in args.ids.split(',')]
        except ValueError:
            print("❌ Invalid ID format. Use: --ids 1,5,10")
            sys.exit(1)
    
    # Process
    processor = GeocodeBatchProcessor(args.db, args.dry_run, args.interactive)
    
    try:
        processor.process_reports(args.force, args.limit, ids)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()