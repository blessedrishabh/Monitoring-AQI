"""
Preprocesses Global Energy Monitor (GEM) data for India.
Extracts facilities with geographic coordinates from 10 GEM tracker files,
deduplicates against existing Climate TRACE data, and outputs a consolidated JSON.
"""
import pandas as pd
import json
import os
import math
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
GEM_DIR = os.path.join(PROJECT_ROOT, 'raw_data', 'gem')
OUTPUT_FILE = os.path.join(PROJECT_ROOT, 'data', 'india_gem_data.json')
CLIMATE_TRACE_FILE = os.path.join(PROJECT_ROOT, 'data', 'india_factories_data.json')

# ── Haversine distance (km) for deduplication ────────────────────────────
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

# ── Parse "lat, lon" text coordinate fields ──────────────────────────────
def parse_coordinates(coord_str):
    """Parse a 'lat, lon' string into (lat, lon) floats. Returns (None, None) on failure."""
    if pd.isna(coord_str) or not isinstance(coord_str, str):
        return None, None
    # Try comma-separated
    parts = re.split(r'[,;\s]+', coord_str.strip())
    nums = []
    for p in parts:
        try:
            nums.append(float(p))
        except ValueError:
            continue
    if len(nums) >= 2:
        lat, lon = nums[0], nums[1]
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon
    return None, None

# ── Safe float extraction ────────────────────────────────────────────────
def safe_float(val):
    if pd.isna(val):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def safe_str(val, default=''):
    if pd.isna(val):
        return default
    s = str(val).strip()
    return s if s and s.lower() != 'nan' else default

# ══════════════════════════════════════════════════════════════════════════
#  FILE PROCESSORS — one per GEM tracker
# ══════════════════════════════════════════════════════════════════════════

def process_coal_mines():
    """Global Coal Mine Tracker — 552+ India mines with methane emissions."""
    path = os.path.join(GEM_DIR, "Global Coal Mine Tracker, May 2026__.xlsx")
    facilities = []
    for sheet in ['Non-closed mines', 'Closed mines']:
        try:
            df = pd.read_excel(path, sheet_name=sheet, engine='openpyxl')
        except Exception as e:
            print(f"  [ERROR] {sheet}: {e}")
            continue
        
        # Filter India
        country_col = 'Country / Area'
        df_india = df[df[country_col].astype(str).str.contains('India', case=False, na=False)]
        print(f"  {sheet}: {len(df_india)} India rows")
        
        for _, row in df_india.iterrows():
            lat = safe_float(row.get('Latitude'))
            lon = safe_float(row.get('Longitude'))
            if lat is None or lon is None:
                continue
            
            # Emissions: prefer CO2e 100yr, fallback to CH4
            emissions = safe_float(row.get('CMM Emissions (CO2e 100 years)'))
            if emissions is None:
                ch4 = safe_float(row.get('Reported Coal Mine Methane Emissions (thousand tonnes CH4)'))
                if ch4 is not None:
                    emissions = ch4 * 1000  # convert thousand tonnes to tonnes
            
            capacity = safe_float(row.get('Capacity (Mtpa)'))
            
            facilities.append({
                'name': safe_str(row.get('Mine Name'), 'Unknown Coal Mine'),
                'lat': lat, 'lon': lon,
                'sector': 'Coal Mining',
                'subsector': safe_str(row.get('Coal Type'), 'Coal'),
                'type': safe_str(row.get('Mine Type'), ''),
                'status': safe_str(row.get('Status'), ''),
                'emissions_tonnes': round(emissions, 2) if emissions else None,
                'capacity': round(capacity * 1_000_000, 2) if capacity else None,  # Mtpa → tonnes
                'capacity_units': 'tpa',
                'capacity_display': f"{capacity} Mtpa" if capacity else 'N/A',
                'owner': safe_str(row.get('Owners'), ''),
                'parent': safe_str(row.get('Parent Company'), ''),
                'start_year': safe_str(row.get('Opening Year'), ''),
                'data_source': 'gem',
                'icon': 'cube',
                'gas': 'co2e_100yr' if emissions else '',
            })
    return facilities

