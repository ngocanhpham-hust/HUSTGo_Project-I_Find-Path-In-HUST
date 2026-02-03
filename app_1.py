import os
import pickle
from typing import Optional, Tuple, Dict

import streamlit as st
import folium
from streamlit_folium import st_folium

from load_map_bachkhoa import build_and_save_graph, DATA_DIR
from AStar import astar, nearest_node_by_coord
from calcDist import haversine_m

try:
    from geocode_address import get_location_with_fallback, COMMON_LOCATIONS as GEO_LOCATIONS
    GEOCODING_AVAILABLE = True
except Exception:
    get_location_with_fallback = None
    GEO_LOCATIONS = {}
    GEOCODING_AVAILABLE = False

try:
    from config import BACHKHOA_BBOX, DEFAULT_SAVE_PREFIX, COMMON_LOCATIONS as CFG_LOCATIONS
except Exception:
    BACHKHOA_BBOX = {'north': 21.0110, 'south': 21.0020, 'east': 105.8530, 'west': 105.8400}
    DEFAULT_SAVE_PREFIX = "bachkhoa_"
    CFG_LOCATIONS = {}


st.set_page_config(page_title="HUSTGo", page_icon="🗺️", layout="wide")
st.markdown(
    """
    <style>
      .app-title {font-size: 28px; font-weight: 800; margin: 0.2rem 0 1rem 0;}
      .subtle {color: #6b7280; font-size: 0.95rem; margin-top: -0.4rem;}
      .card {border: 1px solid #e5e7eb; border-radius: 12px; padding: 14px;}
      .metric {border: 1px solid #e5e7eb; border-radius: 12px; padding: 12px;}
      .stButton>button {border-radius: 12px; height: 42px;}
    </style>
    """,
    unsafe_allow_html=True
)


# utils 

def merge_locations() -> Dict[str, Tuple[float, float]]:
    merged = {}
    merged.update(CFG_LOCATIONS or {})
    merged.update(GEO_LOCATIONS or {})
    return dict(sorted(merged.items(), key=lambda x: x[0].lower()))

COMMON_LOCATIONS = merge_locations()


@st.cache_data(show_spinner=False)
def load_graph_data(save_prefix: str = DEFAULT_SAVE_PREFIX):
    adj_path = os.path.join(DATA_DIR, f"{save_prefix}Adj.pkl")
    nodes_path = os.path.join(DATA_DIR, f"{save_prefix}Nodes.pkl")
    edges_path = os.path.join(DATA_DIR, f"{save_prefix}Edges.pkl")
    graph_path = os.path.join(DATA_DIR, f"{save_prefix}Graph.pkl")

    if not all(os.path.exists(p) for p in [adj_path, nodes_path, edges_path, graph_path]):
        return None

    with open(adj_path, "rb") as f:
        adj = pickle.load(f)
    with open(nodes_path, "rb") as f:
        nodes = pickle.load(f)
    with open(edges_path, "rb") as f:
        edges = pickle.load(f)
    with open(graph_path, "rb") as f:
        G = pickle.load(f)

    return {"adj": adj, "nodes": nodes, "edges": edges, "graph": G}


def parse_location(text: str) -> Tuple[Optional[float], Optional[float]]:
    """Accept 'lat, lon' or name (geocoding fallback if available)."""
    if not text:
        return None, None

    s = text.strip()

    if "," in s:
        parts = s.split(",")
        if len(parts) >= 2:
            try:
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
                return lat, lon
            except ValueError:
                pass

    if GEOCODING_AVAILABLE and get_location_with_fallback is not None:
        try:
            return get_location_with_fallback(s)
        except Exception:
            return None, None

    return None, None


def nearest_node(graph_data, lat: float, lon: float) -> int:
    """Prefer OSMnx nearest_nodes if available; fallback to manual search."""
    try:
        import osmnx as ox
        return ox.nearest_nodes(graph_data["graph"], lon, lat)
    except Exception:
        return nearest_node_by_coord(graph_data["nodes"], lat, lon)


def route_polyline(nodes, path):
    """Convert path node ids -> list of (lat, lon)."""
    coords = []
    for nid in path:
        p = nodes[nid]  
        coords.append((p.lat, p.lon))
    return coords


def build_map(start_lat, start_lon, goal_lat, goal_lon, route_coords):
    center_lat = (start_lat + goal_lat) / 2
    center_lon = (start_lon + goal_lon) / 2

    m = folium.Map(location=[center_lat, center_lon], zoom_start=16, control_scale=True)

    folium.Marker(
        [start_lat, start_lon],
        tooltip="Start",
        icon=folium.Icon(color="green", icon="play"),
    ).add_to(m)

    folium.Marker(
        [goal_lat, goal_lon],
        tooltip="Goal",
        icon=folium.Icon(color="red", icon="flag"),
    ).add_to(m)

    folium.PolyLine(route_coords, weight=6, opacity=0.9).add_to(m)

    bounds = route_coords + [(start_lat, start_lon), (goal_lat, goal_lon)]
    m.fit_bounds(bounds)

    return m


if "graph_data" not in st.session_state:
    st.session_state.graph_data = None
