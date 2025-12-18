# run_path.py
"""
Run example:
python run_path.py --start "21.0037,105.8454" --goal "21.0055,105.8490"
Or:
python run_path.py --start "Thư viện Tạ Quang Bửu, ĐHBK Hà Nội" --goal "Nhà C1, ĐHBK"
"""

import argparse
import pickle
import os
import sys

import osmnx as ox

from load_map_bachkhoa import build_and_save_graph, DATA_DIR
from AStar import astar, nearest_node_by_coord
from visualize_map import plot_route_with_graph_or_simple

# Try to import geocoding helper
try:
    from geocode_address import get_location_with_fallback
    GEOCODING_AVAILABLE = True
except ImportError:
    print("Warning: geocode_address.py not found. Only osmnx geocoding will be available.")
    GEOCODING_AVAILABLE = False

def parse_latlon(s: str):
    """Parse lat,lon string. Returns (lat, lon) or None."""
    s = s.strip()
    if ',' in s:
        parts = s.split(',')
        try:
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            return lat, lon
        except:
            return None
    return None

def parse_location(location_str: str, location_type: str = "location"):
    """
    Smart parser: handles both coordinates and address names.
    
    Args:
        location_str: Either "lat,lon" or address name
        location_type: "start" or "goal" (for logging)
    
    Returns:
        (lat, lon) tuple
    """
    # First, try to parse as coordinates
    coord = parse_latlon(location_str)
    if coord is not None:
        print(f"✓ {location_type.capitalize()} coordinates: {coord[0]:.6f}, {coord[1]:.6f}")
        return coord
    
    # If not coordinates, try geocoding
    print(f"Geocoding {location_type} address: '{location_str}'")
    
    # Try custom geocoding helper first (more accurate for Bách Khoa)
    if GEOCODING_AVAILABLE:
        try:
            lat, lon = get_location_with_fallback(location_str)
            print(f"✓ {location_type.capitalize()} geocoded: {lat:.6f}, {lon:.6f}")
            return lat, lon
        except Exception as e:
            print(f"  Custom geocoding failed: {e}")
            print(f"  Falling back to osmnx geocoding...")
    
    # Fallback to osmnx geocoding
    try:
        loc = ox.geocode(location_str)
        lat, lon = loc[0], loc[1]
        print(f"✓ {location_type.capitalize()} geocoded (osmnx): {lat:.6f}, {lon:.6f}")
        return lat, lon
    except Exception as e:
        print(f"✗ Geocoding failed for '{location_str}': {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='Find path between two locations (coordinates or addresses)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using coordinates (original method)
  python run_path.py --start "21.0037,105.8454" --goal "21.0055,105.8490"
  
  # Using full addresses
  python run_path.py --start "Thư viện Tạ Quang Bửu, ĐHBK Hà Nội" --goal "Nhà C1, ĐHBK"
  
  # Using shorthand (if geocode_address.py is available)
  python run_path.py --start "thư viện" --goal "cổng chính"
  
  # Mixed: coordinate + address
  python run_path.py --start "21.0037,105.8454" --goal "Nhà H1, ĐHBK"
        """
    )
    
    parser.add_argument('--north', type=float, default=None)
    parser.add_argument('--south', type=float, default=None)
    parser.add_argument('--east', type=float, default=None)
    parser.add_argument('--west', type=float, default=None)
    parser.add_argument('--save_prefix', type=str, default="bachkhoa_")
    parser.add_argument('--start', type=str, required=True, 
                       help='Start location: "lat,lon" or address name')
    parser.add_argument('--goal', type=str, required=True,
                       help='Goal location: "lat,lon" or address name')
    parser.add_argument('--save_png', type=str, default=None)
    args = parser.parse_args()

    print("=" * 60)
    print("Pathfinding with Address Support")
    print("=" * 60)
    
    # Build/load graph
    if args.north and args.south and args.east and args.west:
        saved = build_and_save_graph(args.north, args.south, args.east, args.west, args.save_prefix)
    else:
        saved = build_and_save_graph(save_prefix=args.save_prefix)

    # Load graph data
    with open(saved['adj_path'], 'rb') as f:
        adj = pickle.load(f)
    with open(saved['nodes_path'], 'rb') as f:
        nodes = pickle.load(f)
    with open(saved['edges_path'], 'rb') as f:
        edges = pickle.load(f)

    print(f"\n[PARSING LOCATIONS]")
    
    # Parse start location (coordinates or address)
    start_coord = parse_location(args.start, "start")
    
    # Parse goal location (coordinates or address)
    goal_coord = parse_location(args.goal, "goal")

    # Calculate straight-line distance
    from math import radians, cos, sin, asin, sqrt
    
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371000  # Earth radius in meters
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        return R * c
    
    straight_dist = haversine(start_coord[0], start_coord[1], goal_coord[0], goal_coord[1])
    print(f"\nStraight-line distance: {straight_dist:.1f}m")

    # Find nearest nodes
    print(f"\n[FINDING NEAREST NODES]")
    start_node = None
    goal_node = None
    try:
        with open(saved['graph_path'], 'rb') as f:
            G = pickle.load(f)
        # osmnx.nearest_nodes expects (G, lon, lat) = (X, Y)
        start_node = ox.nearest_nodes(G, start_coord[1], start_coord[0])
        goal_node = ox.nearest_nodes(G, goal_coord[1], goal_coord[0])
        print(f"✓ Using osmnx nearest_nodes")
    except Exception as e:
        print(f"⚠ Nearest-node via Graph.pkl failed: {e}")
        print(f"  Using brute-force nearest_node_by_coord...")
        start_node = nearest_node_by_coord(nodes, start_coord[0], start_coord[1])
        goal_node = nearest_node_by_coord(nodes, goal_coord[0], goal_coord[1])

    print(f"Start node: {start_node}")
    print(f"Goal node: {goal_node}")

    # Run A* pathfinding
    print(f"\n[PATHFINDING]")
    path, cost_m = astar(adj, nodes, start_node, goal_node)
    
    if not path:
        print("✗ No path found.")
        sys.exit(1)

    print(f"✓ Path found!")
    print(f"  Path length: {len(path)} nodes")
    print(f"  Route distance: {cost_m:.1f}m")
    print(f"  Detour ratio: {cost_m / straight_dist:.2f}x")

    # Visualize and save
    print(f"\n[VISUALIZATION]")
    save_png = args.save_png or os.path.join(DATA_DIR, f"{args.save_prefix}route.png")
    plot_route_with_graph_or_simple(saved['graph_path'], saved['nodes_path'], saved['edges_path'], path, save_png)
    print(f"✓ Saved visualization to: {save_png}")
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)

if __name__ == "__main__":
    main()