def process_coal_plants():
    """Global Coal Plant Tracker — 1977 India units with CO2 emissions."""
    path = os.path.join(GEM_DIR, "Global-Coal-Plant-Tracker-January-2026.xlsx")
    try:
        df = pd.read_excel(path, sheet_name='Units', engine='openpyxl')
    except Exception as e:
        print(f"  [ERROR]: {e}")
        return []
    
    df_india = df[df['Country/Area'].astype(str).str.contains('India', case=False, na=False)]
    print(f"  Units: {len(df_india)} India rows")
    
    facilities = []
    for _, row in df_india.iterrows():
        lat = safe_float(row.get('Latitude'))
        lon = safe_float(row.get('Longitude'))
        if lat is None or lon is None:
            continue
        
        co2_mt = safe_float(row.get('Annual CO2 (million tonnes / annum)'))
        emissions = co2_mt * 1_000_000 if co2_mt else None  # million tonnes → tonnes
        capacity = safe_float(row.get('Capacity (MW)'))
        
        facilities.append({
            'name': safe_str(row.get('Plant name'), 'Unknown Coal Plant'),
            'lat': lat, 'lon': lon,
            'sector': 'Coal Power',
            'subsector': safe_str(row.get('Coal type'), 'Coal'),
            'type': safe_str(row.get('Combustion technology'), ''),
            'status': safe_str(row.get('Status'), ''),
            'emissions_tonnes': round(emissions, 2) if emissions else None,
            'capacity': round(capacity, 2) if capacity else None,
            'capacity_units': 'MW',
            'capacity_display': f"{capacity:.0f} MW" if capacity else 'N/A',
            'owner': safe_str(row.get('Owner'), ''),
            'parent': safe_str(row.get('Parent'), ''),
            'start_year': safe_str(row.get('Start year'), ''),
            'data_source': 'gem',
            'icon': 'bolt',
            'gas': 'co2' if emissions else '',
        })
    return facilities

def process_solar():
    """Global Solar Power Tracker — filter >= 50 MW for India."""
    path = os.path.join(GEM_DIR, "Global-Solar-Power-Tracker-February-2026.xlsx")
    try:
        df = pd.read_excel(path, sheet_name='Utility-Scale (1 MW+)', engine='openpyxl')
    except Exception as e:
        print(f"  [ERROR]: {e}")
        return []
    
    df_india = df[df['Country/Area'].astype(str).str.contains('India', case=False, na=False)]
    # Capacity filter: >= 50 MW
    df_india = df_india.copy()
    df_india['_cap'] = pd.to_numeric(df_india['Capacity (MW)'], errors='coerce')
    df_india = df_india[df_india['_cap'] >= 50]
    print(f"  Utility-Scale (>=50MW): {len(df_india)} India rows")
    
    facilities = []
    for _, row in df_india.iterrows():
        lat = safe_float(row.get('Latitude'))
        lon = safe_float(row.get('Longitude'))
        if lat is None or lon is None:
            continue
        
        capacity = safe_float(row.get('Capacity (MW)'))
        
        facilities.append({
            'name': safe_str(row.get('Project Name'), 'Unknown Solar Farm'),
            'lat': lat, 'lon': lon,
            'sector': 'Solar Power',
            'subsector': safe_str(row.get('Technology Type'), 'Solar PV'),
            'type': 'Solar Farm',
            'status': safe_str(row.get('Status'), ''),
            'emissions_tonnes': None,  # Solar has no direct emissions
            'capacity': round(capacity, 2) if capacity else None,
            'capacity_units': 'MW',
            'capacity_display': f"{capacity:.0f} MW" if capacity else 'N/A',
            'owner': safe_str(row.get('Owner'), ''),
            'parent': '',
            'start_year': safe_str(row.get('Start year'), ''),
            'data_source': 'gem',
            'icon': 'sun-o',
            'gas': '',
        })
    return facilities

