import os
import pickle
import re
import math
from typing import Dict, Tuple, Optional, List, Any

import streamlit as st
import folium
from streamlit.components.v1 import html as st_html

from AStar import astar, nearest_node_by_coord
from load_map_bachkhoa import build_and_save_graph

try:
    from geocode_address import get_location_with_fallback
    from geocode_address import COMMON_LOCATIONS as COMMON_LOCATIONS_GEO
    GEOCODING_AVAILABLE = True
except Exception:
    GEOCODING_AVAILABLE = False
    COMMON_LOCATIONS_GEO = {}

try:
    from config import COMMON_LOCATIONS as COMMON_LOCATIONS_CFG
except Exception:
    COMMON_LOCATIONS_CFG = {}


def parse_latlon(text: str) -> Optional[Tuple[float, float]]:
    if not text:
        return None
    s = text.strip()
    m = re.match(r"^\s*([+-]?\d+(?:\.\d+)?)\s*[, ]\s*([+-]?\d+(?:\.\d+)?)\s*$", s)
    if not m:
        return None
    return (float(m.group(1)), float(m.group(2)))


def normalize_key(s: str) -> str:
    return (s or "").strip().lower()


def pick_common_locations() -> Dict[str, Tuple[float, float]]:
    merged: Dict[str, Tuple[float, float]] = {}
    for d in (COMMON_LOCATIONS_CFG, COMMON_LOCATIONS_GEO):
        for k, v in (d or {}).items():
            merged[str(k)] = (float(v[0]), float(v[1]))
    if not merged:
        merged = {
            "Cổng chính": (21.00370, 105.84540),
            "Thư viện": (21.00378, 105.84548),
        }
    return dict(sorted(merged.items(), key=lambda x: x[0].lower()))


def estimate_time(distance_m: float, mode: str) -> float:
    speeds_kmh = {"Đi bộ": 4.5, "Xe đạp": 12.0, "Xe máy": 25.0}
    v = speeds_kmh.get(mode, 4.5)
    return (distance_m / 1000.0) / v * 60.0


@st.cache_resource(show_spinner=False)
def load_graph(force_download: bool = False):
    saved = build_and_save_graph(force_download=force_download)

    with open(saved["adj_path"], "rb") as f:
        adj = pickle.load(f)
    with open(saved["nodes_path"], "rb") as f:
        nodes = pickle.load(f)
    with open(saved["edges_path"], "rb") as f:
        edges = pickle.load(f)

    G = None
    try:
        with open(saved["graph_path"], "rb") as f:
            G = pickle.load(f)
    except Exception:
        G = None

    return saved, adj, nodes, edges, G


def resolve_location(text: str, commons: Dict[str, Tuple[float, float]]) -> Tuple[float, float]:
    t = (text or "").strip()
    if not t:
        raise ValueError("Chưa nhập địa điểm.")

    coord = parse_latlon(t)
    if coord:
        return coord

    key = normalize_key(t)
    for name, c in commons.items():
        if normalize_key(name) == key:
            return c
    for name, c in commons.items():
        if key and key in normalize_key(name):
            return c

    if GEOCODING_AVAILABLE:
        loc = get_location_with_fallback(t)
        if loc:
            return (loc[0], loc[1])

    raise ValueError("Không nhận diện được địa điểm. Hãy chọn gợi ý hoặc nhập dạng lat, lon.")


def nearest_node(nodes: Dict[Any, Any], lat: float, lon: float):
    return nearest_node_by_coord(nodes, lat, lon)


def build_map(
    center: Tuple[float, float],
    start: Tuple[float, float],
    goal: Tuple[float, float],
    route_coords: List[Tuple[float, float]],
    show_markers: bool = True,
) -> folium.Map:
    m = folium.Map(location=center, zoom_start=17, control_scale=True, tiles="OpenStreetMap")
    if show_markers:
        folium.Marker(location=start, tooltip="Xuất phát", icon=folium.Icon(color="green")).add_to(m)
        folium.Marker(location=goal, tooltip="Đích", icon=folium.Icon(color="red")).add_to(m)

    if route_coords:
        folium.PolyLine(route_coords, weight=6, opacity=0.9).add_to(m)
        lats = [p[0] for p in route_coords] + [start[0], goal[0]]
        lons = [p[1] for p in route_coords] + [start[1], goal[1]]
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])
    return m


