import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # ==================== FLASK CONFIG ====================
    SECRET_KEY = os.getenv('SECRET_KEY', 'a365b24f23742932a25489d2d01304ba1315641fa028ae59f726e652badfbfcc')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # ==================== DATABASE ====================
    DATABASE_PATH = 'flood_system.db'
    
    # ==================== UPLOADS ====================
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # ==================== GOOGLE SHEETS ====================
    GOOGLE_SHEETS_CREDENTIALS = 'credentials.json'
    SPREADSHEET_ID = '1wdys3GzfDfl0ohCQjUHRyJVbKQcM0VSIMgCryHB0-mc'
    WORKSHEET_NAME = 'flood_reports'
    SERVICE_ACCOUNT_EMAIL = 'flood-sheets-access@flood-warning-system-481323.iam.gserviceaccount.com'
    
    # ==================== OPENSTREETMAP GEOCODING ====================
    #  NEW: OpenStreetMap (Nominatim) Configuration
    GEOCODING_PROVIDER = os.getenv('GEOCODING_PROVIDER', 'osm')  # 'osm' or 'locationiq' for fallback
    OSM_USER_AGENT = os.getenv('OSM_USER_AGENT', 'FloodWarningSystem/2.0 (tyarawahyusaputra@gmail.com)')
    OSM_RATE_LIMIT_DELAY = float(os.getenv('OSM_RATE_LIMIT_DELAY', '1.1'))  # 1.1 seconds (OSM limit)
    OSM_BASE_URL = "https://nominatim.openstreetmap.org"
    
    # Geocoding settings
    GEOCODING_ENABLED = os.getenv('GEOCODING_ENABLED', 'True').lower() == 'true'
    GEOCODING_TIMEOUT = int(os.getenv('GEOCODING_TIMEOUT', '10'))  # seconds
    GEOCODING_MAX_RETRIES = int(os.getenv('GEOCODING_MAX_RETRIES', '3'))
    
    # ==================== SYSTEM ====================
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'tyarawahyusaputra@gmail.com')
    ADMIN_PHONE = os.getenv('ADMIN_PHONE', '085156959561')
    MAX_REPORTS_PER_DAY = 10
    
    # ==================== TIMEZONE ====================
    TIMEZONE = 'Asia/Jakarta'
    
    # ==================== APPLICATION ====================
    APP_NAME = 'Sistem Peringatan Dini Banjir'
    APP_VERSION = '2.0.0'
    
    # ==================== FEATURES ====================
    ENABLE_GOOGLE_SHEETS_SYNC = True
    ENABLE_AUTO_BACKUP = True
    AUTO_SYNC_ON_STARTUP = False  #  DISABLED to prevent duplication
    
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
    LOG_FILE = os.getenv('LOG_FILE', 'logs/flood_system.log')
    LOG_MAX_SIZE = int(os.getenv('LOG_MAX_SIZE', '10485760'))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    
    # ==================== SECURITY ====================
    # Rate limiting for API endpoints
    API_RATE_LIMIT = os.getenv('API_RATE_LIMIT', '100 per day')
    
    # CORS settings (if needed for API)
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',') if os.getenv('CORS_ORIGINS') else []
    
    # ==================== BACKUP SETTINGS ====================
    BACKUP_ENABLED = os.getenv('BACKUP_ENABLED', 'True').lower() == 'true'
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
    """Validate configuration and print warnings"""
    warnings = []
    
    # Check OSM configuration
    if Config.GEOCODING_PROVIDER == 'osm':
        if len(Config.OSM_USER_AGENT) < 20:
            warnings.append("  OSM User Agent might be too short")
        print(" Using OpenStreetMap (Nominatim) for geocoding")
    else:
        print(f"ℹ  Using geocoding provider: {Config.GEOCODING_PROVIDER}")
    
    # Check if Google Sheets credentials exist
    if Config.ENABLE_GOOGLE_SHEETS_SYNC:
        if not os.path.exists(Config.GOOGLE_SHEETS_CREDENTIALS):
            warnings.append("  Google Sheets credentials file not found")
    
    # Check upload folder
    if not os.path.exists(Config.UPLOAD_FOLDER):
        warnings.append(f"  Upload folder '{Config.UPLOAD_FOLDER}' does not exist")
    
    # Print warnings if any
    if warnings:
        print("\n  CONFIGURATION WARNINGS:")
        for warning in warnings:
            print(f"   - {warning}")
    
    return len(warnings) == 0


if __name__ == "__main__":
    # Test configuration
    print(" CONFIGURATION TEST")
    print("=" * 50)
    
    print(f"App Name: {Config.APP_NAME} v{Config.APP_VERSION}")
    print(f"Database: {Config.DATABASE_PATH}")
    print(f"Geocoding Provider: {Config.GEOCODING_PROVIDER}")
    
    is_valid = validate_config()
    
    if is_valid:
        print("\n Configuration is valid")
    else:
        print("\n  Configuration has warnings (app may still work)")
    
    print("\n OSM Config:")
    osm_config = get_osm_config()
    for key, value in osm_config.items():
        print(f"  {key}: {value}")