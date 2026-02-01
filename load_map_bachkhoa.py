import os
import pickle
import time
from typing import Dict, List, Tuple

import osmnx as ox

from point import Point
from calcDist import haversine_m

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

def build_and_save_graph(north: float = 21.0110,
                         south: float = 21.0020,
                         east: float = 105.8530,
                         west: float = 105.8400,
                         save_prefix: str = "bachkhoa_",
                         force_download: bool = False):

    adj_path = os.path.join(DATA_DIR, f"{save_prefix}Adj.pkl")
    nodes_path = os.path.join(DATA_DIR, f"{save_prefix}Nodes.pkl")
    edges_path = os.path.join(DATA_DIR, f"{save_prefix}Edges.pkl")
    graph_path = os.path.join(DATA_DIR, f"{save_prefix}Graph.pkl")

    if (not force_download) and all(os.path.exists(p) for p in [adj_path, nodes_path, edges_path, graph_path]):
        return {"adj_path": adj_path, "nodes_path": nodes_path, "edges_path": edges_path, "graph_path": graph_path}

    # Optimized settings
    ox.settings.use_cache = False
    ox.settings.log_console = True
    ox.settings.timeout = 300
    
    # Calculate center point and distance
    center_lat = (north + south) / 2
    center_lon = (east + west) / 2
    
    # Calculate approximate distance
    lat_dist = (north - south) * 111000  
    lon_dist = (east - west) * 111000 * abs(center_lat/90) 
    dist = max(lat_dist, lon_dist) / 2 * 1.2  
    
    print(f"Downloading graph from OSM ")
    print(f"Center: ({center_lat:.6f}, {center_lon:.6f})")
    print(f"Distance: {dist:.0f}m")
    print(f"Expected bbox: N={north:.4f}, S={south:.4f}, E={east:.4f}, W={west:.4f}")
    
    G = None
    start_time = time.perf_counter()
    
    try:
        G = ox.graph_from_point(
            (center_lat, center_lon),
            dist=dist,
            network_type='all',
            simplify=True
        )
        
    except Exception as ex:
        print(f"Method 1 failed: {type(ex).__name__}: {ex}")
        
        try:
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
            
            try:
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
    print(f"Nodes: {len(G.nodes)}, Edges: {len(G.edges)}")

    # Verify coordinates
    print(f"\nVerifying node coordinates (first 5 nodes):")

    sample_coords = []
    for i, (nid, data) in enumerate(G.nodes(data=True)):
        if i < 5:
            lat, lon = data['y'], data['x']
            sample_coords.append((lat, lon))
            print(f"  Node {nid}: lat={lat:.6f}, lon={lon:.6f}")
    
    if sample_coords:
        avg_lat = sum(c[0] for c in sample_coords) / len(sample_coords)
        avg_lon = sum(c[1] for c in sample_coords) / len(sample_coords)
        
        # Check if coordinates are in corect range
        lat_ok = south <= avg_lat <= north
        lon_ok = west <= avg_lon <= east
        
        print(f"\nAverage coordinates: lat={avg_lat:.6f}, lon={avg_lon:.6f}")
        print(f"Expected range: lat=[{south:.4f}, {north:.4f}], lon=[{west:.4f}, {east:.4f}]")
        
        # Calculate actual dimensions
        lat_dist = (north - south) * 111000  
        lon_dist = (east - west) * 111000 * abs(center_lat/90)  
        area_km2 = (lat_dist / 1000) * (lon_dist / 1000)
        print(f"Bounding box: {lat_dist:.0f}m x {lon_dist:.0f}m, Area: {area_km2:.2f} km²")
        
        if lat_ok and lon_ok:
            print("COORDINATES CORRECT!")
        else:
            print("COORDINATES WRONG!")
            if not lat_ok:
                print(f"  Latitude out of range: {avg_lat:.6f} not in [{south:.4f}, {north:.4f}]")
            if not lon_ok:
                print(f"  Longitude out of range: {avg_lon:.6f} not in [{west:.4f}, {east:.4f}]")
                print(f"  Deviation: ~{abs(avg_lon - center_lon) * 111 * 1000:.0f}m")
    
    area_km2 = (north - south) * (east - west) * 111 * 111
    density = len(G.nodes) / area_km2
    print(f"\nNode density: {len(G.nodes)} nodes / {area_km2:.3f} km² = {density:.0f} nodes/km²")

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
    
    paths = build_and_save_graph()
    
    try:
        with open(paths["graph_path"], 'rb') as f:
            G = pickle.load(f)
        
        fig, ax = ox.plot_graph(G, figsize=(12, 12), 
                                node_size=5, 
                                node_color='blue',
                                edge_color='gray',
                                edge_linewidth=0.5,
                                bgcolor='white',
                                show=False, 
                                close=False)
        
        output_path = os.path.join(DATA_DIR, "bachkhoa_map.png")
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\nMap saved to: {output_path}")
        
        plt.show()
        
    except Exception as e:
        print(f"Visualization failed: {e}")