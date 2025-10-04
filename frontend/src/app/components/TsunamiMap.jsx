"use client";
import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

function looksLike3857(geojson) {
  try {
    const sample = (function findCoords(obj) {
      if (!obj) return null;
      if (Array.isArray(obj) && typeof obj[0] === "number") return obj;
      if (obj.type === "FeatureCollection" && Array.isArray(obj.features) && obj.features.length)
        return findCoords(obj.features[0].geometry);
      if (obj.type === "Feature") return findCoords(obj.geometry);
      if (obj.coordinates) return findCoords(obj.coordinates);
      if (Array.isArray(obj)) return findCoords(obj[0]);
      return null;
    })(geojson);
    if (!sample) return false;
    const x = Math.abs(sample[0]);
    const y = Math.abs(sample[1]);
    return x > 180 || y > 90;
  } catch (e) {
    return false;
  }
}

function reproject3857To4326(x, y) {
  const R = 6378137.0;
  const lon = (x / R) * (180 / Math.PI);
  const lat = (2 * Math.atan(Math.exp(y / R)) - Math.PI / 2) * (180 / Math.PI);
  return [lon, lat];
}

function reprojectCoords(coords) {
  if (!Array.isArray(coords)) return coords;
  if (typeof coords[0] === "number" && typeof coords[1] === "number") return reproject3857To4326(coords[0], coords[1]);
  return coords.map(reprojectCoords);
}

// Default to backend proxy endpoint for thinkhazard Tokyo report when no url provided
const DEFAULT_THINKHAZARD_TOKYO = "http://localhost:5001/api/thinkhazard/tokyo";

