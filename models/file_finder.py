import pandas as pd

# Load the metadata CSV
metadata_path = "gtopo30_metadata.csv"
df = pd.read_csv(metadata_path, encoding='latin1')
print(df.columns.tolist())

# City coordinates (lat, lon)
CITY_LOCATIONS = {
    "crescent_city_ca": (41.75, -124.2),
    "sendai_japan": (38.26, 140.87),
    "aceh_indonesia": (5.55, 95.32),
    "coquimbo_chile": (-29.95, -71.35),
    "kamchatka_russia": (53.05, 158.65), 
    "lemnos_greece": (39.88, 25.21),
    "cambridge_ma": (42.37, -71.11),
    "sydney_australia": (-33.87, 151.21),
    "rio_de_janeiro_brazil": (-22.90, -43.20),
    "singapore": (1.35, 103.82),
    "london_uk": (51.50, 0.12),
    "dubai_uae": (25.20, 55.27),
}

# Ensure only tiles with GeoTIFF available are considered
df = df[df['GEOTIFF Available'] == 'Y']

def city_in_tile(city_lat, city_lon, tile):
    """Check if city falls inside a tile bounding box"""
    nw_lat = tile['NW Corner Lat dec']
    nw_lon = tile['NW Corner Long dec']
    se_lat = tile['SE Corner Lat dec']
    se_lon = tile['SE Corner Long dec']
    
    # Correct for tiles crossing the anti-meridian
    if nw_lon > se_lon:
        inside_lon = (city_lon >= nw_lon) or (city_lon <= se_lon)
    else:
        inside_lon = (city_lon >= nw_lon) and (city_lon <= se_lon)
    
    inside_lat = (city_lat <= nw_lat) and (city_lat >= se_lat)
    
    return inside_lat and inside_lon

# Find tiles per city
tiles_to_download = {}

for city, (lat, lon) in CITY_LOCATIONS.items():
    # Correct filtering — pandas doesn’t understand `a <= x <= b` directly
    matching_tiles = df[
        (df['SE Corner Lat dec'] <= lat) & (df['NW Corner Lat dec'] >= lat) &
        (df['NW Corner Long dec'] <= lon) & (df['NE Corner Long dec'] >= lon)
    ]

    if not matching_tiles.empty:
        tiles_to_download[city] = matching_tiles['Entity ID'].tolist()
    else:
        print(f"⚠️ No tiles found for {city} at coordinates ({lat}, {lon})")
        tiles_to_download[city] = []


# Print results
for city, tiles in tiles_to_download.items():
    print(f"{city}: {tiles}")
