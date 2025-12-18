# visualize_map.py
import pickle
import os
from typing import List, Dict, Optional, Tuple

import matplotlib.pyplot as plt
import networkx as nx
import osmnx as ox

from point import Point

def plot_route_with_osmnx(G, route: List[int], filepath: Optional[str] = None):
    fig, ax = ox.plot_graph_route(G, route, show=False, close=False)
    if filepath:
        fig.savefig(filepath, dpi=150)
        plt.close(fig)
    else:
        plt.show()

def plot_route_simple(nodes: Dict[int, Point], edges: List[Tuple[int,int,float]],
                      route: List[int], filepath: Optional[str] = None):
    G = nx.DiGraph()
    for nid, p in nodes.items():
        G.add_node(nid, x=p.lon, y=p.lat)
    for u,v,w in edges:
        if u in nodes and v in nodes:
            G.add_edge(u, v)
    pos = {n: (nodes[n].lon, nodes[n].lat) for n in G.nodes()}
    plt.figure(figsize=(8,8))
    nx.draw(G, pos=pos, node_size=6, linewidths=0.2, alpha=0.6)
    if route and len(route) >= 2:
        route_edges = list(zip(route[:-1], route[1:]))
        nx.draw_networkx_nodes(G, pos=pos, nodelist=route, node_size=25, node_color='red')
        nx.draw_networkx_edges(G, pos=pos, edgelist=route_edges, width=2.0, edge_color='red')
    if filepath:
        plt.savefig(filepath, dpi=150)
        plt.close()
    else:
        plt.show()

def plot_route_with_graph_or_simple(graph_path: str,
                                    nodes_path: str,
                                    edges_path: str,
                                    route: List[int],
                                    save_png: Optional[str] = None):
    if os.path.exists(graph_path):
        try:
            with open(graph_path, 'rb') as f:
                G = pickle.load(f)
            plot_route_with_osmnx(G, route, filepath=save_png)
            return
        except Exception as e:
            print("Failed to use graph pickle for plotting:", e)
    with open(nodes_path, 'rb') as f:
        nodes = pickle.load(f)
    with open(edges_path, 'rb') as f:
        edges = pickle.load(f)
    plot_route_simple(nodes, edges, route, filepath=save_png)
