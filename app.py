import streamlit as st
import pandas as pd
import json
import math
import folium
from streamlit_folium import st_folium
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

load_dotenv()

st.set_page_config(page_title="India AQI Dashboard", layout="wide", page_icon="🌿")

# --- SESSION STATE INIT ---
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'landing'
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'view' not in st.session_state:
    st.session_state.view = 'dashboard'
if 'selected_city' not in st.session_state:
    st.session_state.selected_city = None
if 'page' not in st.session_state:
    st.session_state.page = 1
if 'search_keyword' not in st.session_state:
    st.session_state.search_keyword = ""
if 'selected_states' not in st.session_state:
    st.session_state.selected_states = []
if 'sort_order' not in st.session_state:
    st.session_state.sort_order = "Highest First (Descending)"
if 'email_draft' not in st.session_state:
    st.session_state.email_draft = None

# --- PERSIST LOGIN ACROSS PAGE REFRESH ---
# We keep a "remember me" token in the URL (?auth_token=...). On every
# rerun: if we're not logged in but a valid token is present, restore the
# session from the DB. If we ARE logged in but no token is in the URL yet
# (e.g. right after a fresh login), mint one and stash it there.
from db import get_user_by_token, create_session, delete_session, log_generated_email

if not st.session_state.authenticated:
    _auth_token = st.query_params.get("auth_token")
    if _auth_token:
        _restored_user = get_user_by_token(_auth_token)
        if _restored_user:
            st.session_state.authenticated = True
            st.session_state.user = _restored_user
            if st.session_state.current_page in ('landing', 'auth'):
                st.session_state.current_page = 'dashboard'
        else:
            # Stale/expired token lingering in the URL — clean it up
            del st.query_params["auth_token"]
elif "auth_token" not in st.query_params:
    st.query_params["auth_token"] = create_session(st.session_state.user['id'])

