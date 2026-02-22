import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """
    Production-Safe Configuration for Flask Flood Warning System
    
    CRITICAL: Paths must be ABSOLUTE for consistency between local and PythonAnywhere
    """
    
    # ==================== PATH CONFIGURATION ====================
    # Get absolute path to project root
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # ==================== FLASK CONFIG ====================
    SECRET_KEY = os.getenv('SECRET_KEY', 'a365b24f23742932a25489d2d01304ba1315641fa028ae59f726e652badfbfcc')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # ==================== DATABASE ====================
    # CRITICAL: Use ABSOLUTE path for database to ensure consistency
    DATABASE_PATH = os.path.join(BASE_DIR, 'flood_system.db')
    
    # Validate database path
    @staticmethod
    def validate_database_path():
        """Ensure database path is valid and accessible"""
        db_dir = os.path.dirname(Config.DATABASE_PATH)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        return Config.DATABASE_PATH
    
    # ==================== UPLOADS ====================
    # Use absolute path for uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # ==================== GOOGLE SHEETS ====================
    GOOGLE_SHEETS_CREDENTIALS = os.path.join(BASE_DIR, 'credentials.json')
    SPREADSHEET_ID = os.getenv('SPREADSHEET_ID', '1wdys3GzfDfl0ohCQjUHRyJVbKQcM0VSIMgCryHB0-mc')
    WORKSHEET_NAME = 'flood_reports'
    SERVICE_ACCOUNT_EMAIL = 'flood-sheets-access@flood-warning-system-481323.iam.gserviceaccount.com'
    
    # ==================== OPENSTREETMAP GEOCODING ====================
    # AUTO-GEOCODING CONFIGURATION
    # Digunakan untuk geocoding otomatis saat user submit laporan banjir
    # Menggunakan OpenStreetMap Nominatim API (GRATIS, tidak perlu API key)
    
    GEOCODING_PROVIDER = os.getenv('GEOCODING_PROVIDER', 'osm')  # 'osm' or 'locationiq' for fallback
    
    # User Agent (WAJIB untuk OSM - identifikasi aplikasi)
    # Format: AppName/Version (contact@email.com)
    OSM_USER_AGENT = os.getenv('OSM_USER_AGENT', 'FloodWarningSystem/2.0 (tyarawahyusaputra@gmail.com)')
    
    # Rate Limit Delay (WAJIB - OSM policy: max 1 request per second)
    # Set 1.1 detik untuk safety margin
    OSM_RATE_LIMIT_DELAY = float(os.getenv('OSM_RATE_LIMIT_DELAY', '1.1'))  # 1.1 seconds
    
    # OSM Nominatim Base URL
    OSM_BASE_URL = "https://nominatim.openstreetmap.org"
    
    # Geocoding settings
    GEOCODING_ENABLED = os.getenv('GEOCODING_ENABLED', 'True').lower() == 'true'  # Enable/disable auto-geocoding
    GEOCODING_TIMEOUT = int(os.getenv('GEOCODING_TIMEOUT', '10'))  # Timeout untuk geocoding request (seconds)
    GEOCODING_MAX_RETRIES = int(os.getenv('GEOCODING_MAX_RETRIES', '3'))  # Max retry jika gagal
    
    # Auto-geocoding behavior
    # Jika True: Geocoding otomatis saat submit laporan
    # Jika False: Laporan tersimpan tanpa geocoding (perlu batch geocode manual)
    AUTO_GEOCODE_ON_SUBMIT = os.getenv('AUTO_GEOCODE_ON_SUBMIT', 'True').lower() == 'true'
    
    # Geocoding fallback
    # Jika geocoding gagal, laporan tetap tersimpan dengan is_geocoded=0
    SAVE_REPORT_WITHOUT_GEOCODE = True  # Always save report even if geocoding fails
    
    # ==================== SYSTEM ====================
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'tyarawahyusaputra@gmail.com')
    ADMIN_PHONE = os.getenv('ADMIN_PHONE', '085156959561')
    MAX_REPORTS_PER_DAY = 10
    
    # ==================== TIMEZONE ====================
    TIMEZONE = 'Asia/Jakarta'
    
    # ==================== APPLICATION ====================
    APP_NAME = 'Sistem Peringatan Dini Banjir'
    APP_VERSION = '2.1.0'
    
    # ==================== FEATURES ====================
    ENABLE_GOOGLE_SHEETS_SYNC = True
    ENABLE_AUTO_BACKUP = True
    AUTO_SYNC_ON_STARTUP = False  # DISABLED to prevent duplication
    
    # ==================== FLASH MESSAGE SETTINGS ====================
    # Flash message configuration untuk notifikasi auto-geocoding
    FLASH_MESSAGE_SUCCESS_GEOCODED = '✅ Laporan berhasil dikirim dan lokasi berhasil dipetakan!'
    FLASH_MESSAGE_SUCCESS_NO_GEOCODE = '✅ Laporan berhasil dikirim!'
    FLASH_MESSAGE_GEOCODE_FAILED = '⚠️ Lokasi belum dapat dipetakan secara otomatis'
    FLASH_MESSAGE_MANUAL_VERIFICATION = 'ℹ️ Tim kami akan memverifikasi lokasi secara manual'
    
    # Link to map page in flash messages
    SHOW_MAP_LINK_IN_FLASH = True  # Show "Lihat di Peta Banjir" link in success message
    
    # ==================== SYNC SETTINGS ====================
    SYNC_BATCH_SIZE = 10  # Number of records to sync at once
    SYNC_RETRY_ATTEMPTS = 3
    SYNC_RETRY_DELAY = 2  # seconds
    
    # ==================== MAP SETTINGS ====================
    # Default map center (dapat disesuaikan sesuai daerah operasional)
    DEFAULT_MAP_CENTER_LAT = float(os.getenv('DEFAULT_MAP_CENTER_LAT', '-7.3305'))
    DEFAULT_MAP_CENTER_LNG = float(os.getenv('DEFAULT_MAP_CENTER_LNG', '110.4983'))
    DEFAULT_MAP_ZOOM = int(os.getenv('DEFAULT_MAP_ZOOM', '12'))
    
    # Map tile provider
    MAP_TILE_PROVIDER = os.getenv('MAP_TILE_PROVIDER', 'openstreetmap')
    MAP_TILE_URL = os.getenv('MAP_TILE_URL', 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png')
    
    # ==================== LOGGING ====================
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.path.join(BASE_DIR, 'logs', 'flood_system.log')
    LOG_MAX_SIZE = int(os.getenv('LOG_MAX_SIZE', '10485760'))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    
    # ==================== SECURITY ====================
    # Rate limiting for API endpoints
    API_RATE_LIMIT = os.getenv('API_RATE_LIMIT', '100 per day')
    
    # CORS settings (if needed for API)
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',') if os.getenv('CORS_ORIGINS') else []
    
    # ==================== BACKUP SETTINGS ====================
    BACKUP_ENABLED = os.getenv('BACKUP_ENABLED', 'True').lower() == 'true'
    BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
    BACKUP_SCHEDULE = os.getenv('BACKUP_SCHEDULE', 'daily')  # 'daily', 'weekly', 'monthly'
    BACKUP_RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))