def process_oil_gas_plants():
    """Global Oil and Gas Plant Tracker — 115 India units."""
    path = os.path.join(GEM_DIR, "Global-Oil-and-Gas-Plant-Tracker-GOGPT-January-2026.xlsx")
    try:
        df = pd.read_excel(path, sheet_name='Gas & Oil Units', engine='openpyxl')
    except Exception as e:
        print(f"  [ERROR]: {e}")
        return []
    
    df_india = df[df['Country/Area'].astype(str).str.contains('India', case=False, na=False)]
    print(f"  Gas & Oil Units: {len(df_india)} India rows")
    
    facilities = []
    for _, row in df_india.iterrows():
        lat = safe_float(row.get('Latitude'))
        lon = safe_float(row.get('Longitude'))
        if lat is None or lon is None:
            continue
        
        capacity = safe_float(row.get('Capacity (MW)'))
        
        facilities.append({
            'name': safe_str(row.get('Plant name'), 'Unknown Oil/Gas Plant'),
            'lat': lat, 'lon': lon,
            'sector': 'Oil & Gas Power',
            'subsector': safe_str(row.get('Fuel'), 'Gas'),
            'type': safe_str(row.get('Turbine/Engine Technology'), ''),
            'status': safe_str(row.get('Status'), ''),
            'emissions_tonnes': None,
            'capacity': round(capacity, 2) if capacity else None,
            'capacity_units': 'MW',
            'capacity_display': f"{capacity:.0f} MW" if capacity else 'N/A',
            'owner': safe_str(row.get('Owner(s)'), ''),
            'parent': safe_str(row.get('Parent(s)'), ''),
            'start_year': safe_str(row.get('Start year'), ''),
            'data_source': 'gem',
            'icon': 'fire',
            'gas': '',
        })
    return facilities

def process_bioenergy():
    """Global Bioenergy Power Tracker — filter >= 10 MW for India."""
    path = os.path.join(GEM_DIR, "Global-Bioenergy-Power-Tracker-GBPT-V3.xlsx")
    try:
        df = pd.read_excel(path, sheet_name='Data', engine='openpyxl')
    except Exception as e:
        print(f"  [ERROR]: {e}")
        return []
    
    df_india = df[df['Country/Area'].astype(str).str.contains('India', case=False, na=False)]
    df_india = df_india.copy()
    df_india['_cap'] = pd.to_numeric(df_india['Capacity (MW)'], errors='coerce')
    df_india = df_india[df_india['_cap'] >= 10]
    print(f"  Data (>=10MW): {len(df_india)} India rows")
    
    facilities = []
    for _, row in df_india.iterrows():
        lat = safe_float(row.get('Latitude'))
        lon = safe_float(row.get('Longitude'))
        if lat is None or lon is None:
            continue
        
        capacity = safe_float(row.get('Capacity (MW)'))
        
        facilities.append({
            'name': safe_str(row.get('Project Name'), 'Unknown Bioenergy Plant'),
            'lat': lat, 'lon': lon,
            'sector': 'Bioenergy',
            'subsector': safe_str(row.get('Fuel'), 'Biomass'),
            'type': 'Bioenergy Plant',
            'status': safe_str(row.get('Status'), ''),
            'emissions_tonnes': None,
            'capacity': round(capacity, 2) if capacity else None,
            'capacity_units': 'MW',
            'capacity_display': f"{capacity:.0f} MW" if capacity else 'N/A',
            'owner': safe_str(row.get('Owner(s)'), ''),
            'parent': safe_str(row.get('Parent(s)'), ''),
            'start_year': safe_str(row.get('Start year'), ''),
            'data_source': 'gem',
            'icon': 'leaf',
            'gas': '',
        })
    return facilities

