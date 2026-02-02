#!/usr/bin/env python3
"""
Batch Geocoding Script for OpenStreetMap
Geocode all pending flood reports that don't have coordinates
FIXED: Pure OSM, better error handling, progress tracking
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from utils.helpers import OSMGeocoder
import sqlite3
import time
import logging

def setup_logging():
    """Setup logging for batch geocoding"""
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/batch_geocode.log', encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def print_header():
    """Print fancy header"""
    print("\n" + "=" * 70)
    print("   BATCH GEOCODING WITH OPENSTREETMAP")
    print("=" * 70 + "\n")

def get_pending_reports_info():
    """Get information about pending reports"""
    logger.info("📊 Checking database for pending geocoding...")
    
    try:
        conn = sqlite3.connect('flood_system.db')
        cursor = conn.cursor()
        
        # Total reports
        cursor.execute("SELECT COUNT(*) FROM flood_reports")
        total = cursor.fetchone()[0]
        
        # Reports with coordinates
        cursor.execute("""
            SELECT COUNT(*) FROM flood_reports 
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """)
        geocoded = cursor.fetchone()[0]
        
        # Reports without coordinates (pending)
        cursor.execute("""
            SELECT COUNT(*) FROM flood_reports 
            WHERE (latitude IS NULL OR longitude IS NULL)
              AND (is_geocoded IS NULL OR is_geocoded = 0)
        """)
        pending = cursor.fetchone()[0]
        
        # Failed geocoding attempts
        cursor.execute("""
            SELECT COUNT(*) FROM flood_reports 
            WHERE is_geocoded = -1
        """)
        failed = cursor.fetchone()[0]
        
        # Get sample pending reports
        cursor.execute("""
            SELECT id, "Alamat" 
            FROM flood_reports 
            WHERE (latitude IS NULL OR longitude IS NULL)
              AND (is_geocoded IS NULL OR is_geocoded = 0)
            LIMIT 5
        """)
        sample_pending = cursor.fetchall()
        
        conn.close()
        
        logger.info(f"   Total reports: {total}")
        logger.info(f"   ✅ Geocoded: {geocoded}")
        logger.info(f"   ⏳ Pending: {pending}")
        logger.info(f"   ❌ Failed: {failed}")
        
        if total > 0:
            percentage = (geocoded / total) * 100
            logger.info(f"   📊 Coverage: {percentage:.1f}%")
        
        if sample_pending:
            logger.info(f"📋 Sample pending reports:")
            for report_id, address in sample_pending:
                logger.info(f"   #{report_id}: {address[:60]}...")
        
        return {
            'total': total,
            'geocoded': geocoded,
            'pending': pending,
            'failed': failed,
            'has_pending': pending > 0
        }
        
    except Exception as e:
        logger.error(f"❌ Error checking database: {e}")
        return None

def confirm_batch_geocoding(info):
    """Ask user confirmation before starting"""
    if not info or not info['has_pending']:
        logger.info("\n✅ No pending reports to geocode")
        return False
    
    print("\n" + "=" * 70)
    print("⚠️  CONFIRMATION REQUIRED")
    print("=" * 70)
    print(f"   You are about to geocode {info['pending']} reports")
    print(f"   Using: OpenStreetMap Nominatim (FREE)")
    print(f"   Rate limit: 1 request per second (OSM policy)")
    print(f"   Estimated time: ~{info['pending'] * 1.2:.1f} seconds")
    print(f"   User-Agent: {Config.OSM_USER_AGENT[:40]}...")
    
    response = input("\n   Continue? (yes/no): ").strip().lower()
    
    return response in ['yes', 'y']

def batch_geocode_reports(limit=None):
    """Main batch geocoding function with OSM"""
    logger.info("\n🚀 STARTING BATCH GEOCODING WITH OPENSTREETMAP")
    
    # Initialize OSM geocoder
    logger.info("Initializing OSM Geocoder...")
    try:
        geocoder = OSMGeocoder(
            user_agent=Config.OSM_USER_AGENT,
            base_url=Config.OSM_BASE_URL
        )
        
        # Test connection first
        if not geocoder.test_connection():
            logger.error("❌ OSM connection test failed!")
            return False
        
        logger.info("✅ OSM Geocoder ready")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize OSM geocoder: {e}")
        return False
    
    # Get pending reports
    conn = sqlite3.connect('flood_system.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = """
        SELECT id, "Alamat" FROM flood_reports 
        WHERE (latitude IS NULL OR longitude IS NULL)
          AND (is_geocoded = 0 OR is_geocoded IS NULL)
    """
    
    if limit:
        query += f' LIMIT {limit}'
    
    cursor.execute(query)
    reports = cursor.fetchall()
    
    total = len(reports)
    if total == 0:
        conn.close()
        logger.info("✅ All reports already geocoded")
        return True
    
    logger.info(f"\n📍 Found {total} reports to geocode")
    
    success_count = 0
    failed_count = 0
    
    start_time = time.time()
    
    for idx, report in enumerate(reports, 1):
        report_id = report['id']
        address = report['Alamat']
        
        logger.info(f"\n[{idx}/{total}] Report #{report_id}")
        logger.info(f"    Address: {address[:60]}...")
        
        try:
            # Geocode with OSM
            lat, lng, error = geocoder.geocode_address(address, "id")
            
            if lat and lng:
                # Update database
                cursor.execute('''
                    UPDATE flood_reports 
                    SET latitude = ?, longitude = ?, is_geocoded = 1
                    WHERE id = ?
                ''', (lat, lng, report_id))
                
                conn.commit()
                success_count += 1
                logger.info(f"    ✅ Success: ({lat:.6f}, {lng:.6f})")
                logger.info(f"    🔗 https://www.openstreetmap.org/?mlat={lat}&mlon={lng}")
            else:
                # Mark as failed
                cursor.execute('''
                    UPDATE flood_reports 
                    SET is_geocoded = -1
                    WHERE id = ?
                ''', (report_id,))
                
                conn.commit()
                failed_count += 1
                logger.info(f"    ❌ Failed: {error}")
            
            # OSM rate limiting is handled by the geocoder class
            # Additional safety delay for batch processing
            if idx < total:
                time.sleep(0.2)  # Small additional buffer
                
        except Exception as e:
            logger.error(f"    ❌ Error: {str(e)}")
            failed_count += 1
        
        # Progress indicator
        if idx % 5 == 0:
            elapsed = time.time() - start_time
            rate = idx / elapsed if elapsed > 0 else 0
            remaining = (total - idx) / rate if rate > 0 else 0
            logger.info(f"\n    ⏱️  Progress: {idx}/{total} ({idx/total*100:.1f}%)")
            logger.info(f"    📈 Rate: {rate:.2f} req/sec")
            logger.info(f"    🕐 ETA: {remaining:.0f} seconds remaining")
    
    conn.close()
    
    # Final summary
    elapsed_total = time.time() - start_time
    
    logger.info("\n" + "=" * 70)
    logger.info("📊 BATCH GEOCODING COMPLETED")
    logger.info("=" * 70)
    logger.info(f"   Total processed: {total}")
    logger.info(f"   ✅ Success: {success_count}")
    logger.info(f"   ❌ Failed: {failed_count}")
    logger.info(f"   ⏱️  Time taken: {elapsed_total:.1f}s")
    logger.info(f"   📈 Average rate: {total/elapsed_total:.2f} req/sec")
    
    if success_count > 0:
        success_rate = (success_count / total) * 100
        logger.info(f"   📊 Success rate: {success_rate:.1f}%")
    
    return success_count > 0

def show_geocoded_sample():
    """Show sample of geocoded reports"""
    logger.info("\n📍 SAMPLE GEOCODED REPORTS")
    
    try:
        conn = sqlite3.connect('flood_system.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, "Alamat", "Tinggi Banjir", latitude, longitude
            FROM flood_reports 
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            ORDER BY id DESC
            LIMIT 5
        """)
        
        reports = cursor.fetchall()
        
        if reports:
            logger.info(f"   Found {len(reports)} geocoded reports:")
            for report in reports:
                report_id, address, height, lat, lng = report
                logger.info(f"\n   #{report_id}: {address[:50]}...")
                logger.info(f"   Tinggi: {height}")
                logger.info(f"   Coordinates: ({lat:.6f}, {lng:.6f})")
                logger.info(f"   🔗 OSM: https://www.openstreetmap.org/?mlat={lat}&mlon={lng}")
                logger.info(f"   🗺️  Google: https://maps.google.com/?q={lat},{lng}")
        else:
            logger.info("   No geocoded reports found")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")

