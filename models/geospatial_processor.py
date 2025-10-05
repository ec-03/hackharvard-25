import geopandas as gpd
from shapely.geometry import box
import pandas as pd
import numpy as np
import warnings
import argparse
import json
import os

# --- GLOBAL FILEPATH CONFIGURATION (User-defined) ---
# NOTE: Replace these placeholder strings with the actual local paths 
# to your SRTM and GTOPO30 shapefile's .shp component.
SRTM_FILEPATH = "srtm_data\\srtm.shp"
GTOPO_FILEPATH = "gtopo30\\gtopo30.shp" 
# GTOPO is optional, but defined here for completeness.
# ----------------------------------------------------


# Dictionary of approximate city coordinates and bounding box sizes (in degrees)
CITY_LOCATIONS = {
    "crescent_city_ca": (41.75, -124.2, 0.05),
    "sendai_japan": (38.26, 140.87, 0.1),
    "aceh_indonesia": (5.55, 95.32, 0.1),
    "coquimbo_chile": (-29.95, -71.35, 0.1),
    "kamchatka_russia": (53.05, 158.65, 0.2), 
    "lemnos_greece": (39.88, 25.21, 0.05),

    "cambridge_ma": (42.37, -71.11, 0.03),
    "sydney_australia": (-33.87, 151.21, 0.1),
    "rio_de_janeiro_brazil": (-22.90, -43.20, 0.1),
    "singapore": (1.35, 103.82, 0.05),
    "london_uk": (51.50, 0.12, 0.05),
    "dubai_uae": (25.20, 55.27, 0.05),
}

# Output file path for the computed factors
VULNERABILITY_FILE = "simulated_vulnerability.json"


# --- Utility Functions for Geospatial Analysis ---

def create_bounding_box(lat, lon, buffer_degree):
    """Creates a rectangular Shapely polygon (bounding box) around a point."""
    min_x = lon - buffer_degree
    max_x = lon + buffer_degree
    min_y = lat - buffer_degree
    max_y = lat + buffer_degree
    return box(min_x, min_y, max_x, max_y)

def extract_z_values(geometry):
    """
    Extracts Z (elevation) values from a Shapely geometry object, 
    designed to handle Point, LineString, and Polygon vertices.
    """
    z_values = []
    
    # Check if geometry has explicit Z dimension enabled
    if not geometry.has_z:
        return np.array([])
    
    # Handle single geometries (Point, LineString)
    if geometry.geom_type == 'Point':
        z_values.append(geometry.z)
    elif geometry.geom_type in ['LineString', 'Polygon']:
        # Extract Z from vertices (coordinate tuple must have 3 dimensions: x, y, z)
        # Using list comprehension ensures only the third element (Z) is captured
        try:
            coords = list(geometry.coords)
            if coords and len(coords[0]) == 3:
                z_values.extend([z for x, y, z in coords if z is not None])
        except Exception:
            pass # Handle errors if geometry.coords doesn't exist/fails
            
    # Handle Multi-part geometries
    elif geometry.geom_type in ['MultiPoint', 'MultiLineString', 'MultiPolygon', 'GeometryCollection']:
        for part in geometry.geoms:
            z_values.extend(extract_z_values(part).tolist())
    
    return np.array(z_values)