def process_coal_terminals():
    """Global Coal Terminals Tracker — 61 India terminals."""
    path = os.path.join(GEM_DIR, "Global-Coal-Terminals-Tracker-December-2024.xlsx")
    try:
        df = pd.read_excel(path, sheet_name='Terminals', engine='openpyxl')
    except Exception as e:
        print(f"  [ERROR]: {e}")
        return []
    
    df_india = df[df['Country/Area'].astype(str).str.contains('India', case=False, na=False)]
    print(f"  Terminals: {len(df_india)} India rows")
    
    facilities = []
    for _, row in df_india.iterrows():
        lat = safe_float(row.get('Latitude'))
        lon = safe_float(row.get('Longitude'))
        if lat is None or lon is None:
            continue
        
        capacity = safe_float(row.get('Capacity (Mt)'))
        
        facilities.append({
            'name': safe_str(row.get('Coal Terminal Name'), 'Unknown Terminal'),
            'lat': lat, 'lon': lon,
            'sector': 'Coal Logistics',
            'subsector': safe_str(row.get('Terminal Type'), 'Coal Terminal'),
            'type': safe_str(row.get('Product Type'), ''),
            'status': safe_str(row.get('Status'), ''),
            'emissions_tonnes': None,
            'capacity': round(capacity * 1_000_000, 2) if capacity else None,
            'capacity_units': 'tpa',
            'capacity_display': f"{capacity} Mt" if capacity else 'N/A',
            'owner': safe_str(row.get('Owner'), ''),
            'parent': '',
            'start_year': safe_str(row.get('Start Year'), ''),
            'data_source': 'gem',
            'icon': 'ship',
            'gas': '',
        })
    return facilities

def process_oil_gas_extraction():
    """Global Oil and Gas Extraction Tracker — 19 India fields."""
    path = os.path.join(GEM_DIR, "Global-Oil-and-Gas-Extraction-Tracker-March-2026.xlsx")
    try:
        df = pd.read_excel(path, sheet_name='Field-level main data', engine='openpyxl')
    except Exception as e:
        print(f"  [ERROR]: {e}")
        return []
    
    df_india = df[df['Country/Area'].astype(str).str.contains('India', case=False, na=False)]
    print(f"  Field-level: {len(df_india)} India rows")
    
    facilities = []
    for _, row in df_india.iterrows():
        lat = safe_float(row.get('Latitude'))
        lon = safe_float(row.get('Longitude'))
        if lat is None or lon is None:
            continue
        
        facilities.append({
            'name': safe_str(row.get('Unit Name'), 'Unknown Oil/Gas Field'),
            'lat': lat, 'lon': lon,
            'sector': 'Oil & Gas Extraction',
            'subsector': safe_str(row.get('Fuel type'), 'Oil & Gas'),
            'type': safe_str(row.get('Production Type'), ''),
            'status': safe_str(row.get('Status'), ''),
            'emissions_tonnes': None,
            'capacity': None,
            'capacity_units': '',
            'capacity_display': 'N/A',
            'owner': safe_str(row.get('Owner(s)'), ''),
            'parent': safe_str(row.get('Parent(s)'), ''),
            'start_year': safe_str(row.get('Production start year'), ''),
            'data_source': 'gem',
            'icon': 'tint',
            'gas': '',
        })
    return facilities

def process_cement():
    """Global Cement and Concrete Tracker — 333 India plants (parse Coordinates)."""
    path = os.path.join(GEM_DIR, "Global-Cement-and-Concrete-Tracker_July-2025.xlsx")
    try:
        df = pd.read_excel(path, sheet_name='Plant Data', engine='openpyxl')
    except Exception as e:
        print(f"  [ERROR]: {e}")
        return []
    
    df_india = df[df['Country/Area'].astype(str).str.contains('India', case=False, na=False)]
    print(f"  Plant Data: {len(df_india)} India rows")
    
    facilities = []
    for _, row in df_india.iterrows():
        lat, lon = parse_coordinates(str(row.get('Coordinates', '')))
        if lat is None or lon is None:
            continue
        
        cement_cap = safe_float(row.get('Cement Capacity (millions metric tonnes per annum)'))
        clinker_cap = safe_float(row.get('Clinker Capacity (millions metric tonnes per annum)'))
        capacity = cement_cap or clinker_cap
        
        facilities.append({
            'name': safe_str(row.get('GEM Asset name (English)'), 'Unknown Cement Plant'),
            'lat': lat, 'lon': lon,
            'sector': 'Cement',
            'subsector': safe_str(row.get('Production type'), 'Cement'),
            'type': safe_str(row.get('Plant type'), ''),
            'status': safe_str(row.get('Operating status'), ''),
            'emissions_tonnes': None,
            'capacity': round(capacity * 1_000_000, 2) if capacity else None,
            'capacity_units': 'tpa',
            'capacity_display': f"{capacity} Mmtpa" if capacity else 'N/A',
            'owner': safe_str(row.get('Owner name (English)'), ''),
            'parent': safe_str(row.get('Parent'), ''),
            'start_year': safe_str(row.get('Start date'), ''),
            'data_source': 'gem',
            'icon': 'building',
            'gas': '',
        })
    return facilities

