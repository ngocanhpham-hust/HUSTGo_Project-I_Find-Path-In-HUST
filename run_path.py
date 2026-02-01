
import argparse
import pickle
import os
import sys

import osmnx as ox

from load_map_bachkhoa import build_and_save_graph, DATA_DIR
from AStar import astar, nearest_node_by_coord
from visualize_map import plot_route_with_graph_or_simple

try:
    from geocode_address import get_location_with_fallback
    GEOCODING_AVAILABLE = True
except ImportError:
    GEOCODING_AVAILABLE = False

def parse_latlon(s: str):
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

def parse_location(location_str: str):
    coord = parse_latlon(location_str)
    if coord is not None:
        return coord
    
    if GEOCODING_AVAILABLE:
        try:
            return get_location_with_fallback(location_str)
        except:
            pass
    
    try:
        loc = ox.geocode(location_str)
        return loc[0], loc[1]
    except Exception as e:
        print(f"Geocoding failed: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Find path between two locations')
    parser.add_argument('--north', type=float, default=None)
    parser.add_argument('--south', type=float, default=None)
    parser.add_argument('--east', type=float, default=None)
    parser.add_argument('--west', type=float, default=None)
    parser.add_argument('--save_prefix', type=str, default="bachkhoa_")
    parser.add_argument('--start', type=str, required=True)
    parser.add_argument('--goal', type=str, required=True)
    parser.add_argument('--save_png', type=str, default=None)
    args = parser.parse_args()

    # load graph
    if args.north and args.south and args.east and args.west:
        saved = build_and_save_graph(args.north, args.south, args.east, args.west, args.save_prefix)
    else:
        saved = build_and_save_graph(save_prefix=args.save_prefix)

    with open(saved['adj_path'], 'rb') as f:
        adj = pickle.load(f)
    with open(saved['nodes_path'], 'rb') as f:
        nodes = pickle.load(f)
    with open(saved['edges_path'], 'rb') as f:
        edges = pickle.load(f)

    start_coord = parse_location(args.start)
    goal_coord = parse_location(args.goal)

    try:
        with open(saved['graph_path'], 'rb') as f:
            G = pickle.load(f)
        start_node = ox.nearest_nodes(G, start_coord[1], start_coord[0])
        goal_node = ox.nearest_nodes(G, goal_coord[1], goal_coord[0])
    except:
        start_node = nearest_node_by_coord(nodes, start_coord[0], start_coord[1])
        goal_node = nearest_node_by_coord(nodes, goal_coord[0], goal_coord[1])

    # run A*
    path, cost_m = astar(adj, nodes, start_node, goal_node)
    
    if not path:
        print("No path found.")
        sys.exit(1)

    print(f"Path: {len(path)} nodes, {cost_m:.1f}m")

    # save visualization
    if args.save_png:
        save_png = args.save_png
    else:
        start_str = f"{start_coord[0]:.4f}_{start_coord[1]:.4f}".replace('.', '')
        goal_str = f"{goal_coord[0]:.4f}_{goal_coord[1]:.4f}".replace('.', '')
        save_png = os.path.join(DATA_DIR, f"{args.save_prefix}route_{start_str}_to_{goal_str}.png")
    
    plot_route_with_graph_or_simple(saved['graph_path'], saved['nodes_path'], saved['edges_path'], path, save_png)
    print(f"Saved: {save_png}")

if __name__ == "__main__":
    main()