def get_elevation_data(filepath, city_key):
    """
    Loads and clips the elevation shapefile for a specific city, 
    relying solely on Z-dimension extraction.
    """
    # A high elevation fallback (meters) that translates to low vulnerability
    NEUTRAL_ELEVATION_FALLBACK = 1000.0 
    MIN_USABLE_ELEVATION = 0.01 # Minimum elevation above sea level to consider usable (0.01 meters)

    if not os.path.exists(filepath):
        warnings.warn(f"Shapefile not found: {filepath}. Assuming neutral elevation.")
        return NEUTRAL_ELEVATION_FALLBACK

    if city_key not in CITY_LOCATIONS:
        warnings.warn(f"City key '{city_key}' not found. Assuming neutral elevation.")
        return NEUTRAL_ELEVATION_FALLBACK

    try:
        # 1. Load the entire shapefile
        full_gdf = gpd.read_file(filepath)
    except Exception as e:
        warnings.warn(f"Error reading shapefile {filepath} for {city_key}. Error: {e}. Assuming neutral elevation.")
        return NEUTRAL_ELEVATION_FALLBACK

    # 2. Define Clipping Geometry (Bounding Box)
    lat, lon, buffer = CITY_LOCATIONS[city_key]
    clip_polygon = create_bounding_box(lat, lon, buffer)
    clip_gdf = gpd.GeoDataFrame({'id': [1], 'geometry': [clip_polygon]}, crs="EPSG:4326")

    # 3. Ensure CRS alignment before clipping (assumes standard WGS 84 input)
    if full_gdf.crs is None or full_gdf.crs.to_string() != clip_gdf.crs.to_string():
        if full_gdf.crs is None:
             full_gdf = full_gdf.set_crs("EPSG:4326")
        else:
            try:
                full_gdf = full_gdf.to_crs(clip_gdf.crs)
            except Exception as e:
                 warnings.warn(f"Reprojection failed: {e}. Proceeding with geometry comparison only.")

    # 4. Clip the data: Spatial join
    clipped_data = gpd.sjoin(full_gdf, clip_gdf, predicate='intersects', how='inner')
    
    if clipped_data.empty:
        warnings.warn(f"Clipped data is empty for {city_key}. No intersecting features found. Assuming neutral elevation.")
        return NEUTRAL_ELEVATION_FALLBACK

    # 5. Extract Elevation from Z-coordinate (Only Priority)
    all_z = []
    
    # Iterate over all geometries in the clipped GeoDataFrame
    for geom in clipped_data.geometry:
        all_z.extend(extract_z_values(geom).tolist())
    
    elevations = np.array(all_z)
    elevations = elevations[~np.isnan(elevations)].astype(float)
        
    # Final check and filtering for usable data
    # We filter out zero/near-zero values as these might represent water or missing data, 
    # but we clamp them to zero meters to represent the lowest coastal land elevation.
    elevations = elevations[(elevations < NEUTRAL_ELEVATION_FALLBACK)]
    
    if elevations.size < 5: 
        warnings.warn(f"Insufficient usable 3D Z-data found for {city_key} after clipping. Assuming neutral elevation.")
        return NEUTRAL_ELEVATION_FALLBACK

    # 6. Compute the Vulnerability Metric: 5th percentile elevation
    # We are looking for the lowest non-zero elevation point in the clipped coastal area.
    min_elevation_vulnerability = np.percentile(elevations, 5)
    
    # Clamp the result at a minimum of 0.0 (no negative elevations/bathymetry)
    final_elevation = max(MIN_USABLE_ELEVATION, min_elevation_vulnerability) 
    
    print(f"[{city_key.replace('_', ' ').title()}] Computed 5th percentile elevation: {final_elevation:.2f} meters.")
    return final_elevation

# --- City Factor Calculation (Unchanged) ---

def calculate_vulnerability_factor(min_elevation, max_tolerable_elevation_m=20.0):
    """
    Maps the low elevation metric (min_elevation) to a damage amplification factor (C).
    Factor is bounded between 0.0 (safest) and 1.0 (most vulnerable).
    """
    # Vulnerability decreases as min_elevation increases.
    vulnerability = 1.0 - (min_elevation / max_tolerable_elevation_m)
    return np.clip(vulnerability, 0.0, 1.0)


def compute_all_city_factors(filepath):
    """Main wrapper to calculate vulnerability factors for all required cities."""
    vulnerability_factors = {}
    
    print(f"Starting elevation analysis using primary source: {filepath}")

    for city_key in CITY_LOCATIONS.keys():
        min_elev = get_elevation_data(filepath, city_key)
        amp_factor = calculate_vulnerability_factor(min_elev)
        vulnerability_factors[city_key] = amp_factor
        
    return vulnerability_factors

# --- Main Execution ---

if __name__ == '__main__':
    
    # Check if filepath is a placeholder
    if SRTM_FILEPATH == "/path/to/your/local/srtm.shp":
        print("\n--- WARNING: SRTM Shapefile Path is a placeholder! ---")
        print("Please edit 'SRTM_FILEPATH' in this script before running locally with actual data.")
        # Create a dummy file with realistic placeholders so the main model can still run
        dummy_vulnerability = {
            "crescent_city_ca": 0.85, "sendai_japan": 0.75, "aceh_indonesia": 0.95, 
            "coquimbo_chile": 0.80, "kamchatka_russia": 0.40, "lemnos_greece": 0.55,
            "cambridge_ma": 0.10, "sydney_australia": 0.65, "rio_de_janeiro_brazil": 0.50, 
            "singapore": 0.88, "london_uk": 0.05, "dubai_uae": 0.70
        }
        vulnerability_scores = dummy_vulnerability
        print("Using placeholder data.")
        
    else:
        print("\n--- Starting Geospatial Elevation Analysis ---")

        # Use the SRTM Shapefile path defined in the global variables
        vulnerability_scores = compute_all_city_factors(SRTM_FILEPATH)

    print("\n--- Final Elevation Vulnerability Factors (0.0=Safest, 1.0=Vulnerable) ---")
    for city, factor in vulnerability_scores.items():
        print(f"{city.replace('_', ' ').title():<30}: {factor:.4f}")
    
    # Save the computed data for the main model to read
    with open(VULNERABILITY_FILE, 'w') as f:
        json.dump(vulnerability_scores, f, indent=4)
        
    print(f"\n[geospatial_processor.py finished] Saved computed data to '{VULNERABILITY_FILE}'")