def main():
    """Main execution function"""
    print_header()
    
    # Check configuration
    logger.info("📋 CONFIGURATION CHECK")
    logger.info("=" * 70)
    
    logger.info(f"   Geocoding Enabled: {Config.GEOCODING_ENABLED}")
    logger.info(f"   Provider: {Config.GEOCODING_PROVIDER}")
    logger.info(f"   OSM User-Agent: {Config.OSM_USER_AGENT[:40]}...")
    logger.info(f"   OSM Rate Limit: {Config.OSM_RATE_LIMIT_DELAY}s")
    
    if not Config.GEOCODING_ENABLED:
        logger.error("\n❌ Geocoding is disabled in config.py")
        logger.error("   Set GEOCODING_ENABLED = True to continue")
        return
    
    # Check database
    if not os.path.exists('flood_system.db'):
        logger.error("\n❌ Database not found!")
        logger.error("   Create database first: python models/database.py")
        return
    
    # Get pending reports info
    info = get_pending_reports_info()
    
    if not info:
        logger.error("\n❌ Failed to check database")
        return
    
    if not info['has_pending']:
        logger.info("\n✅ All reports already geocoded!")
        show_geocoded_sample()
        return
    
    # Confirm before starting
    if not confirm_batch_geocoding(info):
        logger.info("\n⚠️  Batch geocoding cancelled by user")
        return
    
    # Parse command line arguments for limit
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            logger.info(f"\n⚙️  Limit set to {limit} reports")
        except ValueError:
            logger.warning(f"\n⚠️  Invalid limit '{sys.argv[1]}', processing all reports")
    
    # Run batch geocoding
    success = batch_geocode_reports(limit)
    
    if success:
        # Show sample results
        show_geocoded_sample()
        
        logger.info("\n" + "=" * 70)
        logger.info("🎉 BATCH GEOCODING COMPLETED SUCCESSFULLY!")
        logger.info("=" * 70)
        logger.info("\nNext steps:")
        logger.info("  1. Start Flask app: python app.py")
        logger.info("  2. View map at: http://localhost:5000/peta")
        logger.info("  3. Check markers on the map")
        logger.info("\n⚠️  IMPORTANT OSM USAGE NOTES:")
        logger.info("   • Respect OSM rate limit (1 request/second)")
        logger.info("   • Don't overload OSM servers")
        logger.info("   • Cache geocoding results")
        logger.info("   • Consider running batch at off-peak hours")
        logger.info("=" * 70 + "\n")
    else:
        logger.error("\n⚠️  No reports were successfully geocoded")
        logger.error("   Check the error messages above for details")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Batch geocoding interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()