def process_iron_ore():
    """Global Iron Ore Mines Tracker — 248 India mines (parse Coordinates)."""
    path = os.path.join(GEM_DIR, "Global-Iron-Ore-Mines-Tracker-August-2025-V1.xlsx")
    try:
        df = pd.read_excel(path, sheet_name='Main Data', engine='openpyxl')
    except Exception as e:
        print(f"  [ERROR]: {e}")
        return []
    
    df_india = df[df['Country/Area'].astype(str).str.contains('India', case=False, na=False)]
    print(f"  Main Data: {len(df_india)} India rows")
    
    facilities = []
    for _, row in df_india.iterrows():
        lat, lon = parse_coordinates(str(row.get('Coordinates', '')))
        if lat is None or lon is None:
            continue
        
        capacity = safe_float(row.get('Design capacity (ttpa)'))
        
        facilities.append({
            'name': safe_str(row.get('Asset name (English)'), 'Unknown Iron Ore Mine'),
            'lat': lat, 'lon': lon,
            'sector': 'Iron Ore Mining',
            'subsector': 'Iron Ore',
            'type': 'Mine',
            'status': safe_str(row.get('Operating status'), ''),
            'emissions_tonnes': None,
            'capacity': round(capacity * 1000, 2) if capacity else None,  # ttpa (thousand tonnes) → tonnes
            'capacity_units': 'tpa',
            'capacity_display': f"{capacity:.0f} ktpa" if capacity else 'N/A',
            'owner': safe_str(row.get('Owner'), ''),
            'parent': safe_str(row.get('Parent'), ''),
            'start_year': safe_str(row.get('Start date'), ''),
            'data_source': 'gem',
            'icon': 'diamond',
            'gas': '',
        })
    return facilities

def process_chemicals():
    """Global Chemicals Inventory — 48 India plants (parse Coordinates)."""
    path = os.path.join(GEM_DIR, "Plant-level-data-Global-Chemicals-Inventory-November-2025-V1.xlsx")
    try:
        df = pd.read_excel(path, sheet_name='Plant data', engine='openpyxl')
    except Exception as e:
        print(f"  [ERROR]: {e}")
        return []
    
    df_india = df[df['Country/area'].astype(str).str.contains('India', case=False, na=False)]
    print(f"  Plant data: {len(df_india)} India rows")
    
    facilities = []
    for _, row in df_india.iterrows():
        lat, lon = parse_coordinates(str(row.get('Coordinates', '')))
        if lat is None or lon is None:
            continue
        
        facilities.append({
            'name': safe_str(row.get('Plant name (English)'), 'Unknown Chemical Plant'),
            'lat': lat, 'lon': lon,
            'sector': 'Chemicals',
            'subsector': safe_str(row.get('Primary products'), 'Chemical'),
            'type': safe_str(row.get('Feedstock'), ''),
            'status': '',
            'emissions_tonnes': None,
            'capacity': None,
            'capacity_units': '',
            'capacity_display': 'N/A',
            'owner': safe_str(row.get('Owner (English)'), ''),
            'parent': '',
            'start_year': '',
            'data_source': 'gem',
            'icon': 'flask',
            'gas': '',
        })
    return facilities


# ══════════════════════════════════════════════════════════════════════════
#  DEDUPLICATION
# ══════════════════════════════════════════════════════════════════════════

