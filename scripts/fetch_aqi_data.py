import requests
import time
import json
import os
import reverse_geocoder as rg

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_ROOT, 'data', 'india_aqi_data.json')
header = {
    "X-Api-Key": "93d3805b2b193781a05a91c0a8184891ff35d0bcce4b710a6b6df6d4a1b15c0c"
}
def get_india_location_ids():
    url = "https://api.openaq.org/v3/locations"

    india_location_ids = []
    page = 1
    has_more_pages = True

    while has_more_pages:
        params = {
            "countries_id": 9,
            "limit":1000,
            "page":page
        }
        response = requests.get(url, params=params, headers=header)
        # Handle API rate limits gracefully
        if response.status_code == 429:
            print("Rate limit reached. Sleeping for 60 seconds...")
            time.sleep(60)
            continue
        data = response.json()
        results = data.get('results', [])
        if not results:
            has_more_pages = False
            break
        # Extract the unique 'id' for each location and add it to our list
        for location in results:
            india_location_ids.append(location['id'])
        page = page+1
        time.sleep(1)

    return india_location_ids

# The piecewise linear function to calculate the sub-index
def calculate_sub_index(c_p, bp_lo, bp_hi, i_lo, i_hi):
    """
    c_p: Concentration of pollutant
    bp_lo, bp_hi: Breakpoint low and high
    i_lo, i_hi: AQI Index low and high
    """
    aqi_p = ((i_hi - i_lo) / (bp_hi - bp_lo)) * (c_p - bp_lo) + i_lo
    return round(aqi_p)

# Example helper function for PM2.5 using India's breakpoints
def get_pm25_sub_index(c_p):
    if 0 <= c_p <= 30:
        return calculate_sub_index(c_p, 0, 30, 0, 50)       # Good
    elif 31 <= c_p <= 60:
        return calculate_sub_index(c_p, 31, 60, 51, 100)    # Satisfactory
    elif 61 <= c_p <= 90:
        return calculate_sub_index(c_p, 61, 90, 101, 200)   # Moderately Polluted
    elif 91 <= c_p <= 120:
        return calculate_sub_index(c_p, 91, 120, 201, 300)  # Poor
    elif 121 <= c_p <= 250:
        return calculate_sub_index(c_p, 121, 250, 301, 400) # Very Poor
    elif c_p > 250:
        return calculate_sub_index(c_p, 250, 1000, 401, 500)# Severe (using 1000 as arbitrary high)
    return None

def get_aqi_category(aqi):
    if aqi is None:
        return "Unknown"
    if 0 <= aqi <= 50:
        return "Good"
    elif 51 <= aqi <= 100:
        return "Satisfactory"
    elif 101 <= aqi <= 200:
        return "Moderately Polluted"
    elif 201 <= aqi <= 300:
        return "Poor"
    elif 301 <= aqi <= 400:
        return "Very Poor"
    elif aqi > 400:
        return "Severe"
    return "Unknown"



def fetch_bulk_pm25_data(india_location_ids):
    # Parameter ID 2 is PM2.5
    url = "https://api.openaq.org/v3/parameters/2/latest"
    
    page = 1
    has_more_pages = True
    india_aqi_results = {}

    while has_more_pages:
        params = {
            "limit": 1000, # API constraint: Maximum 1,000 results per page
            "page": page
        }
        
        response = requests.get(url, headers=header, params=params)
        
        # Handle rate limiting (HTTP 429) gracefully
        if response.status_code == 429:
            print("Rate limit reached. Sleeping for 60 seconds...")
            time.sleep(60)
            continue
            
        data = response.json()
        results = data.get('results', [])
        
        if not results:
            has_more_pages = False
            break
            
        for item in results:
            loc_id = item['locationsId']
            
            # Check if this data point belongs to one of our India locations
            if loc_id in india_location_ids:
                concentration = item['value']
                # Calculate the sub-index using our piecewise function
                pm25_aqi = get_pm25_sub_index(concentration)
                category = get_aqi_category(pm25_aqi)
                
                coords = item.get('coordinates') or {}
                lat = coords.get('latitude')
                lon = coords.get('longitude')
                
                india_aqi_results[loc_id] = {
                    'city': "Pending",
                    'state': "Pending",
                    'area': "Pending",
                    'longitude': lon,
                    'latitude': lat,
                    'pm_value_used': concentration,
                    'aqi': pm25_aqi,
                    'category': category
                }

        page += 1
        
        # Adding a small sleep between pages is good practice to avoid hitting rate limits
        time.sleep(1) 

    # Bulk resolve city, state, and area using offline reverse geocoder
    loc_ids = list(india_aqi_results.keys())
    coords = []
    valid_indices = []
    
    for i, lid in enumerate(loc_ids):
        lat = india_aqi_results[lid]['latitude']
        lon = india_aqi_results[lid]['longitude']
        if lat is not None and lon is not None:
            coords.append((lat, lon))
            valid_indices.append(i)
            
    if coords:
        rg_results = rg.search(coords)
        for idx, rg_res in enumerate(rg_results):
            original_i = valid_indices[idx]
            lid = loc_ids[original_i]
            india_aqi_results[lid]['city'] = rg_res.get('name', 'Unknown')
            india_aqi_results[lid]['state'] = rg_res.get('admin1', 'Unknown')
            india_aqi_results[lid]['area'] = rg_res.get('admin2', 'Unknown')

    return india_aqi_results

my_india_locations = get_india_location_ids()
aqi_data = fetch_bulk_pm25_data(my_india_locations)

with open(OUTPUT_PATH, "w") as f:
    json.dump(aqi_data, f, indent=4)

print(f"Data successfully saved to {OUTPUT_PATH}")