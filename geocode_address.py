import re
import requests
import time
from typing import Tuple, Optional, List, Dict

# --- CẤU HÌNH ---
BACHKHOA_BBOX = {
    'north': 21.0110,
    'south': 21.0020,
    'east': 105.8530,
    'west': 105.8400
}

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# location format "name": (latitude, longitude)

COMMON_LOCATIONS = {
    # Main department
    "Toà C1": (21.0070715, 105.8425561),
    "Toà C2": (21.0064474, 105.8423066),
    "Toà C3": (21.0066214, 105.8439327),
    "Toà C7": (21.0052757, 105.8451778),
    
    "Toà D3": (21.0047785, 105.8447491),
    "Toà D3-5": (21.0046330, 105.8452138),    
    "Toà D5": (21.0046330, 105.8452138),
    "Toà D6": (21.0043525, 105.8426955),
    "Toà D7": (21.0040340, 105.8448670),      
    "SIE": (21.0040340, 105.8448670),
    "Toà D8": (21.0039763, 105.8426704),
    "Toà B9": (21.0037956, 105.8444671),
    "Toà B1": (21.0044157, 105.8465901),

    "Thư viện Tạ Quang Bửu": (21.0044106, 105.8439888),
    "Hồ Tiền": (21.0040519, 105.8434327),
    
    "Ký túc xá": (21.0049406, 105.8469539),
    "Sân vận động": (21.0021875, 105.8478125),
    "Sân bóng": (21.0021875, 105.8478125),
    "Nhà thi đấu": (21.0035324, 105.8470866),
    "Toà T": (21.0035661, 105.8489794),   
    "Trung tâm": (21.0035661, 105.8489794),
    "TC": (21.0025178, 105.8470152),      

    # GATE
    "Cổng Đại Cồ Việt": (21.007350, 105.843150),
    "Cổng parabol": (21.001650, 105.841850), 
    "Cổng Giải Phóng": (21.001650, 105.841850),
    "Cổng Trần Đại Nghĩa": (21.004850, 105.849350), 
    "Cổng Tạ Quang Bửu": (21.002500, 105.845000), 

    # NEU
    "Cổng NEU Giải Phóng": (21.000094, 105.842499),
    "Cổng NEU Trần Đại Nghĩa": (20.999125, 105.845597),
    "Cổng KTX NEU": (20.999353, 105.846564),

    # HUCE
    "Cổng HUCE Giải Phóng": (21.003314, 105.843321),
    "Cổng HUCE Trần Đại Nghĩa": (21.003029, 105.844619),

    # Others
    "Sân bóng": (21.005000, 105.846000),
    "Bể bơi": (21.003418, 105.847198),
    "Quảng trường C1": (21.006800, 105.842800),
    "Cây xăng Bách Khoa": (21.001977, 105.849331),
    "Cây xăng Giải Phóng": (21.001800, 105.841500),
}

# Utils

def is_coordinate_string(input_str: str) -> bool:
    pattern = r'^-?\d+\.?\d*\s*,\s*-?\d+\.?\d*$'
    return bool(re.match(pattern, input_str.strip()))

def parse_coordinates(coord_str: str) -> Tuple[float, float]:
    parts = coord_str.strip().split(',')
    lat = float(parts[0].strip())
    lon = float(parts[1].strip())
    return lat, lon

def is_in_bachkhoa_area(lat: float, lon: float) -> bool:
    """Kiểm tra xem tọa độ có nằm trong vùng Bách Khoa không"""
    return (BACHKHOA_BBOX['south'] <= lat <= BACHKHOA_BBOX['north'] and
            BACHKHOA_BBOX['west'] <= lon <= BACHKHOA_BBOX['east'])

# Call API

def search_osm_overpass(query: str, retries: int = 2) -> List[Dict]:
    bbox = f"{BACHKHOA_BBOX['south']},{BACHKHOA_BBOX['west']},{BACHKHOA_BBOX['north']},{BACHKHOA_BBOX['east']}"
    overpass_query = f"""
    [out:json][timeout:25];
    (
      node["name"~"{query}",i]({bbox});
      way["name"~"{query}",i]({bbox});
    );
    out center;
    """
    
    for url in OVERPASS_URLS:
        for attempt in range(retries):
            try:
                response = requests.post(url, data=overpass_query, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    for el in data.get('elements', []):
                        lat = el.get('lat') or el.get('center', {}).get('lat')
                        lon = el.get('lon') or el.get('center', {}).get('lon')
                        if lat and lon:
                            results.append({'lat': lat, 'lon': lon, 'name': el.get('tags', {}).get('name')})
                    return results
            except Exception:
                pass 
    return []

def geocode_with_nominatim_fallback(address: str) -> Tuple[Optional[float], Optional[float]]:
    try:
        from geopy.geocoders import Nominatim
        geocoder = Nominatim(user_agent="bachkhoa_pathfinding_app_v3")
        
        location = geocoder.geocode(
            f"{address}, Hai Bà Trưng, Hà Nội",
            timeout=5
        )
        if location:
            if is_in_bachkhoa_area(location.latitude, location.longitude):
                return location.latitude, location.longitude
            else:
                print(f"  Warning: Tìm thấy '{address}' nhưng nằm ngoài vùng BK.")
    except Exception as e:
        print(f"  Nominatim error: {e}")
    return None, None

# Logic functions

def get_location_with_fallback(input_str: str) -> Tuple[float, float]:
    input_str = input_str.strip()
    input_lower = input_str.lower()
    
    if is_coordinate_string(input_str):
        return parse_coordinates(input_str)

    if input_lower in COMMON_LOCATIONS:
        return COMMON_LOCATIONS[input_lower]
    
    for key, coords in COMMON_LOCATIONS.items():
        if key in input_lower: 
            return coords

    results = search_osm_overpass(input_str)
    if results:
        print(f"  -> Tìm thấy trên OSM: {results[0].get('name')}")
        return results[0]['lat'], results[0]['lon']

    lat, lon = geocode_with_nominatim_fallback(input_str)
    if lat and lon:
        return lat, lon

    raise ValueError(f"Không tìm thấy địa điểm: '{input_str}'. Vui lòng thử tên khác hoặc nhập tọa độ.")

if __name__ == "__main__":
  try:
        lat, lon = get_location_with_fallback("Thư viện")
        print(f"Test Thư viện: {lat}, {lon}")
  except Exception as e:
        print(e)
