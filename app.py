import os
import pickle
from typing import Optional, Tuple, Dict

import streamlit as st
import folium
from streamlit_folium import st_folium

from load_map_bachkhoa import build_and_save_graph, DATA_DIR
from AStar import astar, nearest_node_by_coord
from calcDist import haversine_m

# Optional config
try:
    from config import BACHKHOA_BBOX, DEFAULT_SAVE_PREFIX, COMMON_LOCATIONS as CFG_LOCATIONS
except Exception:
    BACHKHOA_BBOX = {'north': 21.0110, 'south': 21.0020, 'east': 105.8530, 'west': 105.8400}
    DEFAULT_SAVE_PREFIX = "bachkhoa_"
    CFG_LOCATIONS = {}

# Optional geocoding
try:
    from geocode_address import get_location_with_fallback, COMMON_LOCATIONS as GEO_LOCATIONS
    GEOCODING_AVAILABLE = True
except Exception:
    get_location_with_fallback = None
    GEO_LOCATIONS = {}
    GEOCODING_AVAILABLE = False


st.set_page_config(page_title="Bách Khoa Pathfinding", page_icon="🗺️", layout="wide")

st.markdown(
    """
    <style>
      .title {font-size: 26px; font-weight: 800; margin: 0.2rem 0 1rem 0;}
      .card {border:1px solid #e5e7eb; border-radius: 12px; padding: 14px;}
      .stButton>button {border-radius: 12px; height: 42px;}
    </style>
    """,
    unsafe_allow_html=True
)


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


@st.cache_resource(show_spinner=False)
def get_graph(save_prefix: str = DEFAULT_SAVE_PREFIX):
    """
    Auto-load if cached files exist; otherwise build once then load.
    No extra buttons needed.
    """
    gd = load_graph_data(save_prefix)
    if gd is not None:
        return gd

    # Build once (first run)
    build_and_save_graph(
        north=BACHKHOA_BBOX["north"],
        south=BACHKHOA_BBOX["south"],
        east=BACHKHOA_BBOX["east"],
        west=BACHKHOA_BBOX["west"],
        save_prefix=save_prefix,
        force_download=False,
    )
    return load_graph_data(save_prefix)


def parse_location(text: str) -> Tuple[Optional[float], Optional[float]]:
    if not text:
        return None, None
    s = text.strip()

    # "lat, lon"
    if "," in s:
        parts = s.split(",")
        if len(parts) >= 2:
            try:
                return float(parts[0].strip()), float(parts[1].strip())
            except ValueError:
                pass

    # geocoding fallback
    if GEOCODING_AVAILABLE and get_location_with_fallback is not None:
        try:
            return get_location_with_fallback(s)
        except Exception:
            return None, None

    return None, None


def nearest_node(graph_data, lat: float, lon: float) -> int:
    try:
        import osmnx as ox
        return ox.nearest_nodes(graph_data["graph"], lon, lat)
    except Exception:
        return nearest_node_by_coord(graph_data["nodes"], lat, lon)


def route_coords(nodes, path):
    return [(nodes[n].lat, nodes[n].lon) for n in path]


def build_map(start, goal, coords):
    center = [(start[0] + goal[0]) / 2, (start[1] + goal[1]) / 2]
    m = folium.Map(location=center, zoom_start=16, control_scale=True)

    folium.Marker(list(start), tooltip="Start", icon=folium.Icon(color="green", icon="play")).add_to(m)
    folium.Marker(list(goal), tooltip="Goal", icon=folium.Icon(color="red", icon="flag")).add_to(m)

    folium.PolyLine(coords, weight=6, opacity=0.9).add_to(m)

    m.fit_bounds(coords + [start, goal])
    return m


# ---------------- UI ----------------
st.markdown('<div class="title">🗺️ Bách Khoa Pathfinding</div>', unsafe_allow_html=True)

# Auto graph (no buttons)
with st.spinner("Loading map data..."):
    graph_data = get_graph(DEFAULT_SAVE_PREFIX)
if graph_data is None:
    st.error("Graph data is not available.")
    st.stop()

left, right = st.columns([1, 2], gap="large")

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)

    # Start
    start_options = ["Custom"] + list(COMMON_LOCATIONS.keys()) if COMMON_LOCATIONS else ["Custom"]
    start_pick = st.selectbox("Start", start_options)
    if start_pick != "Custom":
        s_lat, s_lon = COMMON_LOCATIONS[start_pick]
        start_text = f"{s_lat}, {s_lon}"
        st.text_input("Start input", value=start_text, disabled=True, label_visibility="collapsed")
    else:
        start_text = st.text_input("Start input", placeholder="lat, lon hoặc tên địa điểm", label_visibility="collapsed")
        s_lat, s_lon = parse_location(start_text)

    # Goal
    goal_options = ["Custom"] + list(COMMON_LOCATIONS.keys()) if COMMON_LOCATIONS else ["Custom"]
    goal_pick = st.selectbox("Goal", goal_options)
    if goal_pick != "Custom":
        g_lat, g_lon = COMMON_LOCATIONS[goal_pick]
        goal_text = f"{g_lat}, {g_lon}"
        st.text_input("Goal input", value=goal_text, disabled=True, label_visibility="collapsed")
    else:
        goal_text = st.text_input("Goal input", placeholder="lat, lon hoặc tên địa điểm", label_visibility="collapsed")
        g_lat, g_lon = parse_location(goal_text)

    find_btn = st.button("Find path", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


with right:
    # Default empty map
    center_lat = (BACHKHOA_BBOX["north"] + BACHKHOA_BBOX["south"]) / 2
    center_lon = (BACHKHOA_BBOX["east"] + BACHKHOA_BBOX["west"]) / 2

    if find_btn:
        if s_lat is None or g_lat is None:
            st.error("Invalid Start/Goal.")
            m = folium.Map(location=[center_lat, center_lon], zoom_start=16, control_scale=True)
            st_folium(m, width=None, height=640)
        else:
            with st.spinner("Searching..."):
                s_node = nearest_node(graph_data, s_lat, s_lon)
                g_node = nearest_node(graph_data, g_lat, g_lon)
                path, cost_m = astar(graph_data["adj"], graph_data["nodes"], s_node, g_node)

            if not path:
                st.error("No path found.")
                m = folium.Map(location=[center_lat, center_lon], zoom_start=16, control_scale=True)
                st_folium(m, width=None, height=640)
            else:
                coords = route_coords(graph_data["nodes"], path)
                m = build_map((s_lat, s_lon), (g_lat, g_lon), coords)
                st_folium(m, width=None, height=640)

                # minimal info (optional but practical)
                st.caption(f"Route distance: {float(cost_m):.1f} m | Nodes: {len(path)} | Straight-line: {haversine_m(s_lat, s_lon, g_lat, g_lon):.1f} m")
    else:
        m = folium.Map(location=[center_lat, center_lon], zoom_start=16, control_scale=True)
        st_folium(m, width=None, height=640)