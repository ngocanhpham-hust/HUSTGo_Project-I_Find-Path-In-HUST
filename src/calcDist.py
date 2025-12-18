# calcDist.py
import math
from typing import Tuple

EARTH_R = 6371000.0  # meters

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters between two lat/lon points."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_R * c

def calcDist(p1: Tuple[float,float], p2: Tuple[float,float]) -> float:
    """Wrapper: p1,p2 are (lat, lon) tuples, returns meters."""
    return haversine_m(p1[0], p1[1], p2[0], p2[1])
