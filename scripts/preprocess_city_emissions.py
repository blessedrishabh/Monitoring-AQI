"""
Preprocesses Climate TRACE area-level emissions data (transport, crop fires, buildings)
into a compact JSON keyed by normalized city name, for use in the AQI dashboard.
"""
import pandas as pd
import json
import os
import glob

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'raw_data', 'climate_trace', 'DATA')
OUTPUT_PATH = os.path.join(PROJECT_ROOT, 'data', 'city_emissions_data.json')


def normalize_city_name(source_name):
    """Strip common suffixes to get a clean city name for matching."""
    name = str(source_name).lower().strip()
    for suffix in [' urban area', ' rural area', ' metropolitan area']:
        name = name.replace(suffix, '')
    return name.strip()


def process_area_emissions(csv_path):
    """Read a Climate TRACE area-aggregated CSV and return {city: {total, monthly, ...}}."""
    print(f"  Reading {os.path.basename(csv_path)} ...")
    usecols = ['source_name', 'gas', 'emissions_quantity', 'start_time']
    df = pd.read_csv(csv_path, usecols=usecols, low_memory=False)

    df = df[df['gas'] == 'pm2_5'].copy()
    if df.empty:
        print("    No PM2.5 data found")
        return {}

    df['date'] = pd.to_datetime(df['start_time'], errors='coerce')
    df = df.dropna(subset=['date', 'emissions_quantity'])
    df['year'] = df['date'].dt.year
    df['month_key'] = df['date'].dt.strftime('%Y-%m')
    df['month_num'] = df['date'].dt.month

    latest_year = int(df['year'].max())
    df = df[df['year'] == latest_year]

    result = {}
    for source_name, grp in df.groupby('source_name'):
        city = normalize_city_name(source_name)
        total = float(grp['emissions_quantity'].sum())
        monthly = {}
        for month_key, mgrp in grp.groupby('month_key'):
            monthly[month_key] = round(float(mgrp['emissions_quantity'].sum()), 6)

        result[city] = {
            'total': round(total, 4),
            'monthly': monthly,
            'source_name': str(source_name),
            'year': latest_year
        }

    print(f"    {len(result)} areas extracted for year {latest_year}")
    return result


def main():
    city_emissions = {}

    # --- 1. Road Transportation ---
    print("\n=== Road Transportation ===")
    files = glob.glob(os.path.join(DATA_DIR, "transportation",
                                   "road-transportation_emissions_sources_v*.csv"))
    if files:
        data = process_area_emissions(files[0])
        for city, d in data.items():
            city_emissions.setdefault(city, {})['transport'] = d

    # --- 2. Cropland Fires ---
    print("\n=== Cropland Fires ===")
    files = glob.glob(os.path.join(DATA_DIR, "agriculture",
                                   "cropland-fires_emissions_sources_v*.csv"))
    if files:
        data = process_area_emissions(files[0])
        for city, d in data.items():
            city_emissions.setdefault(city, {})['crop_fires'] = d

    # --- 3. Buildings (residential + non-residential combined) ---
    print("\n=== Buildings ===")
    for pattern in ['residential-onsite-fuel-usage',
                    'non-residential-onsite-fuel-usage']:
        files = glob.glob(os.path.join(DATA_DIR, "buildings",
                                       f"{pattern}_emissions_sources_v*.csv"))
        if not files:
            continue
        data = process_area_emissions(files[0])
        for city, d in data.items():
            city_emissions.setdefault(city, {})
            if 'buildings' not in city_emissions[city]:
                city_emissions[city]['buildings'] = {
                    'total': 0, 'monthly': {},
                    'source_name': d['source_name'], 'year': d['year']
                }
            city_emissions[city]['buildings']['total'] = round(
                city_emissions[city]['buildings']['total'] + d['total'], 4)
            for mk, val in d['monthly'].items():
                prev = city_emissions[city]['buildings']['monthly'].get(mk, 0)
                city_emissions[city]['buildings']['monthly'][mk] = round(prev + val, 6)

    print(f"\n=== Total cities/areas with data: {len(city_emissions)} ===")

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(city_emissions, f, indent=2, ensure_ascii=False)
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