export default function TsunamiMap({ url = DEFAULT_THINKHAZARD_TOKYO, center, zoom, autoFit = true }) {
  const mapContainer = useRef(null);
  const mapRef = useRef(null);

  useEffect(() => {
    if (mapRef.current || !mapContainer.current) return;

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        // MapLibre expects a "sources" object in the style even if we'll add sources dynamically later
        sources: {},
        layers: [
          { id: "background", type: "background", paint: { "background-color": "#ffffff" } },
        ],
      },
      center: center || [139.6917, 35.6895],
      zoom: zoom || 8,
      attributionControl: false,
      // make sure interactions are enabled explicitly
      interactive: true,
    });

    mapRef.current = map;

    map.on("load", async () => {
      try {
        const res = await fetch(url);
        const geojson = await res.json();

        let data = geojson;
        if (looksLike3857(geojson)) {
          // deep clone
          const clone = JSON.parse(JSON.stringify(geojson));
          const reprojectGeometry = (geometry) => {
            if (!geometry) return geometry;
            const g = { ...geometry };
            if (g.type === "GeometryCollection" && Array.isArray(g.geometries)) {
              g.geometries = g.geometries.map(reprojectGeometry);
            } else if (g.coordinates) {
              g.coordinates = reprojectCoords(g.coordinates);
            }
            return g;
          };

          if (clone.type === "FeatureCollection") {
            clone.features = clone.features.map((f) => ({ ...f, geometry: reprojectGeometry(f.geometry) }));
          } else if (clone.type === "Feature") {
            clone.geometry = reprojectGeometry(clone.geometry);
          } else if (clone.type && clone.coordinates) {
            const newGeom = reprojectGeometry(clone);
            Object.assign(clone, newGeom);
          }
          data = clone;
        }

        if (map.getSource("tsunami")) {
          map.getSource("tsunami").setData(data);
        } else {
          map.addSource("tsunami", { type: "geojson", data });
          // use more visible colors for small preview and ensure layers render
          map.addLayer({ id: "tsunami-fill", type: "fill", source: "tsunami", paint: { "fill-color": "#ff7f50", "fill-opacity": 0.6 } });
          map.addLayer({ id: "tsunami-line", type: "line", source: "tsunami", paint: { "line-color": "#cc3b00", "line-width": 1.5 } });
        }

        // ensure the map layout is updated for the container and enable interactions
        try {
          map.resize();
        } catch (e) {
          // ignore resize errors in small previews
        }
        // explicitly enable common interaction handlers
        try {
          if (map.dragPan) map.dragPan.enable();
          if (map.scrollZoom) map.scrollZoom.enable();
          if (map.doubleClickZoom) map.doubleClickZoom.enable();
          if (map.touchZoomRotate) map.touchZoomRotate.enable();
        } catch (e) {
          // some environments may not expose these controls in the same way; ignore
        }

        // give a draggable cursor affordance
        try {
          const canvas = map.getCanvas && map.getCanvas();
          if (canvas) canvas.style.cursor = "grab";
          map.on("mousedown", () => { if (canvas) canvas.style.cursor = "grabbing"; });
          map.on("mouseup", () => { if (canvas) canvas.style.cursor = "grab"; });
        } catch (e) {
          // ignore
        }

  // Focus to data if no explicit center/zoom provided and autoFit is enabled
  if (autoFit && !center && data) {
          // Recursively collect coordinate pairs from various geometry types
          const coords = [];
          const collectCoords = (g) => {
            if (!g) return;
            const t = g.type;
            if (t === "Point") {
              coords.push(g.coordinates);
            } else if (t === "MultiPoint" || t === "LineString") {
              (g.coordinates || []).forEach((c) => coords.push(c));
            } else if (t === "MultiLineString" || t === "Polygon") {
              (g.coordinates || []).forEach((ring) => {
                // polygon: ring is an array of positions
                if (Array.isArray(ring) && Array.isArray(ring[0])) ring.forEach((c) => coords.push(c));
              });
            } else if (t === "MultiPolygon") {
              (g.coordinates || []).forEach((poly) => poly.forEach((ring) => ring.forEach((c) => coords.push(c))));
            } else if (t === "GeometryCollection") {
              (g.geometries || []).forEach((gg) => collectCoords(gg));
            } else if (Array.isArray(g)) {
              // fallback: array of coords
              g.forEach((item) => collectCoords(item));
            }
          };

          if (data.type === "FeatureCollection") data.features.forEach((f) => collectCoords(f.geometry || f));
          else if (data.type === "Feature") collectCoords(data.geometry || data);
          else collectCoords(data);

          const bboxIsValid = (minLon, minLat, maxLon, maxLat) => {
            if (typeof minLon !== "number" || typeof minLat !== "number" || typeof maxLon !== "number" || typeof maxLat !== "number") return false;
            if (!(minLon < maxLon && minLat < maxLat)) return false;
            // Web Mercator valid lon/lat ranges
            if (minLon < -180 || maxLon > 180) return false;
            if (minLat < -85 || maxLat > 85) return false;
            return true;
          };

          const computeAndMaybeFit = (coordsArray) => {
            if (!coordsArray || !coordsArray.length) return false;
            const lons = coordsArray.map((c) => c[0]);
            const lats = coordsArray.map((c) => c[1]);
            const minLon = Math.min(...lons);
            const maxLon = Math.max(...lons);
            const minLat = Math.min(...lats);
            const maxLat = Math.max(...lats);
            if (bboxIsValid(minLon, minLat, maxLon, maxLat)) {
              const sw = [minLon, minLat];
              const ne = [maxLon, maxLat];
              map.fitBounds([sw, ne], { padding: 40, maxZoom: 12 });
              return true;
            }
            return false;
          };

          let fitted = computeAndMaybeFit(coords);

          // If the bbox wasn't valid, attempt a forced reprojection (in case detection missed EPSG:3857)
          if (!fitted) {
            try {
              // make a deep clone and attempt to reproject any numeric coordinate pairs
              const forced = JSON.parse(JSON.stringify(data));
              const forceReproject = (g) => {
                if (!g) return g;
                if (g.type === "GeometryCollection" && Array.isArray(g.geometries)) {
                  g.geometries = g.geometries.map(forceReproject);
                } else if (g.coordinates) {
                  const mapCoords = (c) => {
                    if (!Array.isArray(c)) return c;
                    if (typeof c[0] === "number" && typeof c[1] === "number") {
                      return reproject3857To4326(c[0], c[1]);
                    }
                    return c.map(mapCoords);
                  };
                  g.coordinates = mapCoords(g.coordinates);
                }
                return g;
              };

              if (forced.type === "FeatureCollection") {
                forced.features = forced.features.map((f) => ({ ...f, geometry: forceReproject(f.geometry) }));
              } else if (forced.type === "Feature") {
                forced.geometry = forceReproject(forced.geometry);
              } else {
                forceReproject(forced);
              }

              const forcedCoords = [];
              if (forced.type === "FeatureCollection") forced.features.forEach((f) => collectCoords(f.geometry || f));
              else if (forced.type === "Feature") collectCoords(forced.geometry || forced);
              else collectCoords(forced);

              // try fitting with forced reprojection coords
              fitted = computeAndMaybeFit(forcedCoords);
              if (fitted) {
                // update source data to the reprojected version so rendering matches bounds
                if (map.getSource("tsunami")) map.getSource("tsunami").setData(forced);
              }
            } catch (e) {
              // if forced reprojection fails, don't crash — leave the default center/zoom
              // and log for debugging
              // console.warn('forced reprojection failed', e);
            }
          }
        }
      } catch (e) {
        console.error("failed to load/convert geojson", e);
      }
    });

    return () => map.remove();
  }, [url, center, zoom]);

  return <div ref={mapContainer} className="w-full h-full" />;
}
