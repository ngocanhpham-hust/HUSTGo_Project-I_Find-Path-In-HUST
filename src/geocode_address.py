import re
from typing import Tuple, Optional
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time

# Initialize geocoder with a user agent
geocoder = Nominatim(user_agent="bachkhoa_pathfinding_app")

# Bách Khoa bounding box for validation
BACHKHOA_BBOX = {
    'north': 21.0065,
    'south': 21.0015,
    'east': 105.8495,
    'west': 105.8425
}

def is_coordinate_string(input_str: str) -> bool:
    """Check if input is in lat,lon format."""
    pattern = r'^-?\d+\.?\d*\s*,\s*-?\d+\.?\d*$'
    return bool(re.match(pattern, input_str.strip()))

def parse_coordinates(coord_str: str) -> Tuple[float, float]:
    """Parse 'lat,lon' string to (lat, lon) tuple."""
    parts = coord_str.strip().split(',')
    if len(parts) != 2:
        raise ValueError(f"Invalid coordinate format: {coord_str}")
    
    lat = float(parts[0].strip())
    lon = float(parts[1].strip())
    return lat, lon

def is_in_bachkhoa_area(lat: float, lon: float) -> bool:
    """Check if coordinates are within Bách Khoa area."""
    return (BACHKHOA_BBOX['south'] <= lat <= BACHKHOA_BBOX['north'] and
            BACHKHOA_BBOX['west'] <= lon <= BACHKHOA_BBOX['east'])

def geocode_address(address: str, retries: int = 3) -> Tuple[Optional[float], Optional[float]]:
    """
    Convert address to (lat, lon) coordinates using Nominatim.
    
    Args:
        address: Address string to geocode
        retries: Number of retry attempts if geocoding fails
    
    Returns:
        (lat, lon) tuple or (None, None) if geocoding fails
    """
    # Add context to improve accuracy
    if "Bách Khoa" in address or "ĐHBK" in address:
        search_address = address
    else:
        search_address = f"{address}, Bách Khoa, Hai Bà Trưng, Hà Nội, Vietnam"
    
    print(f"Geocoding: '{search_address}'")
    
    for attempt in range(retries):
        try:
            # Add viewbox to prioritize Bách Khoa area
            location = geocoder.geocode(
                search_address,
                viewbox=(BACHKHOA_BBOX['west'], BACHKHOA_BBOX['south'],
                        BACHKHOA_BBOX['east'], BACHKHOA_BBOX['north']),
                bounded=False,  # Allow results outside viewbox if needed
                timeout=10
            )
            
            if location:
                lat, lon = location.latitude, location.longitude
                print(f"  → Found: {lat:.6f}, {lon:.6f}")
                
                # Warn if outside Bách Khoa area
                if not is_in_bachkhoa_area(lat, lon):
                    print(f"  ⚠ WARNING: Coordinates outside Bách Khoa area!")
                    print(f"    Expected: lat=[{BACHKHOA_BBOX['south']}, {BACHKHOA_BBOX['north']}], "
                          f"lon=[{BACHKHOA_BBOX['west']}, {BACHKHOA_BBOX['east']}]")
                
                return lat, lon
            else:
                print(f"  ✗ No results found")
                return None, None
                
        except GeocoderTimedOut:
            if attempt < retries - 1:
                print(f"  ⚠ Timeout, retrying ({attempt + 1}/{retries})...")
                time.sleep(1)
            else:
                print(f"  ✗ Geocoding failed after {retries} attempts (timeout)")
                return None, None
                
        except GeocoderServiceError as e:
            print(f"  ✗ Geocoding service error: {e}")
            return None, None
        
        except Exception as e:
            print(f"  ✗ Unexpected error: {e}")
            return None, None
    
    return None, None

def parse_location_input(input_str: str) -> Tuple[float, float]:
    """
    Smart parser: handles both coordinate strings and address names.
    
    Args:
        input_str: Either "lat,lon" or an address name
    
    Returns:
        (lat, lon) tuple
    
    Raises:
        ValueError: If parsing fails or geocoding returns no results
    """
    input_str = input_str.strip()
    
    # Check if input is already coordinates
    if is_coordinate_string(input_str):
        lat, lon = parse_coordinates(input_str)
        print(f"Using coordinates: {lat:.6f}, {lon:.6f}")
        return lat, lon
    
    # Otherwise, geocode the address
    lat, lon = geocode_address(input_str)
    
    if lat is None or lon is None:
        raise ValueError(f"Failed to geocode address: '{input_str}'")
    
    return lat, lon

# Predefined common locations in Bách Khoa (fallback/cache)
COMMON_LOCATIONS = {
    "thư viện": (21.00378, 105.84548),
    "thư viện tạ quang bửu": (21.00378, 105.84548),
    "nhà c1": (21.00420, 105.84580),
    "nhà d3": (21.00340, 105.84520),
    "nhà b1": (21.00480, 105.84650),
    "nhà h1": (21.00450, 105.84700),
    "cổng trước": (21.00370, 105.84540),
    "cổng chính": (21.00370, 105.84540),
    "1 đại cồ việt": (21.00370, 105.84540),
}

def get_location_with_fallback(input_str: str) -> Tuple[float, float]:
    """
    Try geocoding first, fall back to predefined locations if geocoding fails.
    
    Args:
        input_str: Coordinate string or address name
    
    Returns:
        (lat, lon) tuple
    """
    try:
        return parse_location_input(input_str)
    except ValueError:
        # Try matching with common locations
        input_lower = input_str.lower()
        for key, coords in COMMON_LOCATIONS.items():
            if key in input_lower:
                print(f"Using predefined location for '{key}': {coords[0]:.6f}, {coords[1]:.6f}")
                return coords
        
        # If no match found, re-raise the error
        raise ValueError(f"Could not parse or geocode: '{input_str}'")

if __name__ == "__main__":
    # Test cases
    print("=" * 60)
    print("Testing Geocoding Helper")
    print("=" * 60)
    
    test_inputs = [
        "21.0037,105.8454",  # Coordinates
        "Thư viện Tạ Quang Bửu, ĐHBK Hà Nội",  # Address
        "Nhà C1, Đại học Bách Khoa Hà Nội",  # Address
        "1 Đại Cồ Việt, Hà Nội",  # Street address
        "thư viện",  # Shorthand (will use fallback)
    ]
    
    for test_input in test_inputs:
        print(f"\nInput: '{test_input}'")
        try:
            lat, lon = get_location_with_fallback(test_input)
            print(f"Result: {lat:.6f}, {lon:.6f}")
        except ValueError as e:
            print(f"Error: {e}")
    
    print("\n" + "=" * 60)