def render_folium(m: folium.Map, height: int = 640):
    st_html(m.get_root().render(), height=height)


# -------------------- Directions --------------------

def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing from point1 to point2 (0..360)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlon)
    b = (math.degrees(math.atan2(y, x)) + 360.0) % 360.0
    return b


def _delta_bearing(b1: float, b2: float) -> float:
    """Signed smallest difference b2 - b1 in degrees (-180..180)."""
    d = (b2 - b1 + 180.0) % 360.0 - 180.0
    return d


def _edge_best_data(G, u, v) -> Optional[dict]:
    if G is None:
        return None
    try:
        data = G.get_edge_data(u, v)
        if not data:
            return None
        # MultiDiGraph: data is dict of keys -> attr dict
        best = None
        best_len = float("inf")
        for k, attrs in data.items():
            L = attrs.get("length", float("inf"))
            if L < best_len:
                best_len = L
                best = attrs
        return best or next(iter(data.values()))
    except Exception:
        return None


def _edge_name(attrs: Optional[dict]) -> str:
    if not attrs:
        return ""
    nm = attrs.get("name", "")
    if isinstance(nm, (list, tuple)):
        nm = " / ".join([str(x) for x in nm if x])
    return str(nm or "").strip()


def _edge_length_m(attrs: Optional[dict], lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    if attrs and isinstance(attrs.get("length", None), (int, float)):
        return float(attrs["length"])
    # fallback: rough distance
    # haversine quick
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def build_directions(path_nodes: List[Any], nodes: Dict[Any, Any], G, origin_label: str, dest_label: str):
    """
    Trả về danh sách bước chỉ đường dạng:
    [{"step": 1, "instruction": "...", "distance_m": 120}, ...]
    """
    if not path_nodes or len(path_nodes) < 2:
        return []

    pts = [(nodes[n].lat, nodes[n].lon) for n in path_nodes]

    # Build raw segments
    segs = []
    for i in range(len(path_nodes) - 1):
        u = path_nodes[i]
        v = path_nodes[i + 1]
        lat1, lon1 = pts[i]
        lat2, lon2 = pts[i + 1]
        attrs = _edge_best_data(G, u, v)
        name = _edge_name(attrs)
        dist = _edge_length_m(attrs, lat1, lon1, lat2, lon2)
        brg = _bearing_deg(lat1, lon1, lat2, lon2)
        segs.append({"u": u, "v": v, "name": name, "dist": dist, "brg": brg})

    # Merge consecutive segments if same street name and direction similar
    merged = []
    cur = {"name": segs[0]["name"], "dist": segs[0]["dist"], "brg": segs[0]["brg"]}
    for s in segs[1:]:
        same_name = (s["name"] == cur["name"])
        small_turn = abs(_delta_bearing(cur["brg"], s["brg"])) < 20
        if same_name and small_turn:
            cur["dist"] += s["dist"]
            cur["brg"] = s["brg"]
        else:
            merged.append(cur)
            cur = {"name": s["name"], "dist": s["dist"], "brg": s["brg"]}
    merged.append(cur)

    # Create turn-by-turn instructions
    steps = []
    steps.append({"step": 1, "instruction": f"Bắt đầu tại: {origin_label}", "distance_m": 0})

    def fmt_name(nm: str) -> str:
        return nm if nm else "đường nội bộ"

    # first move
    if merged:
        steps.append({"step": 2, "instruction": f"Đi theo {fmt_name(merged[0]['name'])}", "distance_m": merged[0]["dist"]})

    step_no = 3
    for i in range(1, len(merged)):
        prev = merged[i - 1]
        curm = merged[i]
        d = _delta_bearing(prev["brg"], curm["brg"])

        if abs(d) < 15:
            turn = "Đi thẳng"
        elif abs(d) < 45:
            turn = "Rẽ nhẹ phải" if d > 0 else "Rẽ nhẹ trái"
        elif abs(d) < 135:
            turn = "Rẽ phải" if d > 0 else "Rẽ trái"
        else:
            turn = "Quay đầu"

        steps.append(
            {
                "step": step_no,
                "instruction": f"{turn} vào {fmt_name(curm['name'])}",
                "distance_m": curm["dist"],
            }
        )
        step_no += 1

    steps.append({"step": step_no, "instruction": f"Đến nơi: {dest_label}", "distance_m": 0})
    return steps


# -------------------- UI --------------------

st.set_page_config(page_title="HUSTGo", page_icon="🧭", layout="wide")

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
      .badge { display:inline-block; padding:0.22rem 0.6rem; border-radius:999px; background:#eef2ff; border:1px solid #e5e7eb; }
      .card { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 16px; padding: 16px; }
      .stButton>button { border-radius: 12px; }
    </style>
    """,
    unsafe_allow_html=True,
)

commons = pick_common_locations()

with st.sidebar:
    mode = st.selectbox("Phương tiện", ["Đi bộ", "Xe đạp", "Xe máy"], index=0)
    show_markers = st.checkbox("Marker", value=True)
    force_download = st.checkbox("Tải lại dữ liệu", value=False)
    load_btn = st.button("Nạp dữ liệu", use_container_width=True)

if load_btn:
    with st.spinner("Đang nạp dữ liệu..."):
        saved, adj, nodes, edges, G = load_graph(force_download=force_download)
else:
    try:
        saved, adj, nodes, edges, G = load_graph(force_download=False)
    except Exception:
        st.stop()

colA, colB = st.columns([0.36, 0.64], gap="large")

with colA:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Chọn điểm")

    tab1, tab2 = st.tabs(["Gợi ý", "Nhập"])
    with tab1:
        names = list(commons.keys())
        start_name = st.selectbox("Xuất phát", names, index=0 if names else 0)
        goal_name = st.selectbox("Đích", names, index=min(1, len(names) - 1) if len(names) > 1 else 0)
        start_text = start_name
        goal_text = goal_name

    with tab2:
        start_text = st.text_input("Xuất phát", value="")
        goal_text = st.text_input("Đích", value="")

    run = st.button("Tìm đường", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with colB:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Kết quả")

    if run:
        try:
            start_coord = resolve_location(start_text, commons)
            goal_coord = resolve_location(goal_text, commons)
        except Exception:
            st.stop()

        start_node = nearest_node(nodes, start_coord[0], start_coord[1])
        goal_node = nearest_node(nodes, goal_coord[0], goal_coord[1])

        with st.spinner("Đang tìm đường..."):
            path_nodes, cost_m = astar(adj, nodes, start_node, goal_node)

        if not path_nodes:
            st.stop()

        route_coords = [(nodes[nid].lat, nodes[nid].lon) for nid in path_nodes]
        minutes = estimate_time(cost_m, mode)

        st.markdown(
            f"""
            <div style="display:flex; gap: 12px; flex-wrap:wrap; margin-bottom: 10px;">
              <span class="badge">📏 {cost_m:.0f} m</span>
              <span class="badge">⏱️ {minutes:.1f} phút</span>
              <span class="badge">🧩 {len(path_nodes)} nút</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_map, tab_dir = st.tabs(["Bản đồ", "Chỉ đường"])

        with tab_map:
            center = ((start_coord[0] + goal_coord[0]) / 2, (start_coord[1] + goal_coord[1]) / 2)
            m = build_map(center, start_coord, goal_coord, route_coords, show_markers=show_markers)
            render_folium(m, height=650)

        with tab_dir:
            steps = build_directions(
                path_nodes=path_nodes,
                nodes=nodes,
                G=G,
                origin_label=start_text.strip() or "Xuất phát",
                dest_label=goal_text.strip() or "Đích",
            )
            if not steps:
                st.write("Không có dữ liệu chỉ đường.")
            else:
                # Show as a clean table-like list
                for s in steps:
                    dist = s["distance_m"]
                    tail = "" if dist <= 0 else f" — {dist:.0f} m"
                    st.write(f"**{s['step']}.** {s['instruction']}{tail}")

    else:
        center = (21.0042, 105.8458)
        m = folium.Map(location=center, zoom_start=16, control_scale=True, tiles="OpenStreetMap")
        render_folium(m, height=650)

    st.markdown("</div>", unsafe_allow_html=True)
