from flask import Flask, jsonify
from flask_cors import CORS
import csv
from io import StringIO
from functools import lru_cache
import urllib.request
import urllib.error

app = Flask(__name__)
CORS(app)

@app.route("/api/hello")
def hello():
    return jsonify(message="Hello from Flask!")

# Raw CSV listing ADM1 codes/names from GFDRR (used by thinkhazard)
ADM1_CSV_URL = "https://raw.githubusercontent.com/GFDRR/thinkhazardmethods/master/source/download/ADM1_TH.csv"

@lru_cache(maxsize=1)
def load_adm1_mapping():
    """Fetch the ADM1 CSV and return a dict mapping lowercase name -> ADM1_CODE (as string)."""
    try:
        with urllib.request.urlopen(ADM1_CSV_URL, timeout=10) as resp:
            raw = resp.read()
            text = raw.decode("utf-8")
        # CSV uses semicolon delimiter
        reader = csv.DictReader(StringIO(text), fieldnames=["ADM1_CODE", "ADM1_NAME", "ADM0_CODE", "ADM0_NAME"], delimiter=";")
        mapping = {}
        for row in reader:
            # Skip header if present
            if row["ADM1_CODE"] == "ADM1_CODE":
                continue
            code = row["ADM1_CODE"].strip()
            name = row["ADM1_NAME"] or ""
            name = name.strip()
            if not code or not name:
                continue
            mapping[name.lower()] = code
        return mapping
    except Exception as e:
        app.logger.error("failed to load ADM1 CSV: %s", e)
        return {}


@app.route("/api/thinkhazard/<city>")
def thinkhazard_city_geojson(city):
    """Return the TS.geojson for the given city name by looking up its ADM1 code.

    Example: /api/thinkhazard/tokyo -> proxies https://thinkhazard.org/en/report/1690/TS.geojson
    """
    mapping = load_adm1_mapping()
    if not mapping:
        return jsonify(error="ADM1 mapping not available"), 500

    key = city.replace("-", " ").strip().lower()
    code = mapping.get(key)
    # Try a looser match: exact capitalizations or removing diacritics could be added later
    if not code:
        # try title-case matching against keys
        for name, c in mapping.items():
            if name.lower() == key:
                code = c
                break
    if not code:
        return jsonify(error="city not found", city=city), 404

    geojson_url = f"https://thinkhazard.org/en/report/{code}/TS.geojson"
    try:
        with urllib.request.urlopen(geojson_url, timeout=10) as resp:
            content = resp.read()
            status = resp.getcode() if hasattr(resp, "getcode") else 200
            return (content, status, {"Content-Type": "application/json"})
    except urllib.error.HTTPError as he:
        app.logger.error("thinkhazard fetch failed: %s", he)
        return jsonify(error="failed to fetch geojson", detail=str(he)), 502
    except Exception as e:
        app.logger.error("unexpected error fetching geojson: %s", e)
        return jsonify(error="unexpected error", detail=str(e)), 500


if __name__ == "__main__":
    app.run(port=5001, debug=True)
