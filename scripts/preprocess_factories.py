"""
Preprocesses Climate TRACE emissions CSV data for India.
Extracts unique factory/industry locations with their latest emissions data
and saves them to a consolidated JSON file for the Streamlit dashboard.
"""
import pandas as pd
import json
import os
import glob

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'raw_data', 'climate_trace', 'DATA')

# Define which sectors and their CSV patterns contain point-source industrial data
INDUSTRIAL_SECTORS = {
    "manufacturing": {
        "subsectors": [
            "cement", "aluminum", "chemicals", "iron-and-steel",
            "petrochemical-steam-cracking", "pulp-and-paper"
        ],
        "icon": "industry"
    },
    "power": {
        "subsectors": ["electricity-generation"],
        "icon": "bolt"
    },
    "fossil_fuel_operations": {
        "subsectors": [
            "coal-mining", "oil-and-gas-production",
            "oil-and-gas-refining", "oil-and-gas-transport"
        ],
        "icon": "fire"
    },
    "mineral_extraction": {
        "subsectors": ["bauxite-mining", "copper-mining", "iron-mining"],
        "icon": "gem"
    },
    "waste": {
        "subsectors": [
            "solid-waste-disposal",
            "industrial-wastewater-treatment-and-discharge"
        ],
        "icon": "trash"
    }
}

def process_sector(sector_name, sector_info):
    """Process all subsector CSVs for a given sector and return a list of facility records."""
    facilities = []
    sector_dir = os.path.join(DATA_DIR, sector_name)

    if not os.path.isdir(sector_dir):
        print(f"  [SKIP] Directory not found: {sector_dir}")
        return facilities

    for subsector in sector_info["subsectors"]:
        # Find the main emissions CSV (not confidence or ownership)
        pattern = os.path.join(sector_dir, f"{subsector}_emissions_sources_v*.csv")
        matches = glob.glob(pattern)

        if not matches:
            print(f"  [SKIP] No CSV found for {subsector}")
            continue

        csv_path = matches[0]
        print(f"  Processing: {os.path.basename(csv_path)}...")

        try:
            df = pd.read_csv(csv_path, low_memory=False)
        except Exception as e:
            print(f"  [ERROR] Failed to read {csv_path}: {e}")
            continue

        # Filter to only CO2 equivalent rows (or pm2_5 if available) to avoid duplicates
        # We want one row per facility with meaningful emissions data
        # Prefer co2e_100yr for total emissions, fallback to co2, then pm2_5
        for gas_priority in ['co2e_100yr', 'co2', 'pm2_5']:
            gas_df = df[df['gas'] == gas_priority]
            if len(gas_df) > 0:
                break
        else:
            gas_df = df  # fallback: use all

        if gas_df.empty:
            continue

        # Get the latest year's data for each facility
        if 'start_time' in gas_df.columns:
            gas_df = gas_df.copy()
            gas_df['year'] = pd.to_datetime(gas_df['start_time'], errors='coerce').dt.year
            # Keep only the latest year per source
            latest_year = gas_df.groupby('source_id')['year'].max().reset_index()
            gas_df = gas_df.merge(latest_year, on=['source_id', 'year'], how='inner')

        # Deduplicate by source_id, keeping the first (latest) row
        gas_df = gas_df.drop_duplicates(subset='source_id', keep='first')

        for _, row in gas_df.iterrows():
            lat = row.get('lat')
            lon = row.get('lon')

            # Skip rows without coordinates
            if pd.isna(lat) or pd.isna(lon):
                continue

            source_name = str(row.get('source_name', 'Unknown'))
            if source_name == 'nan' or not source_name.strip():
                source_name = 'Unknown Facility'

            source_type = str(row.get('source_type', ''))
            if source_type == 'nan':
                source_type = ''

            emissions = row.get('emissions_quantity')
            if pd.isna(emissions):
                emissions = None
            else:
                emissions = round(float(emissions), 2)

            capacity = row.get('capacity')
            if pd.isna(capacity):
                capacity = None
            else:
                try:
                    capacity = round(float(capacity), 2)
                except (ValueError, TypeError):
                    capacity = None

            capacity_units = str(row.get('capacity_units', ''))
            if capacity_units == 'nan':
                capacity_units = ''

            gas_type = str(row.get('gas', ''))

            facilities.append({
                'source_id': str(row.get('source_id', '')),
                'name': source_name,
                'type': source_type,
                'sector': sector_name.replace('_', ' ').title(),
                'subsector': subsector.replace('-', ' ').title(),
                'lat': float(lat),
                'lon': float(lon),
                'gas': gas_type,
                'emissions_tonnes': emissions,
                'capacity': capacity,
                'capacity_units': capacity_units,
                'icon': sector_info['icon']
            })

    return facilities


def main():
    all_facilities = []

    for sector_name, sector_info in INDUSTRIAL_SECTORS.items():
        print(f"\n--- Processing sector: {sector_name} ---")
        facilities = process_sector(sector_name, sector_info)
        all_facilities.extend(facilities)
        print(f"  Found {len(facilities)} facility records")

    # Deduplicate by source_id (a facility might appear in multiple gas rows)
    seen_ids = set()
    unique_facilities = []
    for f in all_facilities:
        if f['source_id'] not in seen_ids:
            seen_ids.add(f['source_id'])
            unique_facilities.append(f)

    print(f"\n=== Total unique facilities: {len(unique_facilities)} ===")

    output_path = os.path.join(PROJECT_ROOT, 'data', 'india_factories_data.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(unique_facilities, f, indent=2, ensure_ascii=False)

    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()
