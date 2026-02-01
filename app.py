# app_streamlit.py
# Giao diện Streamlit cho project tìm đường (A*)
# Chạy: streamlit run app_streamlit.py

import os
import pickle
import re
from typing import Dict, Tuple, Optional, List

import streamlit as st
import folium
from streamlit.components.v1 import html as st_html

from AStar import astar, nearest_node_by_coord
from calcDist import haversine_m
from load_map_bachkhoa import build_and_save_graph

# Geocoding (tuỳ chọn)
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
    lat = float(m.group(1))
    lon = float(m.group(2))
    return (lat, lon)

def normalize_key(s: str) -> str:
    return (s or "").strip().lower()

def pick_common_locations() -> Dict[str, Tuple[float, float]]:
    merged = {}
    for d in (COMMON_LOCATIONS_CFG, COMMON_LOCATIONS_GEO):
        for k, v in (d or {}).items():
            merged[str(k)] = (float(v[0]), float(v[1]))
    if not merged:
        merged = {
            "Cổng chính (gợi ý)": (21.00370, 105.84540),
            "Thư viện (gợi ý)": (21.00378, 105.84548),
        }
    return dict(sorted(merged.items(), key=lambda x: x[0].lower()))

def format_coord(lat: float, lon: float) -> str:
    return f"{lat:.6f}, {lon:.6f}"

# ước lượng thời gian theo từng loại phương tiện
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
        raise ValueError("Bạn chưa nhập địa điểm.")

    coord = parse_latlon(t)
    if coord:
        return coord

    # match key
    key = normalize_key(t)
    for name, c in commons.items():
        if normalize_key(name) == key:
            return c

    # match substring
    for name, c in commons.items():
        if key and key in normalize_key(name):
            return c

    if GEOCODING_AVAILABLE:
        return get_location_with_fallback(t)

    raise ValueError(
        "Không tìm thấy địa điểm. Hãy chọn trong danh sách gợi ý hoặc nhập tọa độ dạng 'lat, lon'. "
        "Nếu muốn nhập tên bất kỳ, hãy cài thêm geocoding/osmnx theo hướng dẫn."
    )

def nearest_node(nodes, lat: float, lon: float) -> int:
    # Dùng nearest_node_by_coord (O(N)) — đủ nhanh cho phạm vi nhỏ
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
        folium.Marker(location=start, tooltip="Điểm xuất phát", icon=folium.Icon(color="green")).add_to(m)
        folium.Marker(location=goal, tooltip="Điểm đến", icon=folium.Icon(color="red")).add_to(m)

    if route_coords:
        folium.PolyLine(route_coords, weight=6, opacity=0.9).add_to(m)

        lats = [p[0] for p in route_coords] + [start[0], goal[0]]
        lons = [p[1] for p in route_coords] + [start[1], goal[1]]
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])
    return m

def render_folium(m: folium.Map, height: int = 620):
    st_html(m.get_root().render(), height=height)

# app UI 

