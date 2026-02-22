"""
Helper functions untuk Flood Warning System
Diperbaiki: OSM Geocoding untuk seluruh Indonesia, Error handling, dan utilities
"""

import requests
import time
import logging
from datetime import datetime
import pytz
import os

logger = logging.getLogger(__name__)

# ==================== OSM GEOCODING ====================

class OSMGeocoder:
    """OpenStreetMap Nominatim Geocoder - Support seluruh Indonesia"""
    
    def __init__(self, user_agent="FloodWarningSystem/2.0", base_url="https://nominatim.openstreetmap.org"):
        self.user_agent = user_agent
        self.base_url = base_url
        self.rate_limit_delay = 1.1  # OSM requires minimum 1 second between requests
        self.last_request_time = 0
        
    def _respect_rate_limit(self):
        """Ensure we don't exceed OSM rate limit"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    def test_connection(self):
        """Test OSM connection"""
        try:
            response = requests.get(
                f"{self.base_url}/status.php",
                headers={'User-Agent': self.user_agent},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def geocode_address(self, address, country_code="id"):
        """
        Geocode an address using OSM Nominatim - Support seluruh Indonesia
        
        Args:
            address: Address string to geocode
            country_code: ISO country code (default: "id" for Indonesia)
            
        Returns:
            tuple: (latitude, longitude, error_message)
        """
        if not address or len(address) < 3:
            return None, None, "Address too short"
        
        try:
            # Respect rate limit
            self._respect_rate_limit()
            
            # Clean and format address for better OSM search
            formatted_address = self._format_address_for_osm(address)
            
            # Prepare search query - get top 5 for better matching
            params = {
                'q': formatted_address,
                'format': 'json',
                'limit': 5,
                'countrycodes': country_code,
                'addressdetails': 1
            }
            
            headers = {
                'User-Agent': self.user_agent
            }
            
            # Make request
            response = requests.get(
                f"{self.base_url}/search",
                params=params,
                headers=headers,
                timeout=15
            )
            
            if response.status_code != 200:
                return None, None, f"HTTP {response.status_code}"
            
            data = response.json()
            
            if not data or len(data) == 0:
                return None, None, "No results found"
            
            # Select best result
            best_result = self._select_best_result(data, address)
            if not best_result:
                best_result = data[0]
            
            lat = float(best_result['lat'])
            lon = float(best_result['lon'])
            
            logger.info(f"OSM Geocoded: {address[:50]} -> ({lat}, {lon})")
            
            return lat, lon, None
            
        except requests.exceptions.Timeout:
            return None, None, "Request timeout"
        except requests.exceptions.ConnectionError:
            return None, None, "Connection error"
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return None, None, str(e)
    
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


# ==================== IP ADDRESS ====================

def get_client_ip(request):
    """Get client IP address from request"""
    # Check for proxy headers first
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr or 'Unknown'


# ==================== DATE/TIME HELPERS ====================

def get_current_datetime_wib():
    """Get current datetime in WIB timezone"""
    tz = pytz.timezone('Asia/Jakarta')
    return datetime.now(tz)


def format_datetime(dt, format='%Y-%m-%d %H:%M:%S'):
    """Format datetime object"""
    if not dt:
        return ''
    if isinstance(dt, str):
        return dt
    return dt.strftime(format)


def format_date_indonesian(date_str):
    """Format date to Indonesian style"""
    if not date_str:
        return 'N/A'
    
    try:
        # Parse date
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']:
            try:
                dt = datetime.strptime(str(date_str), fmt)
                break
            except ValueError:
                continue
        else:
            return str(date_str)
        
        # Indonesian month names
        months_id = [
            '', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
            'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
        ]
        
        return f"{dt.day} {months_id[dt.month]} {dt.year}"
    except:
        return str(date_str)


# ==================== FILE HELPERS ====================

def allowed_file(filename, allowed_extensions=None):
    """Check if file extension is allowed"""
    if not filename:
        return False
    
    if allowed_extensions is None:
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def get_file_size_mb(filepath):
    """Get file size in MB"""
    try:
        if os.path.exists(filepath):
            size_bytes = os.path.getsize(filepath)
            return round(size_bytes / (1024 * 1024), 2)
        return 0
    except:
        return 0


# ==================== VALIDATION ====================

def validate_phone_number(phone):
    """Validate Indonesian phone number"""
    if not phone:
        return True  # Optional field
    
    # Remove spaces and dashes
    phone = phone.replace(' ', '').replace('-', '')
    
    # Should start with 08, +62, or 62
    if phone.startswith('08') or phone.startswith('62') or phone.startswith('+62'):
        # Should be 10-15 digits
        digits = ''.join(filter(str.isdigit, phone))
        return 10 <= len(digits) <= 15
    
    return False


def validate_address(address):
    """Validate address"""
    if not address or len(address) < 5:
        return False, "Alamat terlalu pendek (minimal 5 karakter)"
    
    if len(address) > 500:
        return False, "Alamat terlalu panjang (maksimal 500 karakter)"
    
    return True, ""


# ==================== DATA FORMATTING ====================

def format_flood_height(height_str):
    """Standardize flood height format"""
    if not height_str:
        return "Tidak diketahui"
    
    height_str = str(height_str).strip()
    
    # Already formatted
    if 'cm' in height_str.lower() or 'meter' in height_str.lower():
        return height_str
    
    # Try to extract number
    try:
        num = float(''.join(filter(lambda x: x.isdigit() or x == '.', height_str)))
        if num >= 100:
            return f"{num/100:.1f} meter"
        else:
            return f"{int(num)} cm"
    except:
        return height_str


def truncate_text(text, max_length=50):
    """Truncate text to max length"""
    if not text:
        return ''
    
    text = str(text)
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + '...'


# ==================== ERROR HANDLING ====================

def log_error(error, context=""):
    """Log error with context"""
    error_msg = f"[{context}] {type(error).__name__}: {str(error)}"
    logger.error(error_msg)
    return error_msg


def safe_int(value, default=0):
    """Safely convert to int"""
    try:
        return int(value)
    except:
        return default


def safe_float(value, default=0.0):
    """Safely convert to float"""
    try:
        return float(value)
    except:
        return default


# ==================== DATABASE HELPERS ====================

def dict_from_row(row):
    """Convert sqlite3.Row to dict"""
    if not row:
        return {}
    try:
        return dict(row)
    except:
        return {}


# ==================== TESTING ====================

if __name__ == "__main__":
    print("Testing OSM Geocoder - Support Seluruh Indonesia...")
    
    geocoder = OSMGeocoder()
    
    # Test connection
    if geocoder.test_connection():
        print("✅ OSM connection successful")
        
        # Test geocoding dari berbagai daerah
        test_addresses = [
            "Semarang, Jawa Tengah",
            "Jakarta Selatan",
            "Surabaya, Jawa Timur",
            "Medan, Sumatera Utara",
            "Makassar, Sulawesi Selatan",
            "Denpasar, Bali",
            "Balikpapan, Kalimantan Timur",
            "Jayapura, Papua"
        ]
        
        for address in test_addresses:
            lat, lng, error = geocoder.geocode_address(address)
            if lat and lng:
                print(f"✅ {address}: ({lat}, {lng})")
            else:
                print(f"❌ {address}: {error}")
    else:
        print("❌ OSM connection failed")