# --- GLOBAL UI INJECTIONS ---
# Hide Streamlit's default sidebar navigation (page links) everywhere
st.markdown("""
    <style>
    [data-testid='stSidebarNav'] {display: none;}

    /* Streamlit reserves a large top gap in the sidebar for the collapse
       control; pull the actual content up so it doesn't look like empty
       space sitting above the first widget. */
    section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {
        padding-top: 1.25rem;
    }

    /* Tighten spacing inside the account card block specifically, without
       affecting gaps elsewhere in the sidebar. */
    .st-key-account_block [data-testid="stVerticalBlock"] {
        gap: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

if st.session_state.current_page in ['landing', 'auth', 'city_detail'] or st.session_state.view == 'city_detail':
    st.markdown("""
        <style>
        section[data-testid="stSidebar"] {
            display: none !important;
            width: 0 !important;
            min-width: 0 !important;
            visibility: hidden !important;
        }
        div[data-testid="stSidebarCollapsedControl"] {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

# Global Header
st.markdown("""
    <style>
    .st-key-global_header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        width: 100%;
        z-index: 999999;
        background: linear-gradient(135deg, rgba(34, 193, 195, 0.35), rgba(80, 90, 120, 0.35));
        backdrop-filter: blur(20px);
        border-bottom: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 0;
        padding: 10px 40px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25);
    }
    .st-key-global_header [data-testid="stHorizontalBlock"] {
        align-items: center;
    }
    .st-key-global_header [data-testid="stButton"] button {
        background: rgba(255, 255, 255, 0.10);
        border: 1px solid rgba(255, 255, 255, 0.3);
        color: #ffffff;
        border-radius: 20px;
        font-weight: 600;
        white-space: nowrap;
        transition: all 0.3s ease;
    }
    .st-key-global_header [data-testid="stButton"] button:hover {
        background: rgba(255, 255, 255, 0.3);
        border-color: #22c1c3;
        color: #22c1c3;
    }
    /* Push page content down so the fixed header doesn't cover it */
    div[data-testid="stAppViewBlockContainer"] {
        padding-top: 5rem;
    }
    </style>
""", unsafe_allow_html=True)

with st.container(key="global_header"):
    brand_col, nav_col = st.columns([5, 1])
    with brand_col:
        st.markdown(
            "<div style='color:#ffffff;font-weight:700;font-size:1.2rem;"
            "line-height:2.4rem;'>🌿 India AQI Dashboard</div>",
            unsafe_allow_html=True,
        )
    with nav_col:
        if st.session_state.current_page == 'auth':
            if st.button("🏠 Home", use_container_width=True):
                st.session_state.current_page = 'landing'
                st.rerun()
        elif st.session_state.current_page == 'landing':
            if st.session_state.get('authenticated'):
                if st.button("🚀 Dashboard", use_container_width=True):
                    st.session_state.current_page = 'dashboard'
                    st.rerun()
            else:
                if st.button("🔐 Login / Sign Up", use_container_width=True):
                    st.session_state.current_page = 'auth'
                    st.rerun()
        else:
            if st.button("🏠 Home", use_container_width=True):
                st.session_state.current_page = 'landing'
                st.rerun()

# --- DATA LOADING ---
import os
import time as _time
import requests as _requests
import threading
from datetime import datetime, timedelta

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, 'data')
AQI_DATA_PATH = os.path.join(DATA_DIR, 'india_aqi_data.json')

# How old (in minutes) before we consider AQI data stale
STALE_THRESHOLD_MINUTES = 60

# ── AQI Calculation Helpers (India NAQI) ──────────────────────────────
def _calc_sub_index(c_p, bp_lo, bp_hi, i_lo, i_hi):
    return round(((i_hi - i_lo) / (bp_hi - bp_lo)) * (c_p - bp_lo) + i_lo)

def _get_pm25_sub_index(c_p):
    if 0 <= c_p <= 30:    return _calc_sub_index(c_p, 0, 30, 0, 50)
    elif c_p <= 60:       return _calc_sub_index(c_p, 31, 60, 51, 100)
    elif c_p <= 90:       return _calc_sub_index(c_p, 61, 90, 101, 200)
    elif c_p <= 120:      return _calc_sub_index(c_p, 91, 120, 201, 300)
    elif c_p <= 250:      return _calc_sub_index(c_p, 121, 250, 301, 400)
    elif c_p > 250:       return _calc_sub_index(c_p, 250, 1000, 401, 500)
    return None

def _get_aqi_category_label(aqi):
    if aqi is None: return "Unknown"
    if aqi <= 50:   return "Good"
    elif aqi <= 100: return "Satisfactory"
    elif aqi <= 200: return "Moderately Polluted"
    elif aqi <= 300: return "Poor"
    elif aqi <= 400: return "Very Poor"
    elif aqi > 400:  return "Severe"
    return "Unknown"

# ── Live AQI Fetch Functions ──────────────────────────────────────────
API_KEY = "93d3805b2b193781a05a91c0a8184891ff35d0bcce4b710a6b6df6d4a1b15c0c"
API_HEADERS = {"X-Api-Key": API_KEY}

def _fetch_india_location_ids(progress_callback=None):
    """Fetch all India location IDs from OpenAQ (paginated)."""
    url = "https://api.openaq.org/v3/locations"
    ids = []
    page = 1
    while True:
        params = {"countries_id": 9, "limit": 1000, "page": page}
        try:
            resp = _requests.get(url, params=params, headers=API_HEADERS, timeout=30)
        except _requests.exceptions.RequestException:
            break
        if resp.status_code == 429:
            _time.sleep(10)
            continue
        if resp.status_code != 200:
            break
        results = resp.json().get('results', [])
        if not results:
            break
        for loc in results:
            ids.append(loc['id'])
        if progress_callback:
            progress_callback(f"Found {len(ids)} stations...")
        page += 1
        _time.sleep(0.5)
    return ids

def _fetch_pm25_data(location_ids, progress_callback=None):
    """Fetch latest PM2.5 readings and match to India locations."""
    url = "https://api.openaq.org/v3/parameters/2/latest"
    id_set = set(location_ids)
    results_dict = {}
    page = 1
    while True:
        params = {"limit": 1000, "page": page}
        try:
            resp = _requests.get(url, headers=API_HEADERS, params=params, timeout=30)
        except _requests.exceptions.RequestException:
            break
        if resp.status_code == 429:
            _time.sleep(10)
            continue
        if resp.status_code != 200:
            break
        results = resp.json().get('results', [])
        if not results:
            break
        for item in results:
            loc_id = item['locationsId']
            if loc_id in id_set:
                conc = item['value']
                aqi = _get_pm25_sub_index(conc)
                coords = item.get('coordinates') or {}
                results_dict[loc_id] = {
                    'city': "Pending", 'state': "Pending", 'area': "Pending",
                    'longitude': coords.get('longitude'),
                    'latitude': coords.get('latitude'),
                    'pm_value_used': conc,
                    'aqi': aqi,
                    'category': _get_aqi_category_label(aqi),
                }
        if progress_callback:
            progress_callback(f"Page {page} scanned, {len(results_dict)} India readings found...")
        page += 1
        _time.sleep(0.5)
    return results_dict

def _reverse_geocode_results(results_dict, progress_callback=None):
    """Resolve lat/lon to city/state/area using offline reverse geocoder."""
    try:
        import reverse_geocoder as rg
    except ImportError:
        return results_dict

    loc_ids = list(results_dict.keys())
    coords = []
    valid_indices = []
    for i, lid in enumerate(loc_ids):
        lat = results_dict[lid]['latitude']
        lon = results_dict[lid]['longitude']
        if lat is not None and lon is not None:
            coords.append((lat, lon))
            valid_indices.append(i)

    if coords:
        if progress_callback:
            progress_callback(f"Reverse geocoding {len(coords)} locations...")
        rg_results = rg.search(coords)
        for idx, rg_res in enumerate(rg_results):
            lid = loc_ids[valid_indices[idx]]
            results_dict[lid]['city'] = rg_res.get('name', 'Unknown')
            results_dict[lid]['state'] = rg_res.get('admin1', 'Unknown')
            results_dict[lid]['area'] = rg_res.get('admin2', 'Unknown')

    return results_dict

def refresh_aqi_data(progress_container=None):
    """Full AQI data refresh pipeline. Returns True on success."""
    def update(msg):
        if progress_container:
            progress_container.update(label=msg)

    try:
        update("Step 1/3: Fetching India station list...")
        ids = _fetch_india_location_ids(progress_callback=update)
        if not ids:
            return False

        update(f"Step 2/3: Fetching PM2.5 data for {len(ids)} stations...")
        data = _fetch_pm25_data(ids, progress_callback=update)
        if not data:
            return False

        update("Step 3/3: Resolving location names...")
        data = _reverse_geocode_results(data, progress_callback=update)

        # Save with metadata
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(AQI_DATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        update(f"Done! Updated {len(data)} stations.")
        return True
    except Exception as e:
        if progress_container:
            progress_container.update(label=f"Error: {e}", state="error")
        return False

# ── Data Freshness Check ──────────────────────────────────────────────
def get_data_age_minutes():
    """Returns the age of india_aqi_data.json in minutes, or None if file doesn't exist."""
    try:
        mtime = os.path.getmtime(AQI_DATA_PATH)
        age_seconds = _time.time() - mtime
        return age_seconds / 60
    except FileNotFoundError:
        return None

def get_data_timestamp():
    """Returns a human-readable last-updated timestamp."""
    try:
        mtime = os.path.getmtime(AQI_DATA_PATH)
        return datetime.fromtimestamp(mtime, tz=timezone(timedelta(hours=5, minutes=30))).strftime('%d %b %Y, %I:%M %p IST')
    except FileNotFoundError:
        return None

# ── Cached Data Loaders (with TTL to pick up refreshed files) ─────────
@st.cache_data(ttl=300)  # Re-read from disk every 5 minutes
def load_data():
    with open(AQI_DATA_PATH, 'r') as f:
        data = json.load(f)
    records = []
    for loc_id, info in data.items():
        if info.get('aqi') is not None:
            records.append({
                'City': info.get('city', 'Unknown'),
                'State': info.get('state', 'Unknown'),
                'Area': info.get('area', 'Unknown'),
                'AQI': info.get('aqi'),
                'Category': info.get('category'),
                'PM2.5 (µg/m³)': info.get('pm_value_used'),
                'Latitude': info.get('latitude'),
                'Longitude': info.get('longitude')
            })
    return pd.DataFrame(records)

@st.cache_data(ttl=300)
def load_raw_data():
    with open(AQI_DATA_PATH, 'r') as f:
        return json.load(f)

@st.cache_data
def load_factory_data():
    try:
        with open(os.path.join(DATA_DIR, 'india_factories_data.json'), 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

@st.cache_data
def load_city_emissions():
    try:
        with open(os.path.join(DATA_DIR, 'city_emissions_data.json'), 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

@st.cache_data
def load_gem_data():
    try:
        with open(os.path.join(DATA_DIR, 'india_gem_data.json'), 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# ── Handle Auto-Refresh on Startup ────────────────────────────────────
data_age = get_data_age_minutes()

# If no data exists at all, we MUST fetch before proceeding
if data_age is None:
    st.warning("No AQI data found. Fetching live data from OpenAQ...")
    with st.status("Fetching AQI data...", expanded=True) as status:
        success = refresh_aqi_data(progress_container=status)
        if success:
            status.update(label="AQI data fetched successfully!", state="complete")
        else:
            st.error("Failed to fetch AQI data. Please check your internet connection.")
            st.stop()

# Load data
try:
    df = load_data()
    raw_data = load_raw_data()
    factory_data = load_factory_data()
    gem_data = load_gem_data()
    city_emissions = load_city_emissions()
except FileNotFoundError:
    st.error("Could not find data files. Please ensure the data gathering scripts have been run.")
    st.stop()

# ============================================================
#                    HELPER FUNCTIONS
# ============================================================

def get_category_colors(category):
    """Returns (background_color, text_color) for a given AQI category."""
    if category == 'Good': return '#00b050', '#ffffff'
    elif category == 'Satisfactory': return '#92d050', '#000000'
    elif category == 'Moderately Polluted': return '#ffff00', '#000000'
    elif category == 'Poor': return '#ff9900', '#000000'
    elif category == 'Very Poor': return '#ff0000', '#ffffff'
    elif category == 'Severe': return '#c00000', '#ffffff'
    return '#e2e3e5', '#000000'

def get_aqi_color(aqi):
    """Returns the hex color for an AQI value."""
    if aqi is None: return '#cccccc'
    if 0 <= aqi <= 50: return '#00b050'
    elif 51 <= aqi <= 100: return '#92d050'
    elif 101 <= aqi <= 200: return '#ffff00'
    elif 201 <= aqi <= 300: return '#ff9900'
    elif 301 <= aqi <= 400: return '#ff0000'
    elif aqi > 400: return '#c00000'
    return '#cccccc'

def get_aqi_category(aqi):
    """Returns the AQI category string for a given AQI value."""
    if aqi is None: return "Unknown"
    if 0 <= aqi <= 50: return "Good"
    elif 51 <= aqi <= 100: return "Satisfactory"
    elif 101 <= aqi <= 200: return "Moderately Polluted"
    elif 201 <= aqi <= 300: return "Poor"
    elif 301 <= aqi <= 400: return "Very Poor"
    elif aqi > 400: return "Severe"
    return "Unknown"

def find_stations_in_bbox(raw_data, min_lat, max_lat, min_lon, max_lon):
    """Find all stations from the JSON data that fall within the bounding box."""
    stations = []
    for loc_id, info in raw_data.items():
        lat = info.get('latitude')
        lon = info.get('longitude')
        if lat is not None and lon is not None:
            if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                stations.append({
                    'id': loc_id,
                    'name': info.get('city', 'Unknown'),
                    'area': info.get('area', 'Unknown'),
                    'state': info.get('state', 'Unknown'),
                    'lat': lat,
                    'lon': lon,
                    'aqi': info.get('aqi'),
                    'pm25': info.get('pm_value_used'),
                    'category': info.get('category', 'Unknown')
                })
    return stations

def find_factories_in_bbox(factory_data, gem_data, min_lat, max_lat, min_lon, max_lon):
    """Find all factories/industries from both Climate TRACE and GEM that fall within the bounding box."""
    factories = []
    # Climate TRACE facilities (tag source if not already set)
    for f in factory_data:
        lat = f.get('lat')
        lon = f.get('lon')
        if lat is not None and lon is not None:
            if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                if 'data_source' not in f:
                    f['data_source'] = 'climate_trace'
                factories.append(f)
    # GEM facilities
    for f in gem_data:
        lat = f.get('lat')
        lon = f.get('lon')
        if lat is not None and lon is not None:
            if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                factories.append(f)
    return factories

def match_city_to_emissions(city_name, city_emissions):
    """Try to match a city name from the dashboard to the area-level emissions data."""
    normalized = city_name.lower().strip()
    # 1. Exact match
    if normalized in city_emissions:
        return city_emissions[normalized]
    # 2. Substring match (city name inside key or key inside city name)
    for key, data in city_emissions.items():
        if normalized in key or key in normalized:
            return data
    # 3. First-word match (e.g. "New Delhi" matches "delhi")
    first_word = normalized.split()[0] if normalized.split() else ''
    for key, data in city_emissions.items():
        if first_word and (first_word in key or key in first_word):
            return data
    return None

def build_grid_cells(min_lat, max_lat, min_lon, max_lon, grid_size_km, center_lat):
    """Build a list of grid cell dicts covering the bounding box with the given cell size."""
    km_per_deg_lat = 111.32
    km_per_deg_lon = 111.32 * math.cos(math.radians(center_lat))

    grid_lat_step = grid_size_km / km_per_deg_lat
    grid_lon_step = grid_size_km / km_per_deg_lon

    cells = []
    current_lat = min_lat
    while current_lat < max_lat:
        current_lon = min_lon
        while current_lon < max_lon:
            cells.append({
                'min_lat': current_lat,
                'max_lat': min(current_lat + grid_lat_step, max_lat),
                'min_lon': current_lon,
                'max_lon': min(current_lon + grid_lon_step, max_lon),
                'stations': [],
                'avg_aqi': None,
                'avg_pm25': None
            })
            current_lon += grid_lon_step
        current_lat += grid_lat_step
    return cells

def assign_stations_to_grid(cells, stations):
    """Assign each station to the grid cell it falls within and compute cell averages."""
    for station in stations:
        for cell in cells:
            if (cell['min_lat'] <= station['lat'] < cell['max_lat'] and
                    cell['min_lon'] <= station['lon'] < cell['max_lon']):
                cell['stations'].append(station)
                break

    for cell in cells:
        if cell['stations']:
            aqis = [s['aqi'] for s in cell['stations'] if s['aqi'] is not None]
            pm25s = [s['pm25'] for s in cell['stations'] if s['pm25'] is not None]
            if aqis:
                cell['avg_aqi'] = sum(aqis) / len(aqis)
            if pm25s:
                cell['avg_pm25'] = sum(pm25s) / len(pm25s)
    return cells

# ============================================================
#                    CITY MAP DETAIL VIEW
# ============================================================

def render_city_detail():
    city_data = st.session_state.selected_city
    lat = city_data['Latitude']
    lon = city_data['Longitude']

    # --- Back button ---
    if st.button("⬅️ Back to Dashboard"):
        st.session_state.view = 'dashboard'
        st.session_state.selected_city = None
        st.rerun()

    # --- Header ---
    bg_color, text_color = get_category_colors(city_data['Category'])
    st.markdown(f"""
    <div style="background-color:{bg_color};color:{text_color};padding:20px 30px;border-radius:12px;margin-bottom:20px;">
        <h1 style="margin:0;color:{text_color};">📍 {city_data['City']}</h1>
        <p style="margin:5px 0 0 0;font-size:1.1rem;opacity:0.9;">{city_data['Area']} · {city_data['State']} &nbsp;|&nbsp; AQI: <b>{city_data['AQI']}</b> ({city_data['Category']})</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Calculate bounding box (25 km in each direction → 50 km × 50 km) ---
    extend_km = 25
    km_per_deg_lat = 111.32
    km_per_deg_lon = 111.32 * math.cos(math.radians(lat))

    delta_lat = extend_km / km_per_deg_lat
    delta_lon = extend_km / km_per_deg_lon

    min_lat = lat - delta_lat
    max_lat = lat + delta_lat
    min_lon = lon - delta_lon
    max_lon = lon + delta_lon

    # --- Find stations within bbox ---
    stations = find_stations_in_bbox(raw_data, min_lat, max_lat, min_lon, max_lon)

    # --- Find factories/industries within bbox ---
    factories = find_factories_in_bbox(factory_data, gem_data, min_lat, max_lat, min_lon, max_lon)

    # --- Build 5 km grid & assign stations ---
    grid_cells = build_grid_cells(min_lat, max_lat, min_lon, max_lon, 5, lat)
    grid_cells = assign_stations_to_grid(grid_cells, stations)

    cells_with_data_list = [c for c in grid_cells if c['avg_aqi'] is not None]
    cells_with_data = len(cells_with_data_list)

    # Compute actual coverage from cells that have data
    if cells_with_data_list:
        active_min_lat = min(c['min_lat'] for c in cells_with_data_list)
        active_max_lat = max(c['max_lat'] for c in cells_with_data_list)
        active_min_lon = min(c['min_lon'] for c in cells_with_data_list)
        active_max_lon = max(c['max_lon'] for c in cells_with_data_list)
        active_height = (active_max_lat - active_min_lat) * km_per_deg_lat
        active_width = (active_max_lon - active_min_lon) * km_per_deg_lon
        coverage_str = f"{active_width:.0f} km × {active_height:.0f} km"
    else:
        coverage_str = "No data"

    # --- Stats row ---
    stat1, stat2, stat3, stat4, stat5 = st.columns(5)
    with stat1:
        st.metric("📡 AQI Stations", len(stations))
    with stat2:
        st.metric("🏭 Factories/Industries", len(factories))
    with stat3:
        st.metric("🟩 Grid Cells with Data", f"{cells_with_data} / {len(grid_cells)}")
    with stat4:
        st.metric("📐 Grid Cell Size", "5 km × 5 km")
    with stat5:
        st.metric("📏 Active Coverage", coverage_str)

    # --- Build Folium map ---
    m = folium.Map(location=[lat, lon], zoom_start=11, tiles='OpenStreetMap')

    # Grid overlay
    for cell in grid_cells:
        bounds = [[cell['min_lat'], cell['min_lon']], [cell['max_lat'], cell['max_lon']]]

        if cell['avg_aqi'] is not None:
            color = get_aqi_color(cell['avg_aqi'])
            category = get_aqi_category(int(cell['avg_aqi']))
            station_names = ', '.join(set(s['name'] for s in cell['stations']))

            tooltip_html = (
                f"<b>Average AQI:</b> {cell['avg_aqi']:.0f}<br>"
                f"<b>Category:</b> {category}<br>"
                f"<b>Avg PM2.5:</b> {cell['avg_pm25']:.2f} µg/m³<br>"
                f"<b>Stations:</b> {len(cell['stations'])}<br>"
                f"<b>Names:</b> {station_names}"
            )

            folium.Rectangle(
                bounds=bounds,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.45,
                weight=2,
                tooltip=folium.Tooltip(tooltip_html),
            ).add_to(m)
        else:
            # Empty cell — faint dashed outline
            folium.Rectangle(
                bounds=bounds,
                color='#aaaaaa',
                fill=False,
                weight=0.5,
                dash_array='5 5',
                tooltip="No monitoring data available",
            ).add_to(m)

    # Station markers
    for station in stations:
        color = get_aqi_color(station['aqi'])
        popup_html = (
            f"<div style='min-width:180px'>"
            f"<b style='font-size:1.1rem'>{station['name']}</b><br>"
            f"<b>Area:</b> {station['area']}<br>"
            f"<b>State:</b> {station['state']}<br>"
            f"<hr style='margin:4px 0'>"
            f"<b>AQI:</b> {station['aqi']}<br>"
            f"<b>PM2.5:</b> {station['pm25']:.2f} µg/m³<br>"
            f"<b>Category:</b> {station['category']}<br>"
            f"<b>Lat:</b> {station['lat']:.4f}<br>"
            f"<b>Lon:</b> {station['lon']:.4f}"
            f"</div>"
        )

        folium.CircleMarker(
            location=[station['lat'], station['lon']],
            radius=8,
            color='#333333',
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            weight=2,
            tooltip=f"{station['name']} — AQI: {station['aqi']} ({station['category']})",
            popup=folium.Popup(popup_html, max_width=260),
        ).add_to(m)

    # City centre marker
    folium.Marker(
        location=[lat, lon],
        icon=folium.Icon(color='blue', icon='info-sign'),
        tooltip=f"Selected Location: {city_data['City']}",
    ).add_to(m)

    # --- Factory / Industry markers ---
    SECTOR_COLORS = {
        # Climate TRACE sectors
        'Manufacturing': 'red',
        'Power': 'orange',
        'Fossil Fuel Operations': 'darkred',
        'Mineral Extraction': 'purple',
        'Waste': 'darkgreen',
        # GEM sectors
        'Coal Mining': 'black',
        'Coal Power': 'darkred',
        'Solar Power': 'orange',
        'Oil & Gas Power': 'darkblue',
        'Bioenergy': 'green',
        'Coal Logistics': 'gray',
        'Oil & Gas Extraction': 'darkpurple',
        'Cement': 'cadetblue',
        'Iron Ore Mining': 'red',
        'Chemicals': 'pink',
    }
    SECTOR_ICONS = {
        # Climate TRACE sectors
        'Manufacturing': 'industry',
        'Power': 'bolt',
        'Fossil Fuel Operations': 'fire',
        'Mineral Extraction': 'diamond',
        'Waste': 'recycle',
        # GEM sectors
        'Coal Mining': 'cube',
        'Coal Power': 'bolt',
        'Solar Power': 'sun-o',
        'Oil & Gas Power': 'fire',
        'Bioenergy': 'leaf',
        'Coal Logistics': 'ship',
        'Oil & Gas Extraction': 'tint',
        'Cement': 'building',
        'Iron Ore Mining': 'diamond',
        'Chemicals': 'flask',
    }

    for fac in factories:
        fac_color = SECTOR_COLORS.get(fac['sector'], 'gray')
        fac_icon = SECTOR_ICONS.get(fac.get('sector', ''), fac.get('icon', 'industry'))

        emissions_str = f"{fac['emissions_tonnes']:,.2f} tonnes" if fac.get('emissions_tonnes') is not None else 'N/A'
        # Use capacity_display if available (GEM), otherwise format raw values
        capacity_str = fac.get('capacity_display', '')
        if not capacity_str or capacity_str == 'N/A':
            capacity_str = f"{fac['capacity']:,.2f} {fac.get('capacity_units', '')}" if fac.get('capacity') is not None else 'N/A'

        # Data source badge
        source = fac.get('data_source', 'climate_trace')
        source_badge = (
            "<span style='background:#2ecc71;color:white;padding:2px 6px;border-radius:4px;font-size:0.7rem;'>Climate TRACE</span>"
            if source == 'climate_trace' else
            "<span style='background:#3498db;color:white;padding:2px 6px;border-radius:4px;font-size:0.7rem;'>GEM</span>"
        )

        # Owner/Status info for GEM facilities
        owner_html = f"<b>Owner:</b> {fac['owner']}<br>" if fac.get('owner') else ''
        status_html = f"<b>Status:</b> {fac['status']}<br>" if fac.get('status') else ''
        year_html = f"<b>Start Year:</b> {fac['start_year']}<br>" if fac.get('start_year') else ''

        popup_html = (
            f"<div style='min-width:240px;font-family:sans-serif;'>"
            f"<b style='font-size:1.1rem;color:#333;'>{fac['name']}</b> {source_badge}<br>"
            f"<span style='color:#666;font-size:0.85rem;'>{fac.get('subsector', '')}</span><br>"
            f"<hr style='margin:5px 0;border-color:#ddd;'>"
            f"<b>Sector:</b> {fac['sector']}<br>"
            f"<b>Type:</b> {fac.get('type', 'N/A')}<br>"
            f"{status_html}"
            f"{owner_html}"
            f"<b>Emissions:</b> {emissions_str}<br>"
            f"<b>Capacity:</b> {capacity_str}<br>"
            f"{year_html}"
            f"<b>Lat:</b> {fac['lat']:.4f}<br>"
            f"<b>Lon:</b> {fac['lon']:.4f}"
            f"</div>"
        )

        folium.Marker(
            location=[fac['lat'], fac['lon']],
            icon=folium.Icon(color=fac_color, icon=fac_icon, prefix='fa'),
            tooltip=f"{fac['name']} ({fac['sector']})",
            popup=folium.Popup(popup_html, max_width=320),
        ).add_to(m)

    # Render
    st_folium(m, height=620, width="100%")

    # --- AQI Color Legend ---
    st.markdown("### 🎨 AQI Color Legend")
    legend_items = [
        ("Good (0-50)", "#00b050", "#ffffff"),
        ("Satisfactory (51-100)", "#92d050", "#000000"),
        ("Moderate (101-200)", "#ffff00", "#000000"),
        ("Poor (201-300)", "#ff9900", "#000000"),
        ("Very Poor (301-400)", "#ff0000", "#ffffff"),
        ("Severe (400+)", "#c00000", "#ffffff"),
    ]
    lcols = st.columns(len(legend_items))
    for i, (label, bg, fg) in enumerate(legend_items):
        with lcols[i]:
            st.markdown(
                f'<div style="background:{bg};color:{fg};padding:10px 6px;border-radius:8px;'
                f'text-align:center;font-size:0.8rem;font-weight:600;">{label}</div>',
                unsafe_allow_html=True,
            )

    # ==============================================================
    #  SECTION: EMISSIONS BREAKDOWN — "Why is this city's AQI bad?"
    # ==============================================================
    st.markdown("---")
    st.info("ℹ️ **Data Note:** While the AQI data shown above is real-time, the factory and sector emissions breakdown below relies on **historical baseline estimates** (annual/monthly averages from Climate TRACE and GEM). We overlay this historical data against current AQI spikes to identify probable industrial sources.")

    import altair as alt

    # Industrial emissions total from factories in bbox
    industry_total = sum(
        f.get('emissions_tonnes', 0) or 0 for f in factories
    )

    # Match city to area-level emissions
    matched_emissions = match_city_to_emissions(city_data['City'], city_emissions)

    transport_total = 0.0
    crop_fires_total = 0.0
    buildings_total = 0.0
    monthly_data_available = False

    if matched_emissions:
        transport_total = matched_emissions.get('transport', {}).get('total', 0)
        crop_fires_total = matched_emissions.get('crop_fires', {}).get('total', 0)
        buildings_total = matched_emissions.get('buildings', {}).get('total', 0)
        monthly_data_available = True

    # Build breakdown data
    breakdown_records = [
        {'Source': '🏭 Industry',       'PM2.5 (tonnes)': round(industry_total, 2)},
        {'Source': '🚗 Transport',      'PM2.5 (tonnes)': round(transport_total, 2)},
        {'Source': '🔥 Crop Fires',     'PM2.5 (tonnes)': round(crop_fires_total, 2)},
        {'Source': '🏠 Buildings',      'PM2.5 (tonnes)': round(buildings_total, 2)},
    ]
    breakdown_df = pd.DataFrame(breakdown_records)

    has_any_data = breakdown_df['PM2.5 (tonnes)'].sum() > 0

    if has_any_data:
        st.markdown("---")
        st.markdown("## 📊 What’s Causing the Air Pollution?")
        st.caption("A summary of PM2.5 emissions from four major sources in this area.")

        # Show proportion summary
        total_all = breakdown_df['PM2.5 (tonnes)'].sum()
        if total_all > 0:
            top_source = breakdown_df.loc[breakdown_df['PM2.5 (tonnes)'].idxmax()]
            pct = (top_source['PM2.5 (tonnes)'] / total_all) * 100
            st.info(f"⚠️ **{top_source['Source']}** is the largest contributor, "
                    f"accounting for **{pct:.1f}%** of all PM2.5 emissions in this area.")

    # ==============================================================
    #  SECTION: SEASONAL TREND — "When are emissions worst?"
    # ==============================================================
    if monthly_data_available and matched_emissions:
        st.markdown("---")
        st.markdown("## 📈 How Do Emissions Change Throughout the Year?")
        st.caption("This line chart shows monthly PM2.5 emissions for each source. "
                   "Look for seasonal spikes — e.g. crop fires in Oct–Nov or heating "
                   "fuel use in winter.")

        MONTH_NAMES = {
            1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
            7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
        }

        trend_rows = []
        sector_monthly = {
            '🚗 Transport': matched_emissions.get('transport', {}).get('monthly', {}),
            '🔥 Crop Fires': matched_emissions.get('crop_fires', {}).get('monthly', {}),
            '🏠 Buildings': matched_emissions.get('buildings', {}).get('monthly', {}),
        }
        for source_label, monthly_dict in sector_monthly.items():
            for month_key, val in monthly_dict.items():
                try:
                    month_num = int(month_key.split('-')[1])
                    trend_rows.append({
                        'Month': MONTH_NAMES.get(month_num, month_key),
                        'Month_Num': month_num,
                        'Emissions (tonnes)': round(val, 4),
                        'Source': source_label
                    })
                except (ValueError, IndexError):
                    pass

        if trend_rows:
            trend_df = pd.DataFrame(trend_rows)
            trend_df = trend_df.sort_values('Month_Num')

            trend_chart = alt.Chart(trend_df).mark_line(
                point=alt.OverlayMarkDef(size=50)
            ).encode(
                x=alt.X('Month:N', sort=list(MONTH_NAMES.values()),
                         axis=alt.Axis(labelAngle=0, labelFontSize=12)),
                y=alt.Y('Emissions (tonnes):Q',
                         axis=alt.Axis(labelFontSize=12, titleFontSize=13)),
                color=alt.Color('Source:N', scale=alt.Scale(
                    domain=['🚗 Transport', '🔥 Crop Fires', '🏠 Buildings'],
                    range=['#3498db', '#f39c12', '#2ecc71']
                )),
                tooltip=['Source', 'Month', 'Emissions (tonnes)']
            ).properties(height=350)
            st.altair_chart(trend_chart, width='stretch')

            # Find peak month
            if not trend_df.empty:
                monthly_totals = trend_df.groupby('Month_Num')['Emissions (tonnes)'].sum()
                peak_num = int(monthly_totals.idxmax())
                peak_name = MONTH_NAMES.get(peak_num, str(peak_num))
                st.info(f"📅 **{peak_name}** is the month with the highest combined PM2.5 "
                        f"emissions in this area.")
        else:
            st.info("Monthly trend data is not available for this city.")

    # ==============================================================
    #  SECTION: FACTORY LEADERBOARD — "Who are the biggest polluters?"
    # ==============================================================
    if factories:
        st.markdown("---")
        st.markdown("## 🏆 Biggest Industrial Polluters Nearby")
        st.caption("These are the top factories and industries in this area, ranked by "
                   "their reported emissions. Click on their markers on the map above "
                   "to see full details.")

        # Sort and take top 10 (excluding 0 emissions)
        sorted_facs = sorted(
            [f for f in factories if f.get('emissions_tonnes') and f['emissions_tonnes'] > 0],
            key=lambda x: x['emissions_tonnes'],
            reverse=True
        )[:10]

        if sorted_facs:
            leaderboard_rows = []
            for rank, fac in enumerate(sorted_facs, 1):
                medal = {1: '🥇', 2: '🥈', 3: '🥉'}.get(rank, f' {rank}.')
                cap_str = fac.get('capacity_display', '')
                if not cap_str or cap_str == 'N/A':
                    cap_str = f"{fac['capacity']:,.0f} {fac.get('capacity_units', '')}" if fac.get('capacity') else 'N/A'
                source_label = 'GEM' if fac.get('data_source') == 'gem' else 'Climate TRACE'
                leaderboard_rows.append({
                    'Rank': medal,
                    'Facility': fac['name'],
                    'Sector': fac['sector'],
                    'Type': fac.get('type', ''),
                    'Emissions (tonnes)': round(fac['emissions_tonnes'], 2),
                    'Capacity': cap_str,
                    'Source': source_label,
                })

            lb_df = pd.DataFrame(leaderboard_rows)
            st.dataframe(lb_df, width='stretch', hide_index=True)
        else:
            st.info("No factory emissions data available for ranking in this area.")

    # ==============================================================
    #  SECTION: DETAILED DATA TABLES
    # ==============================================================
    st.markdown("---")
    st.markdown("## 📋 Detailed Data")
    st.caption("Expand the sections below to see raw data for AQI monitoring stations "
               "and factories in this area.")

    if stations:
        with st.expander(f"📡 AQI Monitoring Stations ({len(stations)})", expanded=False):
            station_df = pd.DataFrame(stations).rename(columns={
                'name': 'City', 'area': 'Area', 'state': 'State',
                'lat': 'Latitude', 'lon': 'Longitude',
                'aqi': 'AQI', 'pm25': 'PM2.5 (µg/m³)', 'category': 'Category'
            })
            station_df = station_df[['City', 'Area', 'State', 'AQI', 'Category', 'PM2.5 (µg/m³)', 'Latitude', 'Longitude']]
            station_df = station_df.sort_values(by='AQI', ascending=False).reset_index(drop=True)
            st.dataframe(station_df, width='stretch', hide_index=True)

    if factories:
        with st.expander(f"🏭 Factories, Industries & Other Facilities ({len(factories)})", expanded=False):
            fac_df = pd.DataFrame(factories)
            # Add Source column
            fac_df['Source'] = fac_df['data_source'].apply(
                lambda x: 'GEM' if x == 'gem' else 'Climate TRACE'
            )
            fac_df = fac_df.rename(columns={
                'name': 'Facility Name', 'type': 'Type', 'sector': 'Sector',
                'subsector': 'Subsector', 'lat': 'Latitude', 'lon': 'Longitude',
                'gas': 'Gas', 'emissions_tonnes': 'Emissions (tonnes)',
                'capacity': 'Capacity', 'capacity_units': 'Capacity Units',
                'status': 'Status', 'owner': 'Owner',
            })
            display_cols = ['Facility Name', 'Sector', 'Subsector', 'Type', 'Status', 'Owner', 'Emissions (tonnes)', 'Capacity', 'Capacity Units', 'Source', 'Latitude', 'Longitude']
            display_cols = [c for c in display_cols if c in fac_df.columns]
            fac_df = fac_df[display_cols].sort_values(by='Emissions (tonnes)', ascending=False, na_position='last').reset_index(drop=True)
            st.dataframe(fac_df, width='stretch', hide_index=True)

    # ==============================================================
    #  SECTION: REPORT AQI TO AUTHORITIES
    # ==============================================================
    if st.session_state.get('authenticated'):
        st.markdown("---")
        st.markdown("## 📧 Report AQI to Authorities")
        st.caption("Generate an AI-powered complaint email with real data from this area "
                   "and send it to the responsible State Pollution Control Board.")

        from mail_service import find_authority_for_state, find_municipal_corp, generate_complaint_email

        state = city_data.get('State', '')
        authority = find_authority_for_state(state)
        municipal = find_municipal_corp(city_data.get('City', ''))

        if authority:
            auth_col1, auth_col2 = st.columns(2)
            with auth_col1:
                st.markdown(f"""
                <div style="background: rgba(34, 193, 195, 0.08); border: 1px solid rgba(34, 193, 195, 0.25); 
                            border-radius: 12px; padding: 18px;">
                    <p style="margin:0 0 6px 0; font-weight: 700; font-size: 1.05rem; color: #22c1c3;">🏛️ {authority['board_name']}</p>
                    <p style="margin:0; font-size: 0.9rem; color: rgba(255,255,255,0.7);">State: {authority['state']}</p>
                    <p style="margin:4px 0 0 0; font-size: 0.9rem;">📧 {authority['email'] or 'No email available'}</p>
                    <p style="margin:4px 0 0 0; font-size: 0.9rem;">📞 {authority['phone'] or 'N/A'}</p>
                    {'<p style="margin:4px 0 0 0; font-size: 0.9rem;">📱 ' + authority['complaint_app'] + '</p>' if authority.get('complaint_app') else ''}
                </div>
                """, unsafe_allow_html=True)
            with auth_col2:
                if municipal:
                    st.markdown(f"""
                    <div style="background: rgba(253, 187, 45, 0.08); border: 1px solid rgba(253, 187, 45, 0.25);
                                border-radius: 12px; padding: 18px;">
                        <p style="margin:0 0 6px 0; font-weight: 700; font-size: 1.05rem; color: #fdbb2d;">🏢 {municipal['corp_name']}</p>
                        <p style="margin:0; font-size: 0.9rem; color: rgba(255,255,255,0.7);">Municipal Corporation</p>
                        <p style="margin:4px 0 0 0; font-size: 0.9rem;">📧 {municipal['email'] or 'No email (use phone/app)'}</p>
                        <p style="margin:4px 0 0 0; font-size: 0.9rem;">📞 {municipal['phone'] or 'N/A'}</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("No municipal corporation contact found for this city. The SPCB above is the primary authority.")

            st.markdown("")

            if authority.get('email'):
                language = st.selectbox(
                        "📝 Email Language",
                        ["English", "Hindi", "Tamil", "Bengali", "Marathi", "Telugu", "Kannada", "Gujarati"],
                        key="email_language"
                    )
                if st.button("✉️  Generate Complaint Email", type="primary", use_container_width=True):
                    user = st.session_state.get('user', {})
                    with st.spinner("Generating email with AI..."):
                        try:
                            result = generate_complaint_email(
                                city=city_data.get('City', ''),
                                state=city_data.get('State', ''),
                                area=city_data.get('Area', ''),
                                aqi=city_data.get('AQI', 0),
                                pm25=city_data.get('PM2.5 (µg/m³)', 0),
                                category=city_data.get('Category', ''),
                                authority_name=authority['board_name'],
                                authority_email=authority['email'],
                                nearby_factories=factories,
                                station_count=len(stations),
                                user_name=user.get('full_name', 'Concerned Citizen'),
                                user_email=user.get('email', ''),
                                language = language,
                            )
                            st.session_state.email_draft = result
                            
                            # Log to database for record-keeping
                            if user.get('id'):
                                log_generated_email(
                                    user_id=user['id'],
                                    city=city_data.get('City', ''),
                                    authority_email=authority['email'],
                                    subject=result['subject'],
                                    body=result['body']
                                )
                                
                        except Exception as e:
                            st.error(f"Failed to generate email: {e}")

                # Show email draft if generated
                if st.session_state.email_draft:
                    draft = st.session_state.email_draft
                    st.markdown("### 📄 Email Preview")

                    st.markdown(f"""
                    <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1);
                                border-radius: 12px; padding: 24px; font-family: 'Inter', sans-serif;">
                        <p style="margin: 0 0 4px 0; font-size: 0.85rem; color: rgba(255,255,255,0.5);">TO</p>
                        <p style="margin: 0 0 14px 0; font-weight: 600;">{draft['to_name']} &lt;{draft['to']}&gt;</p>
                        <p style="margin: 0 0 4px 0; font-size: 0.85rem; color: rgba(255,255,255,0.5);">FROM</p>
                        <p style="margin: 0 0 14px 0; font-weight: 600;">{draft['from_name']} &lt;{draft['from_email']}&gt;</p>
                        <p style="margin: 0 0 4px 0; font-size: 0.85rem; color: rgba(255,255,255,0.5);">SUBJECT</p>
                        <p style="margin: 0 0 14px 0; font-weight: 600;">{draft['subject']}</p>
                        <hr style="border-color: rgba(255,255,255,0.1); margin: 14px 0;">
                        <div style="white-space: pre-wrap; line-height: 1.7; font-size: 0.95rem; color: rgba(255,255,255,0.85);">{draft['body']}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown("##### 📋 Copy Email Content")
                    full_email_text = f"To: {draft['to']}\nSubject: {draft['subject']}\n\n{draft['body']}"
                    st.code(full_email_text, language="text")

                    st.markdown("")
                    if st.button("🗑️  Discard Draft", use_container_width=False):
                        st.session_state.email_draft = None
                        st.rerun()
            else:
                st.warning(f"No email address available for {authority['board_name']}. "
                           f"Please use their phone ({authority['phone']}) or complaint app.")
        else:
            st.info("No authority contact found for this state. You can report to CPCB at cpcb.nic.in.")


# ============================================================
#                    DASHBOARD VIEW
# ============================================================

def render_dashboard():
    st.title("🌿 India AQI Dashboard")
    st.markdown("Real-time air quality index monitoring for cities across India. Click **View Map** on any tile to explore the area.")

    def update_filters():
        st.session_state.search_keyword = st.session_state._search
        st.session_state.selected_states = st.session_state._states
        st.session_state.sort_order = st.session_state._sort
        st.session_state.page = 1

    # --- Sidebar user info ---
    if st.session_state.get('authenticated') and st.session_state.get('user'):
        user = st.session_state.user
        with st.sidebar.container(key="account_block"):
            st.markdown(f"""
            <div style="background: rgba(34, 193, 195, 0.08); border: 1px solid rgba(34, 193, 195, 0.2);
                        border-radius: 10px; padding: 14px; text-align: center;">
                <p style="margin: 0 0 8px 0; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.06em;
                          text-transform: uppercase; color: rgba(255,255,255,0.5);">👤 Account</p>
                <p style="margin: 0; font-weight: 600; font-size: 1rem;">{user['full_name']}</p>
                <p style="margin: 4px 0 0 0; font-size: 0.8rem; color: rgba(255,255,255,0.5);">{user['email']}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🚪 Logout", use_container_width=True):
                _token = st.query_params.get("auth_token")
                if _token:
                    delete_session(_token)
                    del st.query_params["auth_token"]
                st.session_state.authenticated = False
                st.session_state.user = None
                st.session_state.current_page = 'landing'
                st.session_state.email_draft = None
                st.rerun()

    # --- Sidebar filters ---
    st.sidebar.header("📡 Data Status")
    last_updated = get_data_timestamp() or "Never"
    st.sidebar.caption(f"Last updated:\n**{last_updated}**")
    
    if st.sidebar.button("🔄 Refresh Live Data", use_container_width=True):
        with st.sidebar.status("Fetching AQI data...") as status:
            success = refresh_aqi_data(progress_container=status)
            if success:
                status.update(label="AQI data refreshed!", state="complete")
                # Clear cache and rerun to show new data
                load_data.clear()
                load_raw_data.clear()
                st.rerun()
            else:
                st.sidebar.error("Refresh failed.")

    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filters & Search")
    st.sidebar.text_input("Search Location", placeholder="e.g. Delhi, Pune...", 
                          value=st.session_state.search_keyword, key="_search", on_change=update_filters)
    
    states = sorted(df['State'].unique().tolist())
    st.sidebar.multiselect("Filter by State", states, 
                           default=st.session_state.selected_states, key="_states", on_change=update_filters)
    
    sort_idx = 0 if st.session_state.sort_order == "Highest First (Descending)" else 1
    st.sidebar.radio("Sort AQI by:", ("Highest First (Descending)", "Lowest First (Ascending)"), 
                     index=sort_idx, key="_sort", on_change=update_filters)
    
    search_keyword = st.session_state.search_keyword
    selected_states = st.session_state.selected_states
    ascending = st.session_state.sort_order == "Lowest First (Ascending)"

    # --- Apply filters ---
    filtered_df = df.copy()
    if search_keyword:
        mask = (
            filtered_df['City'].str.contains(search_keyword, case=False, na=False) |
            filtered_df['State'].str.contains(search_keyword, case=False, na=False) |
            filtered_df['Area'].str.contains(search_keyword, case=False, na=False)
        )
        filtered_df = filtered_df[mask]
    if selected_states:
        filtered_df = filtered_df[filtered_df['State'].isin(selected_states)]
    filtered_df = filtered_df.sort_values(by='AQI', ascending=ascending).reset_index(drop=True)

    # --- Pagination ---
    RESULTS_PER_PAGE = 15
    total_results = len(filtered_df)
    total_pages = max(1, (total_results - 1) // RESULTS_PER_PAGE + 1)

    if st.session_state.page > total_pages:
        st.session_state.page = total_pages

    st.write(f"**Total Results Found:** {total_results}")

    if total_results > 0:
        start_idx = (st.session_state.page - 1) * RESULTS_PER_PAGE
        end_idx = start_idx + RESULTS_PER_PAGE
        paginated_df = filtered_df.iloc[start_idx:end_idx]

        # --- Render tiles ---
        cols = st.columns(3)
        for idx, row in enumerate(paginated_df.to_dict('records')):
            col = cols[idx % 3]
            bg_color, text_color = get_category_colors(row['Category'])

            tile_html = f"""
            <div style="
                background-color: {bg_color};
                color: {text_color};
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 8px;
                box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
                text-align: center;
                transition: transform 0.2s;
            " onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
                <div style="margin-top: 0; margin-bottom: 5px; color: {text_color}; font-size: 1.5rem; font-weight: 700;">{row['City']}</div>
                <div style="margin-top: 0; margin-bottom: 5px; font-size: 1.1rem; opacity: 0.95;"><b>{row['Area']}</b></div>
                <div style="margin-top: 0; margin-bottom: 15px; font-size: 0.9rem; opacity: 0.85;">{row['State']}</div>
                <div style="margin: 10px 0; font-size: 2.5rem; font-weight: 700; color: {text_color};">{row['AQI']}</div>
                <div style="margin: 0; font-size: 1.1rem; font-weight: 600; color: {text_color};">{row['Category']}</div>
                <div style="margin-top: 15px; padding-top: 10px; border-top: 1px solid rgba(0,0,0,0.1); font-size: 0.8rem; opacity: 0.8; text-align: left;">
                    <div><b>PM2.5:</b> {row['PM2.5 (µg/m³)']:.2f} µg/m³</div>
                    <div><b>Lat:</b> {row['Latitude']:.4f}</div>
                    <div><b>Lon:</b> {row['Longitude']:.4f}</div>
                </div>
            </div>
            """

            with col:
                st.markdown(tile_html, unsafe_allow_html=True)
                if st.button("🗺️ View Map", key=f"map_{st.session_state.page}_{idx}", width='stretch'):
                    st.session_state.view = 'city_detail'
                    st.session_state.selected_city = row
                    st.rerun()

        # --- Pagination controls ---
        st.markdown("---")
        if total_pages > 1:
            pcol1, pcol2, pcol3, pcol4, pcol5 = st.columns([2, 1, 2, 1, 2])
            with pcol2:
                if st.button("⬅️ Prev", width='stretch') and st.session_state.page > 1:
                    st.session_state.page -= 1
                    st.rerun()
            with pcol3:
                st.markdown(
                    f"<div style='text-align:center;margin-top:7px;font-size:1.1rem;'>"
                    f"Page <b>{st.session_state.page}</b> of <b>{total_pages}</b></div>",
                    unsafe_allow_html=True,
                )
            with pcol4:
                if st.button("Next ➡️", width='stretch') and st.session_state.page < total_pages:
                    st.session_state.page += 1
                    st.rerun()
    else:
        st.warning("No cities found matching your filters.")


# ============================================================
#                    MAIN ROUTING
# ============================================================

page = st.session_state.current_page

if page == 'landing':
    from pages.landing import render_landing
    render_landing()

elif page == 'auth':
    from pages.auth import render_auth
    render_auth()

elif page == 'dashboard':
    # Require authentication
    if not st.session_state.get('authenticated'):
        st.session_state.current_page = 'auth'
        st.rerun()
    else:
        if st.session_state.view == 'city_detail' and st.session_state.selected_city is not None:
            render_city_detail()
        else:
            render_dashboard()

else:
    # Fallback to landing
    from pages.landing import render_landing
    render_landing()