if "result" not in st.session_state:
    st.session_state.result = None


st.markdown('<div class="app-title">🏨 HUSTGo</div>', unsafe_allow_html=True)
st.markdown('<div class="subtle">Tìm đường trong Đại học Bách khoa Hà Nội</div>', unsafe_allow_html=True)
st.write("")


with st.sidebar:
    st.subheader("Graph")
    save_prefix = st.text_input("Save prefix", value=DEFAULT_SAVE_PREFIX)

    colA, colB = st.columns(2)
    with colA:
        load_btn = st.button("Load", use_container_width=True)
    with colB:
        rebuild_btn = st.button("Rebuild", use_container_width=True)

    if load_btn:
        gd = load_graph_data(save_prefix)
        if gd is None:
            st.warning("No saved graph found. Use Rebuild.")
        else:
            st.session_state.graph_data = gd
            st.success("Graph loaded")

    if rebuild_btn:
        with st.spinner("Building graph..."):
            build_and_save_graph(
                north=BACHKHOA_BBOX["north"],
                south=BACHKHOA_BBOX["south"],
                east=BACHKHOA_BBOX["east"],
                west=BACHKHOA_BBOX["west"],
                save_prefix=save_prefix,
                force_download=True,
            )
        gd = load_graph_data(save_prefix)
        st.session_state.graph_data = gd
        st.success("Graph rebuilt & loaded")

    if st.session_state.graph_data is not None:
        gd = st.session_state.graph_data
        st.caption(f"Nodes: {len(gd['nodes'])}  |  Edges: {len(gd['edges'])}")


# app UI

graph_data = st.session_state.graph_data
if graph_data is None:
    st.info("Load graph from the sidebar to start.")
    st.stop()

left, right = st.columns([1, 2], gap="large")

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Route")

    start_mode = st.radio("Start", ["Chọn nhanh", "Nhập"], horizontal=True, label_visibility="collapsed")
    if start_mode == "Chọn nhanh" and COMMON_LOCATIONS:
        start_name = st.selectbox("Start location", list(COMMON_LOCATIONS.keys()))
        s_lat, s_lon = COMMON_LOCATIONS[start_name]
    else:
        start_text = st.text_input("Start location", placeholder="lat, lon hoặc tên địa điểm")
        s_lat, s_lon = parse_location(start_text)

    goal_mode = st.radio("Goal", ["Chọn nhanh", "Nhập"], horizontal=True, label_visibility="collapsed")
    if goal_mode == "Chọn nhanh" and COMMON_LOCATIONS:
        goal_name = st.selectbox("Goal location", list(COMMON_LOCATIONS.keys()))
        g_lat, g_lon = COMMON_LOCATIONS[goal_name]
    else:
        goal_text = st.text_input("Goal location", placeholder="lat, lon hoặc tên địa điểm")
        g_lat, g_lon = parse_location(goal_text)

    find_btn = st.button("Find path", type="primary", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    if find_btn:
        if s_lat is None or g_lat is None:
            st.error("Invalid start/goal input.")
        else:
            with st.spinner("Searching..."):
                start_node = nearest_node(graph_data, s_lat, s_lon)
                goal_node = nearest_node(graph_data, g_lat, g_lon)

                path, cost_m = astar(graph_data["adj"], graph_data["nodes"], start_node, goal_node)

                if not path:
                    st.session_state.result = None
                    st.error("No path found.")
                else:
                    st.session_state.result = {
                        "path": path,
                        "cost_m": float(cost_m),
                        "start": (s_lat, s_lon),
                        "goal": (g_lat, g_lon),
                        "start_node": int(start_node),
                        "goal_node": int(goal_node),
                    }

with right:
    res = st.session_state.result

    if res is None:
        center_lat = (BACHKHOA_BBOX["north"] + BACHKHOA_BBOX["south"]) / 2
        center_lon = (BACHKHOA_BBOX["east"] + BACHKHOA_BBOX["west"]) / 2
        m = folium.Map(location=[center_lat, center_lon], zoom_start=16, control_scale=True)
        st_folium(m, width=None, height=640)
    else:
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown('<div class="metric">', unsafe_allow_html=True)
            st.caption("Route distance")
            st.markdown(f"### {res['cost_m']:.1f} m")
            st.markdown("</div>", unsafe_allow_html=True)
        with m2:
            st.markdown('<div class="metric">', unsafe_allow_html=True)
            st.caption("Path nodes")
            st.markdown(f"### {len(res['path'])}")
            st.markdown("</div>", unsafe_allow_html=True)
        with m3:
            st.markdown('<div class="metric">', unsafe_allow_html=True)
            st.caption("Straight-line")
            sd = haversine_m(res["start"][0], res["start"][1], res["goal"][0], res["goal"][1])
            st.markdown(f"### {sd:.1f} m")
            st.markdown("</div>", unsafe_allow_html=True)

        route_coords = route_polyline(graph_data["nodes"], res["path"])
        m = build_map(res["start"][0], res["start"][1], res["goal"][0], res["goal"][1], route_coords)
        st_folium(m, width=None, height=640)