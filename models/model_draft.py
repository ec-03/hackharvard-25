import geopandas as gpd
from shapely.geometry import shape

def predict_damage(flood_geojson, buildings_gdf, avg_value=80000, vuln=0.3, depth=None, severity='moderate'):
    flood_poly = shape(flood_geojson['features'][0]['geometry'])
    # intersect
    affected = buildings_gdf[buildings_gdf.intersects(flood_poly)]
    N = len(affected)
    depth_factor = 0.5
    if depth is not None:
        depth_factor = min(1.0, depth / 2.0)
    else:
        severity_map = {'minor':0.2, 'moderate':0.5, 'severe':0.9}
        depth_factor = severity_map.get(severity)
    damage_per_building = avg_value * depth_factor * vuln
    total_damage = N * damage_per_building
    return {
       "buildings_affected": N,
       "total_damage_usd": total_damage,
       "model_version": "v0.1-rulebase"
    }
    
#testing
def main():
    # example: square
    flood_geojson = {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "properties": {},
          "geometry": {
            "type": "Polygon",
            "coordinates": [
              [
                [-122.42305755615234, 37.77825932800253],
                [-122.4127197265625, 37.77825932800253],
                [-122.4127197265625, 37.78661798334754],
                [-122.42305755615234, 37.78661798334754],
                [-122.42305755615234, 37.77825932800253]
              ]
            ]
          }
        }
      ]
    }
    buildings_data = {
        'geometry': [
            shape({"type": "Point", "coordinates": [-122.4194, 37.7749]}),  # San Francisco
            shape({"type": "Point", "coordinates": [-122.414, 37.779]}),   # Inside flood
            shape({"type": "Point", "coordinates": [-122.410, 37.780]}),   # Inside flood
            shape({"type": "Point", "coordinates": [-122.430, 37.770]})    # Outside flood
        ]
    }
    buildings_gdf = gpd.GeoDataFrame(buildings_data, crs="EPSG:4326")
    
    type_map = {1: 'minor', 2: 'moderate', 3: 'severe'}
    severity = type_map[int(input("Enter flood severity (1: light, 2: moderate, 3: severe): "))]
    result = predict_damage(flood_geojson, buildings_gdf, avg_value=100000, vuln=0.4, severity=severity)
    print(result)

main()