# Helper function to get OSM configuration
def get_osm_config():
    """Get OSM configuration as a dictionary"""
    return {
        'user_agent': Config.OSM_USER_AGENT,
        'rate_limit_delay': Config.OSM_RATE_LIMIT_DELAY,
        'base_url': Config.OSM_BASE_URL,
        'timeout': Config.GEOCODING_TIMEOUT,
        'enabled': Config.GEOCODING_ENABLED
    }


def validate_config():
    """Validate configuration and create necessary directories"""
    warnings = []
    
    # Create necessary directories
    directories = [
        Config.UPLOAD_FOLDER,
        os.path.dirname(Config.LOG_FILE),
        Config.BACKUP_DIR
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"✅ Created directory: {directory}")
            except Exception as e:
                warnings.append(f"Could not create directory {directory}: {e}")
    
    # Validate database path
    Config.validate_database_path()
    print(f"✅ Database path: {Config.DATABASE_PATH}")
    
    # Check OSM configuration
    if Config.GEOCODING_PROVIDER == 'osm':
        if len(Config.OSM_USER_AGENT) < 20:
            warnings.append("OSM User Agent might be too short")
        print(f"✅ Using OpenStreetMap (Nominatim) for geocoding")
        print(f"   Auto-geocode on submit: {Config.AUTO_GEOCODE_ON_SUBMIT}")
        print(f"   Rate limit delay: {Config.OSM_RATE_LIMIT_DELAY}s")
        print(f"   Timeout: {Config.GEOCODING_TIMEOUT}s")
    else:
        print(f"ℹ️  Using geocoding provider: {Config.GEOCODING_PROVIDER}")
    
    # Check if Google Sheets credentials exist
    if Config.ENABLE_GOOGLE_SHEETS_SYNC:
        if not os.path.exists(Config.GOOGLE_SHEETS_CREDENTIALS):
            warnings.append("Google Sheets credentials file not found")
            print(f"⚠️  Google Sheets credentials not found at: {Config.GOOGLE_SHEETS_CREDENTIALS}")
    
    # Print warnings if any
    if warnings:
        print("\n⚠️  CONFIGURATION WARNINGS:")
        for warning in warnings:
            print(f"   - {warning}")
    
    return len(warnings) == 0


def get_environment_info():
    """Get current environment information"""
    return {
        'BASE_DIR': Config.BASE_DIR,
        'DATABASE_PATH': Config.DATABASE_PATH,
        'UPLOAD_FOLDER': Config.UPLOAD_FOLDER,
        'CREDENTIALS_PATH': Config.GOOGLE_SHEETS_CREDENTIALS,
        'LOG_FILE': Config.LOG_FILE,
        'BACKUP_DIR': Config.BACKUP_DIR,
        'GEOCODING_ENABLED': Config.GEOCODING_ENABLED,
        'GOOGLE_SHEETS_SYNC': Config.ENABLE_GOOGLE_SHEETS_SYNC
    }


if __name__ == "__main__":
    # Test configuration
    print("=" * 70)
    print("📋 CONFIGURATION TEST")
    print("=" * 70)
    
    print(f"\nApp: {Config.APP_NAME} v{Config.APP_VERSION}")
    print(f"Base Directory: {Config.BASE_DIR}")
    print(f"Database: {Config.DATABASE_PATH}")
    print(f"Uploads: {Config.UPLOAD_FOLDER}")
    print(f"Logs: {Config.LOG_FILE}")
    print(f"Backups: {Config.BACKUP_DIR}")
    print(f"Geocoding Provider: {Config.GEOCODING_PROVIDER}")
    
    is_valid = validate_config()
    
    if is_valid:
        print("\n✅ Configuration is valid")
    else:
        print("\n⚠️  Configuration has warnings (app may still work)")
    
    print("\n📊 OSM Config:")
    osm_config = get_osm_config()
    for key, value in osm_config.items():
        print(f"  {key}: {value}")
    
    print("\n🌍 Environment Info:")
    env_info = get_environment_info()
    for key, value in env_info.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 70)