import os
from typing import Dict, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, 'data')

os.makedirs(DATA_DIR, exist_ok=True)


EARTH_RADIUS_M = 6371000.0


BACHKHOA_BBOX = {
    'north': 21.0110,
    'south': 21.0020,
    'east': 105.8530,
    'west': 105.8400
}

BACHKHOA_NORTH = BACHKHOA_BBOX['north']
BACHKHOA_SOUTH = BACHKHOA_BBOX['south']
BACHKHOA_EAST = BACHKHOA_BBOX['east']
BACHKHOA_WEST = BACHKHOA_BBOX['west']

DEFAULT_SAVE_PREFIX = "bachkhoa_"

OSM_SETTINGS = {
    'use_cache': False,
    'log_console': True,
    'timeout': 300,  
    'network_type': 'all',  
    'simplify': True,
}

OSM_CUSTOM_FILTER = (
    '["highway"]["area"!~"yes"]["highway"!~"abandoned|bus_guideway|'
    'construction|corridor|elevator|escalator|planned|platform|'
    'proposed|raceway"]'
)


COMMON_LOCATIONS: Dict[str, Tuple[float, float]] = {
    # Main Buildings
    "thư viện": (21.00378, 105.84548),
    "thư viện tạ quang bửu": (21.00378, 105.84548),
    "nhà c1": (21.00420, 105.84580),
    "nhà d3": (21.00340, 105.84520),
    "nhà b1": (21.00480, 105.84650),
    "nhà h1": (21.00450, 105.84700),
    
    # Campus Entrances
    "cổng trước": (21.00370, 105.84540),
    "cổng chính": (21.00370, 105.84540),
    "1 đại cồ việt": (21.00370, 105.84540),
}
# Nominatim geocoder settings
GEOCODING_USER_AGENT = "bachkhoa_pathfinding_app"
GEOCODING_TIMEOUT = 10  
GEOCODING_RETRIES = 3  

GEOCODING_SEARCH_SUFFIX = ", Bách Khoa, Hai Bà Trưng, Hà Nội, Vietnam"


ASTAR_SETTINGS = {
    'epsilon': 1e-9,  # Tolerance for floating point comparisons
}

VISUALIZATION_SETTINGS = {
    'dpi': 150,
    'figsize': (12, 12),
    'node_size': 5,
    'node_color': 'blue',
    'edge_color': 'gray',
    'edge_linewidth': 0.5,
    'route_node_size': 25,
    'route_node_color': 'red',
    'route_edge_color': 'red',
    'route_edge_width': 2.0,
    'bgcolor': 'white',
}

# Output file names
DEFAULT_MAP_FILENAME = "bachkhoa_map.png"
DEFAULT_ROUTE_FILENAME = "bachkhoa_route.png"
TEMP_ROUTE_FILENAME = "temp_route.png"



STREAMLIT_CONFIG = {
    'page_title': "Bách Khoa Pathfinding",
    'page_icon': "🗺️",
    'layout': "wide",
}

UI_TEXT = {
    'app_title': "HUSTGo",
    'welcome_title': "Welcome to Hanoi University of Science and Technology!",
    'tagline': "Bách Khoa Pathfinding System | Powered by A* Algorithm & OpenStreetMap",
}


def get_graph_paths(save_prefix: str = DEFAULT_SAVE_PREFIX) -> Dict[str, str]:
    """
    Generate file paths for graph data files.
    
    Args:
        save_prefix: Prefix for file names
        
    Returns:
        Dictionary with paths for adj, nodes, edges, and graph files
    """
    return {
        'adj_path': os.path.join(DATA_DIR, f"{save_prefix}Adj.pkl"),
        'nodes_path': os.path.join(DATA_DIR, f"{save_prefix}Nodes.pkl"),
        'edges_path': os.path.join(DATA_DIR, f"{save_prefix}Edges.pkl"),
        'graph_path': os.path.join(DATA_DIR, f"{save_prefix}Graph.pkl"),
    }


def get_output_path(filename: str) -> str:
    """
    Get full path for output file in data directory.
    
    Args:
        filename: Name of the output file
        
    Returns:
        Full path to the output file
    """
    return os.path.join(DATA_DIR, filename)


def is_in_bachkhoa_area(lat: float, lon: float) -> bool:
    """
    Check if coordinates are within Bách Khoa campus boundaries.
    
    Args:
        lat: Latitude
        lon: Longitude
        
    Returns:
        True if coordinates are within campus boundaries
    """
    return (BACHKHOA_SOUTH <= lat <= BACHKHOA_NORTH and
            BACHKHOA_WEST <= lon <= BACHKHOA_EAST)


# Enable debug mode (can be overridden by environment variable)
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')

# Verbose logging
VERBOSE = os.getenv('VERBOSE', 'False').lower() in ('true', '1', 'yes')


__version__ = "1.0.0"
__author__ = "Pham Thi Ngoc Anh"
__project__ = "HUST Pathfinding System - Project I"

