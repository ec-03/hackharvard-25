import geopandas as gpd

# 1️⃣ Load dataset directly from ThinkHazard
url = "https://thinkhazard.org/en/report/1690/TS.geojson"
gdf = gpd.read_file(url)

print("Original CRS:", gdf.crs)

# 2️⃣ Assign Web Mercator CRS if missing (EPSG:3857)
if gdf.crs is None:
    gdf = gdf.set_crs("EPSG:3857", allow_override=True)

# 3️⃣ Reproject to latitude/longitude (EPSG:4326)
gdf = gdf.to_crs("EPSG:4326")

# 4️⃣ Optional: simplify geometry for lighter web maps
gdf["geometry"] = gdf["geometry"].simplify(tolerance=0.0001, preserve_topology=True)

# 5️⃣ Export to GeoJSON
output_path = "tsunami_converted.geojson"
gdf.to_file(output_path, driver="GeoJSON")

print("✅ Converted GeoJSON saved as:", output_path)