"""
WIB Timezone Helper Module
===========================
Module ini menyediakan fungsi untuk menangani timezone WIB (GMT+7)
untuk memastikan waktu yang ditampilkan selalu WIB di mana pun server berada.

Usage:
    from utils.wib_helper import get_wib_now
    
    current_time = get_wib_now()
"""

from datetime import datetime
import pytz

# WIB Timezone (Asia/Jakarta = GMT+7)
WIB = pytz.timezone('Asia/Jakarta')

def get_wib_now():
    """
    Get current datetime in WIB timezone
    
    Returns:
        datetime: Current datetime in WIB timezone
    
    Example:
        >>> now = get_wib_now()
        >>> print(now.strftime('%Y-%m-%d %H:%M:%S %Z'))
        2026-02-04 15:30:00 WIB
    """
    # Get current UTC time
    utc_now = datetime.now(pytz.UTC)
    
    # Convert to WIB
    wib_now = utc_now.astimezone(WIB)
    
    return wib_now


def get_wib_datetime_from_utc(utc_datetime):
    """
    Convert UTC datetime to WIB timezone
    
    Args:
        utc_datetime (datetime): UTC datetime object
        
    Returns:
        datetime: Datetime in WIB timezone
    """
    if utc_datetime.tzinfo is None:
        # If naive datetime, assume it's UTC
        utc_datetime = pytz.UTC.localize(utc_datetime)
    
    return utc_datetime.astimezone(WIB)


def format_wib_datetime(dt, format='%d/%m/%Y %H:%M'):
    """
    Format datetime to string in WIB timezone
    
    Args:
        dt (datetime): Datetime object
        format (str): Format string (default: '%d/%m/%Y %H:%M')
        
    Returns:
        str: Formatted datetime string
    """
    if dt is None:
        return ''
    
    # Ensure datetime is in WIB
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    
    wib_dt = dt.astimezone(WIB)
    return wib_dt.strftime(format)


def format_wib_date(dt):
    """
    Format date only (DD/MM/YYYY) in WIB timezone
    
    Args:
        dt (datetime): Datetime object
        
    Returns:
        str: Formatted date string
    """
    return format_wib_datetime(dt, '%d/%m/%Y')


def format_wib_time(dt):
    """
    Format time only (HH:MM) in WIB timezone
    
    Args:
        dt (datetime): Datetime object
        
    Returns:
        str: Formatted time string
    """
    return format_wib_datetime(dt, '%H:%M')


def format_wib_datetime_full(dt):
    """
    Format full datetime with WIB indicator
    
    Args:
        dt (datetime): Datetime object
        
    Returns:
        str: Formatted datetime string with WIB
    """
    return format_wib_datetime(dt, '%d/%m/%Y %H:%M WIB')


# Convenience function for Flask templates
def get_wib_for_template():
    """
    Get WIB datetime formatted for template usage
    
    Returns:
        datetime: Current WIB datetime that works with strftime in templates
    """
    return get_wib_now()


if __name__ == "__main__":
    # Test the module
    print("=" * 60)
    print("WIB TIMEZONE HELPER - TEST")
    print("=" * 60)
    
    now = get_wib_now()
    print(f"\nCurrent WIB Time:")
    print(f"  Full: {format_wib_datetime_full(now)}")
    print(f"  Date: {format_wib_date(now)}")
    print(f"  Time: {format_wib_time(now)}")
    print(f"  Timezone: {now.tzinfo}")
    print(f"  UTC Offset: {now.strftime('%z')}")
    
    # Test UTC conversion
    import datetime as dt
    utc_time = dt.datetime.now(pytz.UTC)
    wib_time = get_wib_datetime_from_utc(utc_time)
    
    print(f"\nUTC to WIB Conversion:")
    print(f"  UTC: {utc_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"  WIB: {wib_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"  Difference: +7 hours")
    
    print("\n" + "=" * 60)