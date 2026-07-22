# 🗺️ Project Roadmap — India AQI Dashboard

> A complete, step-by-step walkthrough of how this project was built from scratch, covering every decision, data source, script, and feature.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Problem Statement & Motivation](#2-problem-statement--motivation)
3. [Architecture & High-Level Flowchart](#3-architecture--high-level-flowchart)
4. [Tech Stack Choices](#4-tech-stack-choices)
5. [Step 1 — Project Setup & Environment](#step-1--project-setup--environment)
6. [Step 2 — Data Sourcing & Collection](#step-2--data-sourcing--collection)
7. [Step 3 — Data Preprocessing Pipeline](#step-3--data-preprocessing-pipeline)
8. [Step 4 — AQI Calculation Engine](#step-4--aqi-calculation-engine)
9. [Step 5 — Building the Dashboard (app.py)](#step-5--building-the-dashboard-apppy)
10. [Step 6 — City Detail View & Interactive Maps](#step-6--city-detail-view--interactive-maps)
11. [Step 7 — Emissions Analytics & Charts](#step-7--emissions-analytics--charts)
12. [Step 8 — Live Data Refresh System](#step-8--live-data-refresh-system)
13. [Data Flow Diagram (End-to-End)](#data-flow-diagram-end-to-end)
14. [File-by-File Reference](#file-by-file-reference)
15. [Key Algorithms & Logic](#key-algorithms--logic)
16. [Summary](#summary)

---

## 1. Project Overview

This is a **real-time Air Quality Index (AQI) monitoring dashboard** for cities across India. It combines:

- **Live AQI data** from 500+ government monitoring stations (via the OpenAQ API)
- **Industrial facility data** from 2,391 Climate TRACE facilities and 1,603 GEM facilities
- **PM2.5 emission breakdowns** by source — Industry, Transport, Crop Fires, Buildings
- **Interactive maps** with 5 km AQI grid overlays and factory markers
- **Analytics** — seasonal emission trends, factory leaderboards, pollution source breakdowns

The final product is a single Streamlit web app (`app.py`) backed by 4 preprocessed JSON data files.

---

## 2. Problem Statement & Motivation

This project was built for the **ET AI Hackathon 2026** (problem statement PDF stored in `docs/`). The challenge was:

> *"Build a tool that helps citizens and policymakers understand air quality in Indian cities — not just the AQI number, but **why** the air is polluted and **who** the biggest contributors are."*

Most AQI dashboards only show a number. This project goes further by answering:

| Question | How the project answers it |
|----------|--------------------------|
| "What's the AQI in my city?" | Live PM2.5 readings from OpenAQ, converted to India's NAQI scale |
| "Where exactly is the pollution worst?" | 5 km × 5 km grid overlay on an interactive map |
| "What's causing it?" | PM2.5 breakdown by source: Industry, Transport, Crop Fires, Buildings |
| "When is it worst?" | Monthly seasonal trend charts (e.g., crop fire spikes in Oct–Nov) |
| "Who are the biggest polluters?" | Factory leaderboard ranked by emissions, with map pins |

---

## 3. Architecture & High-Level Flowchart

```
┌─────────────────────────────────────────────────────────────────────┐
│                       RAW DATA SOURCES                              │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────────────┐  │
│  │  OpenAQ API  │  │  Climate TRACE   │  │  Global Energy        │  │
│  │  (Live API)  │  │  (CSV files)     │  │  Monitor (Excel)      │  │
│  └──────┬───────┘  └───────┬──────────┘  └──────────┬────────────┘  │
└─────────┼──────────────────┼────────────────────────┼───────────────┘
          │                  │                        │
          ▼                  ▼                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PREPROCESSING SCRIPTS                            │
│  ┌──────────────────┐ ┌─────────────────────┐ ┌─────────────────┐  │
│  │ fetch_aqi_data.py│ │preprocess_factories │ │preprocess_gem   │  │
│  │                  │ │       .py           │ │    _data.py     │  │
│  └──────┬───────────┘ └──────────┬──────────┘ └───────┬─────────┘  │
│         │             ┌──────────────────────┐        │            │
│         │             │preprocess_city       │        │            │
│         │             │  _emissions.py       │        │            │
│         │             └──────────┬───────────┘        │            │
└─────────┼────────────────────────┼────────────────────┼────────────┘
          │                        │                    │
          ▼                        ▼                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     PROCESSED DATA (data/)                          │
│  ┌───────────────────┐  ┌────────────────────────┐                 │
│  │india_aqi_data.json│  │india_factories_data.json│                │
│  │(500+ stations)    │  │(2,391 facilities)       │                │
│  └───────────────────┘  └────────────────────────┘                 │
│  ┌───────────────────┐  ┌────────────────────────┐                 │
│  │india_gem_data.json│  │city_emissions_data.json │                │
│  │(1,603 facilities) │  │(city-level PM2.5 trends)│                │
│  └───────────────────┘  └────────────────────────┘                 │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      STREAMLIT APP (app.py)                         │
│                                                                     │
│  ┌─────────────────┐    ┌──────────────────────────┐               │
│  │ DASHBOARD VIEW  │───▶│    CITY DETAIL VIEW       │               │
│  │ (tile grid +    │    │ (map + grid + factories   │               │
│  │  search/filter) │    │  + emissions + leaderboard)│              │
│  └─────────────────┘    └──────────────────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Tech Stack Choices

| Layer | Technology | Why it was chosen |
|-------|-----------|-------------------|
| **Web framework** | Streamlit | Rapid prototyping — entire dashboard in a single Python file, no frontend code needed |
| **Interactive maps** | Folium (Leaflet.js wrapper) | Rich map features: grid overlays, circle markers, icon markers, popups, tooltips |
| **Map rendering** | streamlit-folium | Bridge to render Folium maps inside Streamlit |
| **Charts** | Altair | Declarative charting — concise code for line charts with tooltips and color encoding |
| **Data wrangling** | Pandas | Industry standard for CSV/Excel reading and DataFrame manipulation |
| **API calls** | Requests | Standard HTTP client for OpenAQ API |
| **Reverse geocoding** | reverse_geocoder | Offline lat/lon → city/state resolution (no API quota issues) |
| **Excel reading** | openpyxl | Required by Pandas to read `.xlsx` files from GEM trackers |

---

## Step 1 — Project Setup & Environment

### What was done:

1. **Created the project folder structure:**
   ```
   Monitoring-AQI-main/
   ├── app.py
   ├── requirements.txt
   ├── data/            ← processed JSON files
   ├── raw_data/        ← source CSVs and Excel files (gitignored)
   │   ├── climate_trace/
   │   └── gem/
   ├── scripts/         ← preprocessing scripts
   └── docs/            ← hackathon problem statement
   ```

2. **Set up a Python virtual environment:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Created `.gitignore`** to exclude:
   - Virtual environments (`.venv/`)
   - Python cache (`__pycache__/`)
   - IDE files (`.vscode/`, `.idea/`)
   - Raw data files (`raw_data/`) — too large for Git
   - OS files (`.DS_Store`, `Thumbs.db`)

4. **Obtained API key** for OpenAQ v3 API (free registration at openaq.org).

### Key decision: Why separate `raw_data/` from `data/`?
- `raw_data/` contains the original downloaded CSVs and Excel files (~hundreds of MBs). These are gitignored.
- `data/` contains the lightweight processed JSON files (~3 MB total). These ARE tracked in Git so the dashboard works immediately after cloning — no preprocessing needed.

---

## Step 2 — Data Sourcing & Collection

Three completely independent data sources were used:

### Source A — OpenAQ API (Live AQI)

| Detail | Value |
|--------|-------|
| **API** | OpenAQ v3 (`api.openaq.org/v3`) |
| **Authentication** | API key via `X-Api-Key` header |
| **Country filter** | `countries_id=9` (India) |
| **Pollutant** | PM2.5 (parameter ID `2`) |
| **Stations covered** | 500+ monitoring stations across India |
| **Data freshness** | Real-time (latest readings) |

**How it works (2-step API call pattern):**

```
Step 1: GET /v3/locations?countries_id=9
        → Returns all India monitoring station IDs (paginated, 1000/page)

Step 2: GET /v3/parameters/2/latest
        → Returns latest PM2.5 readings globally (paginated)
        → Filter to only keep readings matching India station IDs
```

This 2-step pattern is necessary because OpenAQ's `/latest` endpoint doesn't support country filtering directly — it returns global data, so the script must first build a set of India station IDs and then filter the global PM2.5 readings against that set.

### Source B — Climate TRACE (Industrial Emissions)

| Detail | Value |
|--------|-------|
| **Source** | climatetrace.org — downloadable CSV bundles |
| **Data format** | CSV files organized by sector |
| **Sectors used** | Manufacturing, Power, Fossil Fuel Ops, Mineral Extraction, Waste |
| **Subsectors** | 14 specific subsectors (cement, aluminum, coal-mining, etc.) |
| **Key columns** | `source_name`, `lat`, `lon`, `emissions_quantity`, `gas`, `capacity` |
| **Gas types** | co2e_100yr, co2, pm2_5 (prioritized in this order) |
| **Area-level data** | Road transportation, cropland fires, buildings (for PM2.5 trends) |

**Folder structure of raw Climate TRACE data:**
```
raw_data/climate_trace/DATA/
├── manufacturing/
│   ├── cement_emissions_sources_v*.csv
│   ├── aluminum_emissions_sources_v*.csv
│   ├── chemicals_emissions_sources_v*.csv
│   ├── iron-and-steel_emissions_sources_v*.csv
│   └── ...
├── power/
│   └── electricity-generation_emissions_sources_v*.csv
├── fossil_fuel_operations/
│   ├── coal-mining_emissions_sources_v*.csv
│   └── ...
├── transportation/
│   └── road-transportation_emissions_sources_v*.csv
├── agriculture/
│   └── cropland-fires_emissions_sources_v*.csv
└── buildings/
    ├── residential-onsite-fuel-usage_emissions_sources_v*.csv
    └── non-residential-onsite-fuel-usage_emissions_sources_v*.csv
```

### Source C — Global Energy Monitor (GEM)

| Detail | Value |
|--------|-------|
| **Source** | globalenergymonitor.org — downloadable Excel trackers |
| **Data format** | `.xlsx` files (21 Excel files in `raw_data/gem/`) |
| **Trackers processed** | 10 different GEM trackers |
| **Key fields** | Facility name, lat/lon, capacity (MW/Mt), status, owner |

**The 10 GEM trackers processed:**

| # | Tracker | India facilities | Key data |
|---|---------|-----------------|----------|
| 1 | Global Coal Mine Tracker | 552+ mines | Methane emissions, capacity (Mtpa) |
| 2 | Global Coal Plant Tracker | 1,977 units | CO2 emissions, capacity (MW) |
| 3 | Global Solar Power Tracker | ≥50 MW farms | Capacity (MW), no emissions |
| 4 | Global Oil & Gas Plant Tracker | 115 units | Capacity (MW) |
| 5 | Global Bioenergy Power Tracker | ≥10 MW plants | Capacity (MW) |
| 6 | Global Coal Terminals Tracker | 61 terminals | Capacity (Mt) |
| 7 | Global Oil & Gas Extraction Tracker | 19 fields | Production type |
| 8 | Global Cement & Concrete Tracker | 333 plants | Cement/clinker capacity (Mmtpa) |
| 9 | Global Iron Ore Mines Tracker | 248 mines | Capacity (ktpa) |
| 10 | Global Chemicals Inventory | 48 plants | Primary products, feedstock |

---

## Step 3 — Data Preprocessing Pipeline

Four scripts transform raw data into dashboard-ready JSON. Here's exactly what each does:

### Script 1: `fetch_aqi_data.py` → `india_aqi_data.json`

**Purpose:** Fetch live PM2.5 readings from OpenAQ and convert to AQI.

**Flow:**
```
┌──────────────────────┐
│ 1. GET /v3/locations │ ← Paginated (1000/page), filtered to India (countries_id=9)
│    Extract all IDs   │ ← Rate limit handling: sleep 60s on HTTP 429
└──────────┬───────────┘
           ▼
┌──────────────────────────┐
│ 2. GET /parameters/2/    │ ← Parameter 2 = PM2.5
│    latest                │ ← Paginated, returns GLOBAL data
│    Filter to India IDs   │ ← Match against the set from step 1
│    Calculate AQI         │ ← Piecewise linear (India NAQI breakpoints)
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│ 3. Reverse Geocode       │ ← Using `reverse_geocoder` library (offline)
│    (lat, lon) → city,    │ ← Bulk geocodes all coordinates at once
│    state, area           │
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│ 4. Save JSON             │ → data/india_aqi_data.json
│    Keyed by location_id  │
└──────────────────────────┘
```

**Output structure (per station):**
```json
{
  "7282": {
    "city": "Thanesar",
    "state": "Haryana",
    "area": "Kurukshetra",
    "longitude": 76.875879,
    "latitude": 29.966942,
    "pm_value_used": 13.7,
    "aqi": 23,
    "category": "Good"
  }
}
```

### Script 2: `preprocess_factories.py` → `india_factories_data.json`

**Purpose:** Extract point-source industrial facilities from Climate TRACE CSVs.

**Flow:**
```
For each of 5 sectors × their subsectors:
  ┌────────────────────────────────┐
  │ 1. Find CSV by glob pattern   │ ← e.g., cement_emissions_sources_v*.csv
  │    in raw_data/climate_trace/  │
  └──────────┬─────────────────────┘
             ▼
  ┌────────────────────────────────┐
  │ 2. Filter to best gas type    │ ← Priority: co2e_100yr > co2 > pm2_5
  │    (avoid duplicate rows)     │
  └──────────┬─────────────────────┘
             ▼
  ┌────────────────────────────────┐
  │ 3. Keep latest year only      │ ← Group by source_id, max(year)
  │    per facility               │
  └──────────┬─────────────────────┘
             ▼
  ┌────────────────────────────────┐
  │ 4. Deduplicate by source_id   │ ← Global dedup after all sectors
  └──────────┬─────────────────────┘
             ▼
  ┌────────────────────────────────┐
  │ 5. Save JSON array            │ → data/india_factories_data.json
  │    (2,391 unique facilities)  │
  └────────────────────────────────┘
```

**Sectors and subsectors processed:**

| Sector | Subsectors | Icon |
|--------|-----------|------|
| Manufacturing | cement, aluminum, chemicals, iron-and-steel, petrochemical-steam-cracking, pulp-and-paper | 🏭 industry |
| Power | electricity-generation | ⚡ bolt |
| Fossil Fuel Operations | coal-mining, oil-and-gas-production, oil-and-gas-refining, oil-and-gas-transport | 🔥 fire |
| Mineral Extraction | bauxite-mining, copper-mining, iron-mining | 💎 gem |
| Waste | solid-waste-disposal, industrial-wastewater-treatment-and-discharge | ♻️ recycle |

### Script 3: `preprocess_gem_data.py` → `india_gem_data.json`

**Purpose:** Extract Indian facilities from 10 GEM Excel trackers, deduplicate against Climate TRACE.

This is the most complex preprocessing script (617 lines). It has:
- **10 individual processor functions** — one per GEM tracker file
- **Internal deduplication** — removes facilities within 0.5 km of each other in the same sector
- **Cross-source deduplication** — removes GEM facilities within 1 km of an existing Climate TRACE facility in a related sector

**Flow:**
```
┌─────────────────────────────────┐
│ For each of 10 GEM trackers:    │
│  1. Read Excel sheet            │ ← openpyxl engine
│  2. Filter to India rows        │ ← Country column contains "India"
│  3. Extract lat/lon             │ ← Some have columns, some need
│     (varies per tracker)        │   coordinate string parsing
│  4. Normalize capacity units    │ ← Mtpa → tonnes, MW stays MW, etc.
│  5. Append to all_facilities    │
└──────────┬──────────────────────┘
           ▼
┌─────────────────────────────────┐
│ Internal Dedup                  │ ← Same sector + within 0.5 km
│ (Haversine distance check)     │   = duplicate, keep first
└──────────┬──────────────────────┘
           ▼
┌─────────────────────────────────┐
│ Cross-Source Dedup              │ ← Load india_factories_data.json
│ vs Climate TRACE                │   (must run preprocess_factories.py first!)
│                                 │ ← Sector keyword matching + within 1 km
│                                 │   = duplicate, remove GEM entry
└──────────┬──────────────────────┘
           ▼
┌─────────────────────────────────┐
│ Save JSON array                 │ → data/india_gem_data.json
│ (1,603 unique GEM facilities)   │
└─────────────────────────────────┘
```

**Coordinate parsing challenge:**
Some GEM trackers (Cement, Iron Ore, Chemicals) store coordinates as a single string `"23.119, 81.689"` instead of separate Latitude/Longitude columns. The `parse_coordinates()` function handles this by splitting on commas/semicolons/whitespace and extracting the first two valid floats.

**Deduplication logic (cross-source):**
```python
# Quick bounding box pre-filter (skip if > ~2km apart)
if abs(gem_lat - ct_lat) > 0.02 or abs(gem_lon - ct_lon) > 0.02:
    continue

# Sector keyword matching (e.g., "Coal Mining" → ["fossil", "mining", "coal"])
sector_match = any(keyword in climate_trace_sector_lower for keyword in gem_keywords)

# If same sector + within 1km → duplicate
if sector_match and haversine_km(gem, ct) < 1.0:
    is_duplicate = True
```

### Script 4: `preprocess_city_emissions.py` → `city_emissions_data.json`

**Purpose:** Extract area-level PM2.5 emissions from Climate TRACE for transport, crop fires, and buildings — with monthly breakdowns.

**Flow:**
```
┌───────────────────────────────────────┐
│ 1. Road Transportation CSV            │ ← road-transportation_emissions_sources_v*.csv
│    Filter gas == "pm2_5"              │
│    Keep latest year only              │
│    Group by source_name → monthly     │
└──────────┬────────────────────────────┘
           ▼
┌───────────────────────────────────────┐
│ 2. Cropland Fires CSV                 │ ← cropland-fires_emissions_sources_v*.csv
│    Same processing                    │
└──────────┬────────────────────────────┘
           ▼
┌───────────────────────────────────────┐
│ 3. Buildings (2 CSVs combined)        │ ← residential-onsite-fuel-usage_v*.csv
│    + non-residential-onsite-fuel...   │   + non-residential-onsite-fuel-usage_v*.csv
│    Sum together per city              │ ← residential + non-residential = total buildings
└──────────┬────────────────────────────┘
           ▼
┌───────────────────────────────────────┐
│ 4. Normalize city names               │ ← "Delhi Urban Area" → "delhi"
│    Merge all 3 sources per city       │ ← Strip " Urban Area", " Rural Area", etc.
│    Save JSON                          │ → data/city_emissions_data.json
└───────────────────────────────────────┘
```

**Output structure (per city):**
```json
{
  "delhi": {
    "transport": {
      "total": 123.45,
      "monthly": { "2026-01": 30.1, "2026-02": 28.5, ... },
      "source_name": "Delhi Urban Area",
      "year": 2026
    },
    "crop_fires": { "total": ..., "monthly": {...} },
    "buildings": { "total": ..., "monthly": {...} }
  }
}
```

---

## Step 4 — AQI Calculation Engine

The project uses **India's National Air Quality Index (NAQI)** standard, not the US EPA AQI.

### Breakpoint Table (PM2.5 only)

| AQI Category | AQI Range | PM2.5 Concentration (µg/m³) |
|-------------|-----------|----------------------------|
| Good | 0–50 | 0–30 |
| Satisfactory | 51–100 | 31–60 |
| Moderately Polluted | 101–200 | 61–90 |
| Poor | 201–300 | 91–120 |
| Very Poor | 301–400 | 121–250 |
| Severe | 401–500 | 250–1000 |

### Formula (Piecewise Linear Interpolation)

```
AQI = ((I_hi - I_lo) / (BP_hi - BP_lo)) × (C - BP_lo) + I_lo
```

Where:
- `C` = Observed PM2.5 concentration
- `BP_lo`, `BP_hi` = Breakpoint concentrations bracketing `C`
- `I_lo`, `I_hi` = AQI values corresponding to those breakpoints

**Example:** PM2.5 = 75 µg/m³ → Falls in [61, 90] bracket → AQI = ((200-101)/(90-61)) × (75-61) + 101 = **149** (Moderately Polluted)

This calculation appears in three places:
1. `scripts/fetch_aqi_data.py` → `get_pm25_sub_index()` (offline script)
2. `app.py` → `_get_pm25_sub_index()` (live refresh in the app)
3. Both are identical implementations

---

## Step 5 — Building the Dashboard (app.py)

The app is a single 1,018-line Streamlit application with two views managed by `st.session_state`:

### Application Startup Flow

```
┌──────────────────────────────────┐
│ 1. Set page config              │ ← layout="wide", title="India AQI Dashboard"
│ 2. Initialize session state     │ ← view, selected_city, page, search, filters
└──────────┬───────────────────────┘
           ▼
┌──────────────────────────────────┐
│ 3. Check data freshness         │ ← Is india_aqi_data.json missing?
│    If missing → auto-fetch      │ ← Calls refresh_aqi_data() with progress UI
│    If present → proceed         │
└──────────┬───────────────────────┘
           ▼
┌──────────────────────────────────┐
│ 4. Load all 4 JSON data files   │ ← @st.cache_data for performance
│    into DataFrames/dicts        │ ← TTL=300s for AQI data (re-read after 5 min)
└──────────┬───────────────────────┘
           ▼
┌──────────────────────────────────┐
│ 5. Route to view:               │
│    session_state.view ==        │
│    'dashboard' → Dashboard View │
│    'city_detail' → City Detail  │
└──────────────────────────────────┘
```

### Dashboard View — `render_dashboard()`

```
┌──────────────────────────────────────────────────────────────┐
│                        SIDEBAR                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 📡 Data Status (last updated timestamp)                │ │
│  │ 🔄 Refresh Live Data button                            │ │
│  │ ─────────────────────────────────────────               │ │
│  │ 🔍 Search Location (text input)                        │ │
│  │ Filter by State (multiselect)                          │ │
│  │ Sort AQI by (radio: Highest/Lowest first)              │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│                       MAIN AREA                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Title: "🌿 India AQI Dashboard"                        │ │
│  │ Total Results Found: N                                 │ │
│  │                                                         │ │
│  │ ┌──────────┐ ┌──────────┐ ┌──────────┐                │ │
│  │ │ City Tile│ │ City Tile│ │ City Tile│  ← 3 columns   │ │
│  │ │ AQI: 156 │ │ AQI: 89  │ │ AQI: 312 │  ← Color-coded│ │
│  │ │[View Map]│ │[View Map]│ │[View Map]│                │ │
│  │ └──────────┘ └──────────┘ └──────────┘                │ │
│  │         ... (15 tiles per page) ...                    │ │
│  │                                                         │ │
│  │ ⬅️ Prev    Page 1 of 34    Next ➡️                     │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

**Key features:**
- **Color-coded tiles** — background color matches AQI severity (green → red → maroon)
- **Search & filter** — live text search across City, State, Area fields + state multiselect
- **Sorting** — toggle between highest-first and lowest-first AQI
- **Pagination** — 15 results per page with prev/next navigation
- **Hover effects** — CSS `transform: scale(1.02)` on tile hover

**Filter pipeline:**
```python
filtered_df = df.copy()
if search_keyword:
    mask = City.contains(keyword) | State.contains(keyword) | Area.contains(keyword)
    filtered_df = filtered_df[mask]
if selected_states:
    filtered_df = filtered_df[State.isin(selected_states)]
filtered_df = filtered_df.sort_values(by='AQI', ascending=ascending)
```

---

## Step 6 — City Detail View & Interactive Maps

When you click **"View Map"** on any city tile, the app switches to the detail view.

### `render_city_detail()` — Full Flow

```
┌──────────────────────────────────────────────────────────────┐
│ 1. Calculate 50km × 50km bounding box around city center    │
│    (25 km in each direction from the clicked station)       │
│                                                              │
│    delta_lat = 25 / 111.32         ← km per degree latitude │
│    delta_lon = 25 / (111.32 × cos(lat))  ← adjusted for    │
│                                             longitude       │
└──────────┬───────────────────────────────────────────────────┘
           ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. Find all AQI stations within the bounding box            │
│    Find all factories (Climate TRACE + GEM) within bbox     │
└──────────┬───────────────────────────────────────────────────┘
           ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. Build 5km × 5km grid covering the bounding box           │
│                                                              │
│    grid_lat_step = 5 / 111.32                               │
│    grid_lon_step = 5 / (111.32 × cos(lat))                  │
│    Create cell objects: {min_lat, max_lat, min_lon, max_lon} │
└──────────┬───────────────────────────────────────────────────┘
           ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. Assign stations to grid cells                            │
│    Compute avg AQI and avg PM2.5 per cell                   │
└──────────┬───────────────────────────────────────────────────┘
           ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. Render Folium map with:                                  │
│    a. Color-coded grid rectangles (AQI-based fill)          │
│    b. Empty cell outlines (dashed gray)                     │
│    c. Station markers (CircleMarker with popups)            │
│    d. City centre marker (blue icon)                        │
│    e. Factory markers (color-coded by sector, FA icons)     │
│       - 10 sector colors (red, orange, black, purple, etc.) │
│       - 10 sector icons (industry, bolt, fire, leaf, etc.)  │
│       - Popup with name, sector, emissions, capacity, owner │
│       - Data source badge: "Climate TRACE" or "GEM"         │
└──────────────────────────────────────────────────────────────┘
```

### Grid Computation Detail

The grid divides the 50 km × 50 km area into 5 km × 5 km cells (approximately 100 cells). Each cell is a Folium `Rectangle`:

- **Cells with data** → Filled with AQI color (green to maroon), 45% opacity, with tooltip showing avg AQI, avg PM2.5, station count
- **Empty cells** → Faint dashed gray outline, tooltip says "No monitoring data available"

---

## Step 7 — Emissions Analytics & Charts

The city detail view includes three analytics sections below the map:

### Section A: "What's Causing the Air Pollution?"

Combines emissions from 4 sources:

| Source | Data origin |
|--------|------------|
| 🏭 Industry | Sum of `emissions_tonnes` from factories/industries in the bounding box |
| 🚗 Transport | `city_emissions_data.json` → `transport.total` |
| 🔥 Crop Fires | `city_emissions_data.json` → `crop_fires.total` |
| 🏠 Buildings | `city_emissions_data.json` → `buildings.total` |

City matching uses a fuzzy 3-tier strategy in `match_city_to_emissions()`:
```
1. Exact match:    "delhi" == "delhi"            ✓
2. Substring match: "new delhi" contains "delhi"  ✓
3. First-word match: "new" matches "new-delhi"    ✓ (fallback)
```

### Section B: "How Do Emissions Change Throughout the Year?"

An Altair line chart showing monthly PM2.5 emissions for Transport, Crop Fires, and Buildings:
- X-axis: Month (Jan–Dec)
- Y-axis: Emissions (tonnes)
- 3 colored lines: Transport (blue), Crop Fires (orange), Buildings (green)
- Interactive tooltips on hover
- Identifies the peak emission month

### Section C: "Biggest Industrial Polluters Nearby"

A leaderboard table of the top 10 factories ranked by `emissions_tonnes`:
- Medal emojis for ranks 1–3 (🥇🥈🥉)
- Columns: Rank, Facility, Sector, Type, Emissions, Capacity, Source (GEM vs Climate TRACE)

---

## Step 8 — Live Data Refresh System

The app supports refreshing AQI data without restarting:

### Refresh Architecture

```
┌─────────────────────────────────┐
│ User clicks "🔄 Refresh Live   │
│ Data" in sidebar                │
└──────────┬──────────────────────┘
           ▼
┌─────────────────────────────────┐
│ refresh_aqi_data()              │ ← Runs inline (same thread)
│                                 │
│ Step 1/3: Fetch India station   │ ← _fetch_india_location_ids()
│           list from OpenAQ      │   (paginated, with rate limit handling)
│                                 │
│ Step 2/3: Fetch PM2.5 readings  │ ← _fetch_pm25_data()
│           for those stations    │   (paginated, matches against ID set)
│                                 │
│ Step 3/3: Reverse geocode       │ ← _reverse_geocode_results()
│           lat/lon → city names  │   (offline reverse_geocoder library)
│                                 │
│ Save to data/india_aqi_data.json│
└──────────┬──────────────────────┘
           ▼
┌─────────────────────────────────┐
│ Clear Streamlit cache           │ ← load_data.clear()
│ st.rerun()                      │ ← Force re-render with new data
└─────────────────────────────────┘
```

**Auto-refresh on startup:**
- If `india_aqi_data.json` doesn't exist → automatic fetch with progress UI
- If file exists → use cached data (re-read from disk every 5 min via `@st.cache_data(ttl=300)`)

**Data staleness check:**
- `get_data_age_minutes()` checks the file's modification timestamp
- `get_data_timestamp()` returns a human-readable "12 Jul 2026, 03:45 PM" string

---

## Data Flow Diagram (End-to-End)

```
     ┌──────────────────┐
     │   OpenAQ API     │
     │   (Live PM2.5)   │
     └────────┬─────────┘
              │ HTTP GET (paginated)
              ▼
  ┌───────────────────────┐       ┌──────────────────────────────┐
  │ fetch_aqi_data.py     │       │ Climate TRACE CSVs           │
  │ + reverse_geocoder    │       │ (14 subsector files)         │
  └────────┬──────────────┘       └──────────┬───────────────────┘
           │                                  │
           ▼                                  ▼
  ┌────────────────────┐       ┌──────────────────────────────────┐
  │india_aqi_data.json │       │ preprocess_factories.py          │
  │(500+ stations)     │       │ + preprocess_city_emissions.py   │
  └────────┬───────────┘       └───────┬──────────────┬───────────┘
           │                           │              │
           │              ┌────────────┘   ┌──────────┘
           │              ▼                ▼
           │  ┌──────────────────┐ ┌──────────────────────┐
           │  │india_factories   │ │city_emissions        │
           │  │_data.json        │ │_data.json            │
           │  │(2,391 facilities)│ │(city-level PM2.5)    │
           │  └────────┬─────────┘ └──────────┬───────────┘
           │           │                      │
           │           │    ┌─────────────────┘
           │           │    │
           │    ┌──────┘    │   ┌───────────────────────┐
           │    │           │   │ GEM Excel Trackers     │
           │    │           │   │ (10 .xlsx files)       │
           │    │           │   └──────────┬─────────────┘
           │    │           │              │
           │    │           │              ▼
           │    │           │   ┌──────────────────────┐
           │    │           │   │preprocess_gem_data.py│
           │    │           │   │(reads factories JSON │
           │    │           │   │ for deduplication)   │
           │    │           │   └──────────┬───────────┘
           │    │           │              │
           │    │           │              ▼
           │    │           │   ┌──────────────────────┐
           │    │           │   │india_gem_data.json   │
           │    │           │   │(1,603 facilities)    │
           │    │           │   └──────────┬───────────┘
           │    │           │              │
           ▼    ▼           ▼              ▼
  ┌────────────────────────────────────────────────────┐
  │                    app.py                           │
  │         (Streamlit Dashboard + Folium Maps)        │
  │                                                    │
  │  load_data()          → AQI DataFrame              │
  │  load_factory_data()  → Climate TRACE list         │
  │  load_gem_data()      → GEM facilities list        │
  │  load_city_emissions()→ Emissions dict             │
  │                                                    │
  │  Dashboard View ←→ City Detail View                │
  └────────────────────────────────────────────────────┘
```

---

## File-by-File Reference

| File | Lines | Size | Purpose |
|------|-------|------|---------|
| [app.py](app.py) | 1,018 | 42 KB | Main Streamlit app — dashboard + city detail + all UI logic |
| [scripts/fetch_aqi_data.py](scripts/fetch_aqi_data.py) | 178 | 5.8 KB | Fetches live AQI data from OpenAQ API + reverse geocoding |
| [scripts/preprocess_factories.py](scripts/preprocess_factories.py) | 182 | 6.2 KB | Processes Climate TRACE CSVs into factory JSON |
| [scripts/preprocess_gem_data.py](scripts/preprocess_gem_data.py) | 617 | 26 KB | Processes 10 GEM Excel trackers + deduplication |
| [scripts/preprocess_city_emissions.py](scripts/preprocess_city_emissions.py) | 115 | 4.4 KB | Aggregates city-level PM2.5 emissions by source |
| [data/india_aqi_data.json](data/india_aqi_data.json) | 7,252 | 159 KB | 500+ stations with AQI, PM2.5, city, state, coordinates |
| [data/india_factories_data.json](data/india_factories_data.json) | 33,476 | 829 KB | 2,391 Climate TRACE facilities |
| [data/india_gem_data.json](data/india_gem_data.json) | 30,459 | 774 KB | 1,603 GEM facilities (deduplicated) |
| [data/city_emissions_data.json](data/city_emissions_data.json) | 81,902 | 1.8 MB | City-level PM2.5: transport, crop fires, buildings (monthly) |
| [requirements.txt](requirements.txt) | 14 | 254 B | Python dependencies (7 packages) |
| [.gitignore](.gitignore) | 27 | 361 B | Excludes venv, cache, raw_data, IDE files |
| [README.md](README.md) | 108 | 4.8 KB | User-facing documentation |

---

## Key Algorithms & Logic

### 1. Bounding Box Calculation (Lat/Lon to Km)

```python
km_per_deg_lat = 111.32                          # constant everywhere
km_per_deg_lon = 111.32 * cos(radians(center_lat))  # shrinks toward poles

delta_lat = extend_km / km_per_deg_lat
delta_lon = extend_km / km_per_deg_lon
```

Used for: creating the 50 km search area and 5 km grid cells around a city.

### 2. Haversine Distance (Deduplication)

```python
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)² + cos(lat1) * cos(lat2) * sin(dlon/2)²
    return R * 2 * asin(sqrt(a))
```

Used for: removing duplicate facilities between GEM and Climate TRACE datasets (threshold: 1 km same sector).

### 3. AQI Color Mapping

```python
AQI 0–50    → #00b050 (Green)
AQI 51–100  → #92d050 (Yellow-Green)
AQI 101–200 → #ffff00 (Yellow)
AQI 201–300 → #ff9900 (Orange)
AQI 301–400 → #ff0000 (Red)
AQI 400+    → #c00000 (Maroon)
```

Used for: tile backgrounds, grid cell fills, and station circle markers.

### 4. Fuzzy City Name Matching

```python
def match_city_to_emissions(city_name, city_emissions):
    # 1. Exact: "delhi" in city_emissions → match
    # 2. Substring: "new delhi" contains "delhi" → match
    # 3. First-word: "new" from "new delhi" matches key containing "new" → match
```

Used for: connecting AQI station city names to the emissions breakdown data (which uses different naming like "Delhi Urban Area" → normalized to "delhi").

### 5. Streamlit Caching Strategy

```python
@st.cache_data(ttl=300)   # AQI data — re-read from disk every 5 min
def load_data(): ...

@st.cache_data             # Factory/GEM/Emissions data — cached forever
def load_factory_data(): ...  # (only changes when preprocessing scripts re-run)
```

---

## Summary

### Order of Operations to Build This Project

| Step | Action | Output |
|------|--------|--------|
| **1** | Set up project structure, venv, requirements.txt | Runnable Python environment |
| **2** | Download raw data: Climate TRACE CSVs + GEM Excel files | `raw_data/` directory |
| **3** | Obtain OpenAQ API key | API key string |
| **4** | Write `fetch_aqi_data.py` — API calls + AQI calculation + reverse geocoding | `india_aqi_data.json` |
| **5** | Write `preprocess_factories.py` — parse Climate TRACE CSVs by sector | `india_factories_data.json` |
| **6** | Write `preprocess_gem_data.py` — parse 10 Excel trackers + deduplicate | `india_gem_data.json` |
| **7** | Write `preprocess_city_emissions.py` — aggregate PM2.5 by city/source | `city_emissions_data.json` |
| **8** | Build `app.py` — Dashboard view with search, filter, sort, pagination | Working dashboard |
| **9** | Add City Detail view — Folium map + AQI grid + factory markers | Interactive maps |
| **10** | Add Emissions analytics — source breakdown + seasonal trends + leaderboard | Charts + tables |
| **11** | Add Live Refresh — in-app API fetch with progress UI + cache invalidation | Self-updating data |
| **12** | Polish — color coding, hover effects, tooltips, data source badges | Production-ready UI |

### Script Execution Order (Dependencies)

```
1. fetch_aqi_data.py               (independent — calls OpenAQ API)
2. preprocess_factories.py         (independent — reads Climate TRACE CSVs)
3. preprocess_gem_data.py          (depends on #2 — reads india_factories_data.json for dedup)
4. preprocess_city_emissions.py    (independent — reads Climate TRACE area CSVs)
5. streamlit run app.py            (depends on all 4 JSON files existing in data/)
```

> **Note:** Steps 1, 2, and 4 can run in parallel. Step 3 must run after step 2. Step 5 requires all JSON files to be present, but they ship pre-built in the repo — so you can skip steps 1–4 entirely if you just want to run the dashboard.