st.set_page_config(
    page_title="HUSTGo",
    page_icon="🏨",
    layout="wide",
)

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
      .small-muted { color: #6b7280; font-size: 0.9rem; }
      .badge { display:inline-block; padding:0.2rem 0.55rem; border-radius:999px; background:#eef2ff; }
      .card { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 16px; padding: 16px; }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🏨 HUSTGo")
st.write("Tìm đường đi trong Đại học Bách Khoa Hà Nội")

commons = pick_common_locations()

with st.sidebar:
    st.header("⚙️ Setting")
    mode = st.selectbox("Phương tiện", ["Đi bộ", "Xe đạp", "Xe máy"], index=0)
    show_markers = st.checkbox("Hiển thị marker", value=True)
    st.divider()

    st.subheader("Dữ liệu bản đồ")
    force_download = st.checkbox("Tải lại từ OSM (chậm)", value=False, help="Bật nếu bạn muốn cập nhật dữ liệu đường.")
    load_btn = st.button("Download dữ liệu", use_container_width=True)

    st.markdown(
        """
        <div class="small-muted">
        Nếu bị lỗi thiếu thư viện, bạn cần cài:
        <code>pip install streamlit folium osmnx networkx shapely geopandas pyproj requests</code>
        </div>
        """,
        unsafe_allow_html=True
    )

if load_btn:
    with st.spinner("Đang tải dữ liệu đồ thị..."):
        saved, adj, nodes, edges, G = load_graph(force_download=force_download)
    st.success("Đã tải xong dữ liệu!")
else:
    try:
        saved, adj, nodes, edges, G = load_graph(force_download=False)
    except Exception as e:
        st.error("Chưa thể nạp dữ liệu đồ thị. Hãy bấm 'Tải / Nạp dữ liệu' ở sidebar.")
        st.exception(e)
        st.stop()

colA, colB = st.columns([0.38, 0.62], gap="large")

with colA:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📍 Chọn điểm")
    tab1, tab2 = st.tabs(["Gợi ý nhanh", "Nhập tự do"])

    with tab1:
        names = list(commons.keys())
        start_name = st.selectbox("Điểm xuất phát", names, index=0)
        goal_name = st.selectbox("Điểm đến", names, index=min(1, len(names)-1))
        start_text = start_name
        goal_text = goal_name

    with tab2:
        st.write("Nhập *tên* hoặc *tọa độ* dạng `lat, lon`.")
        start_text = st.text_input("Điểm xuất phát", value="Thư viện Tạ Quang Bửu")
        goal_text = st.text_input("Điểm đến", value="Cổng Đại Cồ Việt")

    st.divider()
    st.subheader("🚦 Tác vụ")
    run = st.button("🔎 Tìm đường", type="primary", use_container_width=True)

    st.markdown(
        """
        <div class="small-muted">
        Mẹo: Bạn có thể nhập tọa độ để chính xác hơn, ví dụ: <code>21.003700, 105.845400</code>.
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

with colB:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Kết quả tìm đường")

    if run:
        try:
            start_coord = resolve_location(start_text, commons)
            goal_coord = resolve_location(goal_text, commons)
        except Exception as e:
            st.error(str(e))
            st.stop()

        # Find nearest nodes
        start_node = nearest_node(nodes, start_coord[0], start_coord[1])
        goal_node = nearest_node(nodes, goal_coord[0], goal_coord[1])

        # Run A*
        with st.spinner("Đang chạy A* để tìm đường..."):
            path_nodes, cost_m = astar(adj, nodes, start_node, goal_node)

        if not path_nodes:
            st.error("Không tìm thấy đường đi phù hợp giữa hai điểm.")
            st.stop()

        # Build polyline coordinates
        route_coords = [(nodes[nid].lat, nodes[nid].lon) for nid in path_nodes]

        # Summary
        minutes = estimate_time(cost_m, mode)
        st.markdown(
            f"""
            <div style="display:flex; gap: 12px; flex-wrap:wrap; margin-bottom: 8px;">
              <span class="badge">📏 {cost_m:.0f} m</span>
              <span class="badge">⏱️ ~{minutes:.1f} phút ({mode})</span>
              <span class="badge">🧩 {len(path_nodes)} nút</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Map
        center = ((start_coord[0] + goal_coord[0]) / 2, (start_coord[1] + goal_coord[1]) / 2)
        m = build_map(center, start_coord, goal_coord, route_coords, show_markers=show_markers)
        render_folium(m, height=650)

        # Show details (optional)
        with st.expander("📌 Xem chi tiết tọa độ tuyến đường"):
            st.write("Điểm xuất phát:", format_coord(*start_coord))
            st.write("Điểm đến:", format_coord(*goal_coord))
            st.code("\n".join([format_coord(lat, lon) for lat, lon in route_coords[:200]]))
            if len(route_coords) > 200:
                st.caption("Đã hiển thị 200 điểm đầu tiên để tránh quá dài.")
    else:
        # Default map view (center campus)
        center = (21.0042, 105.8458)
        m = folium.Map(location=center, zoom_start=16, control_scale=True, tiles="OpenStreetMap")
        folium.CircleMarker(center, radius=6, tooltip="Bách Khoa (gợi ý)", fill=True).add_to(m)
        render_folium(m, height=650)

    st.markdown("</div>", unsafe_allow_html=True)

st.caption("© Demo UI Streamlit — HUSTGo Project")
