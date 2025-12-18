"""
Build and save a simplified OSM graph (bbox API compatible with modern osmnx).
Saves into ./data folder (created if missing).

Usage:
    from load_map_bachkhoa import build_and_save_graph
    build_and_save_graph()
"""

import os
import pickle
import time
from typing import Dict, List, Tuple

import osmnx as ox

from point import Point
from calcDist import haversine_m

# Save data into ./data (same folder as this file)
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

def build_and_save_graph(north: float = 21.0065,
                         south: float = 21.0015,
                         east: float = 105.8495,
                         west: float = 105.8425,
                         save_prefix: str = "bachkhoa_",
                         force_download: bool = False):
    """
    Build graph from OSM via overpass for given bbox tuple and save adj/nodes/edges/graph.
    OPTIMIZED: Get ALL walkable paths including pedestrian, service roads, and paths.
    """
    adj_path = os.path.join(DATA_DIR, f"{save_prefix}Adj.pkl")
    nodes_path = os.path.join(DATA_DIR, f"{save_prefix}Nodes.pkl")
    edges_path = os.path.join(DATA_DIR, f"{save_prefix}Edges.pkl")
    graph_path = os.path.join(DATA_DIR, f"{save_prefix}Graph.pkl")

    if (not force_download) and all(os.path.exists(p) for p in [adj_path, nodes_path, edges_path, graph_path]):
        print("Pickles already exist. Loading paths.")
        return {"adj_path": adj_path, "nodes_path": nodes_path, "edges_path": edges_path, "graph_path": graph_path}

    # Optimized settings
    ox.settings.use_cache = False
    ox.settings.log_console = True
    ox.settings.timeout = 300
    
    # Calculate center point and distance
    center_lat = (north + south) / 2
    center_lon = (east + west) / 2
    
    # Calculate approximate distance
    lat_dist = (north - south) * 111000  # ~555m
    lon_dist = (east - west) * 111000 * abs(center_lat/90)  # ~777m
    dist = max(lat_dist, lon_dist) / 2 * 1.2  # Add 20% buffer
    
    print(f"Downloading graph from OSM (Bách Khoa area - ALL roads)...")
    print(f"Center: ({center_lat:.6f}, {center_lon:.6f})")
    print(f"Distance: {dist:.0f}m")
    print(f"Expected bbox: N={north:.4f}, S={south:.4f}, E={east:.4f}, W={west:.4f}")
    
    G = None
    start_time = time.perf_counter()
    
    try:
        # METHOD 1: Use 'all' network type to get everything
        print("\n[Method 1] Using network_type='all' to get all roads...")
        G = ox.graph_from_point(
            (center_lat, center_lon),
            dist=dist,
            network_type='all',  # Changed from 'drive' to 'all'
            simplify=True
        )
        
    except Exception as ex:
        print(f"Method 1 failed: {type(ex).__name__}: {ex}")
        print("\n[Method 2] Trying custom filter for all road types...")
        
        try:
            # METHOD 2: Custom filter with comprehensive road types
            custom_filter = (
                '["highway"]["area"!~"yes"]["highway"!~"abandoned|bus_guideway|'
                'construction|corridor|elevator|escalator|planned|platform|'
                'proposed|raceway"]'
            )
            G = ox.graph_from_point(
                (center_lat, center_lon),
                dist=dist,
                custom_filter=custom_filter,
                simplify=True
            )
        except Exception as ex2:
            print(f"Method 2 failed: {type(ex2).__name__}: {ex2}")
            print("\n[Method 3] Trying network_type='all_private'...")
            
            try:
                # METHOD 3: all_private includes private roads (common in universities)
                G = ox.graph_from_point(
                    (center_lat, center_lon),
                    dist=dist,
                    network_type='all_private',
                    simplify=True
                )
            except Exception as ex3:
                print(f"All methods failed. Last error: {type(ex3).__name__}: {ex3}")
                raise RuntimeError("Cannot download OSM data.") from ex3

    elapsed = time.perf_counter() - start_time
    print(f"\nGraph downloaded in {elapsed:.1f}s. Nodes: {len(G.nodes)}, Edges: {len(G.edges)}")

    # CRITICAL: Verify coordinates
    print(f"\n{'='*60}")
    print("VERIFYING COORDINATES:")
    print(f"{'='*60}")
    
    sample_coords = []
    for i, (nid, data) in enumerate(G.nodes(data=True)):
        if i < 5:
            lat, lon = data['y'], data['x']
            sample_coords.append((lat, lon))
            print(f"  Node {nid}: lat={lat:.6f}, lon={lon:.6f}")
    
    if sample_coords:
        avg_lat = sum(c[0] for c in sample_coords) / len(sample_coords)
        avg_lon = sum(c[1] for c in sample_coords) / len(sample_coords)
        
        # Check if coordinates are in CORRECT range
        lat_ok = south <= avg_lat <= north
        lon_ok = west <= avg_lon <= east
        
        print(f"\nAverage coordinates: lat={avg_lat:.6f}, lon={avg_lon:.6f}")
        print(f"Expected range: lat=[{south:.4f}, {north:.4f}], lon=[{west:.4f}, {east:.4f}]")
        
        if lat_ok and lon_ok:
            print("✓ ✓ ✓ COORDINATES CORRECT! ✓ ✓ ✓")
        else:
            print("✗ ✗ ✗ WARNING: COORDINATES WRONG! ✗ ✗ ✗")
            if not lat_ok:
                print(f"  Latitude out of range: {avg_lat:.6f} not in [{south:.4f}, {north:.4f}]")
            if not lon_ok:
                print(f"  Longitude out of range: {avg_lon:.6f} not in [{west:.4f}, {east:.4f}]")
                print(f"  Deviation: ~{abs(avg_lon - center_lon) * 111 * 1000:.0f}m")
    
    # Show node density
    area_km2 = (north - south) * (east - west) * 111 * 111
    density = len(G.nodes) / area_km2
    print(f"\nNode density: {len(G.nodes)} nodes / {area_km2:.3f} km² = {density:.0f} nodes/km²")
    
    if len(G.nodes) < 50:
        print("⚠ WARNING: Very few nodes! Consider using network_type='all' or custom filter.")
    elif len(G.nodes) < 100:
        print("⚠ Note: Moderate node count. May be sufficient depending on use case.")
    else:
        print("✓ Good node density for routing!")
    
    print(f"{'='*60}\n")

    # Build nodes dict and adjacency list and edges list
    nodes = {}
    for nid, data in G.nodes(data=True):
        lat = data.get('y')
        lon = data.get('x')
        nodes[nid] = Point(id=nid, lat=lat, lon=lon)

    adj: Dict[int, List[Tuple[int, float]]] = {}
    edges: List[Tuple[int, int, float]] = []

    for u, v, key, data in G.edges(keys=True, data=True):
        length = data.get('length')
        if length is None or length <= 0:
            pu = nodes[u]
            pv = nodes[v]
            length = haversine_m(pu.lat, pu.lon, pv.lat, pv.lon)
        length = float(length)
        edges.append((u, v, length))
        adj.setdefault(u, []).append((v, length))

    # Save using highest protocol
    with open(adj_path, 'wb') as f:
        pickle.dump(adj, f, protocol=pickle.HIGHEST_PROTOCOL)
    with open(nodes_path, 'wb') as f:
        pickle.dump(nodes, f, protocol=pickle.HIGHEST_PROTOCOL)
    with open(edges_path, 'wb') as f:
        pickle.dump(edges, f, protocol=pickle.HIGHEST_PROTOCOL)
    with open(graph_path, 'wb') as f:
        pickle.dump(G, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"Saved files:")
    print(f"  {adj_path}")
    print(f"  {nodes_path}")
    print(f"  {edges_path}")
    print(f"  {graph_path}")
    
    return {"adj_path": adj_path, "nodes_path": nodes_path, "edges_path": edges_path, "graph_path": graph_path}

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    
    print("=" * 60)
    print("Building and saving graph...")
    print("=" * 60)
    
    paths = build_and_save_graph()
    
    print("\n" + "=" * 60)
    print("Visualizing map...")
    print("=" * 60)
    
    try:
        with open(paths["graph_path"], 'rb') as f:
            G = pickle.load(f)
        
        fig, ax = ox.plot_graph(G, figsize=(12, 12), 
                                node_size=5,  # Smaller nodes for dense graph
                                node_color='blue',
                                edge_color='gray',
                                edge_linewidth=0.5,
                                bgcolor='white',
                                show=False, 
                                close=False)
        
        output_path = os.path.join(DATA_DIR, "bachkhoa_map.png")
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\n✓ Map saved to: {output_path}")
        
        plt.show()
        print("✓ Map displayed on screen")
        
    except Exception as e:
        print(f"✗ Visualization failed: {e}")