def deduplicate_against_climate_trace(gem_facilities):
    """Remove GEM facilities that are within 1km of an existing Climate TRACE facility in the same sector category."""
    # Load existing Climate TRACE data
    try:
        with open(CLIMATE_TRACE_FILE, 'r', encoding='utf-8') as f:
            ct_facilities = json.load(f)
    except FileNotFoundError:
        print("  [INFO] No Climate TRACE file found, skipping deduplication")
        return gem_facilities
    
    # Map GEM sectors to Climate TRACE sector keywords for matching
    SECTOR_MAP = {
        'Coal Mining': ['fossil', 'mining', 'coal'],
        'Coal Power': ['power', 'electricity'],
        'Solar Power': ['power', 'electricity'],
        'Oil & Gas Power': ['power', 'electricity', 'fossil', 'oil', 'gas'],
        'Bioenergy': ['power', 'electricity'],
        'Coal Logistics': ['fossil', 'coal'],
        'Oil & Gas Extraction': ['fossil', 'oil', 'gas'],
        'Cement': ['manufacturing', 'cement'],
        'Iron Ore Mining': ['mineral', 'mining', 'iron'],
        'Chemicals': ['manufacturing', 'chemical'],
    }
    
    kept = []
    duplicates = 0
    
    for gem_fac in gem_facilities:
        is_dup = False
        gem_sector_keywords = SECTOR_MAP.get(gem_fac['sector'], [])
        
        for ct_fac in ct_facilities:
            # Quick bounding box check (skip if > ~0.02 degrees apart ≈ ~2km)
            if (abs(gem_fac['lat'] - ct_fac['lat']) > 0.02 or 
                abs(gem_fac['lon'] - ct_fac['lon']) > 0.02):
                continue
            
            # Check sector similarity
            ct_sector_lower = (ct_fac.get('sector', '') + ' ' + ct_fac.get('subsector', '')).lower()
            sector_match = any(kw in ct_sector_lower for kw in gem_sector_keywords)
            
            if sector_match:
                dist = haversine_km(gem_fac['lat'], gem_fac['lon'], ct_fac['lat'], ct_fac['lon'])
                if dist < 1.0:  # Within 1km
                    is_dup = True
                    duplicates += 1
                    break
        
        if not is_dup:
            kept.append(gem_fac)
    
    print(f"\n  Deduplication: {duplicates} duplicates removed, {len(kept)} unique GEM facilities kept")
    return kept


# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════

def main():
    all_facilities = []
    
    processors = [
        ("Coal Mines",          process_coal_mines),
        ("Coal Plants",         process_coal_plants),
        ("Solar Power (>=50MW)", process_solar),
        ("Oil & Gas Plants",    process_oil_gas_plants),
        ("Bioenergy (>=10MW)",  process_bioenergy),
        ("Coal Terminals",      process_coal_terminals),
        ("Oil & Gas Extraction", process_oil_gas_extraction),
        ("Cement Plants",       process_cement),
        ("Iron Ore Mines",      process_iron_ore),
        ("Chemical Plants",     process_chemicals),
    ]
    
    for name, processor in processors:
        print(f"\n--- Processing: {name} ---")
        try:
            facilities = processor()
            all_facilities.extend(facilities)
            print(f"  -> {len(facilities)} facilities extracted")
        except Exception as e:
            print(f"  [ERROR] {name}: {e}")
    
    print(f"\n=== Total GEM facilities before dedup: {len(all_facilities)} ===")
    
    # Deduplicate within GEM data itself (same lat/lon within 0.5km)
    unique = []
    for fac in all_facilities:
        is_internal_dup = False
        for existing in unique:
            if (abs(fac['lat'] - existing['lat']) < 0.005 and 
                abs(fac['lon'] - existing['lon']) < 0.005 and
                fac['sector'] == existing['sector']):
                dist = haversine_km(fac['lat'], fac['lon'], existing['lat'], existing['lon'])
                if dist < 0.5:
                    is_internal_dup = True
                    break
        if not is_internal_dup:
            unique.append(fac)
    
    print(f"After internal dedup: {len(unique)} unique facilities")
    
    # Deduplicate against Climate TRACE
    final = deduplicate_against_climate_trace(unique)
    
    print(f"\n=== FINAL: {len(final)} GEM facilities for India ===")
    
    # Sector breakdown
    sector_counts = {}
    for f in final:
        sector_counts[f['sector']] = sector_counts.get(f['sector'], 0) + 1
    for sector, count in sorted(sector_counts.items(), key=lambda x: -x[1]):
        print(f"  {sector}: {count}")
    
    # Save
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved to: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
