import pandas as pd
import numpy as np
import argparse
import os
import math
import matplotlib.pyplot as plt
import folium
from folium.plugins import MarkerCluster
import json

# --- CONFIG / DEFAULTS ---
DEFAULT_INPUT = "world_tsunamis.csv"
VULNERABILITY_FILE = "simulated_vulnerability.json" # Input from geospatial_processor.py

DEFAULT_WEIGHTS = {
    "magnitude": 0.2, 
    "max_height": 0.2,
    "runups": 0.2,
    "deposits": 0.2,
    "city_amp": 0.2 # NEW: Weight for city-specific amplification factor
}

CITY_COORDS = {
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
# Map common names to keys used in the vulnerability JSON
CITY_NAME_TO_KEY = {
    "crescent city, ca": "crescent_city_ca",
    "sendai, japan": "sendai_japan",
    "aceh, indonesia": "aceh_indonesia",
    "coquimbo, chile": "coquimbo_chile",
    "kamchatka province, russia": "kamchatka_russia",
    "lemnos island, greece": "lemnos_greece",
    "cambridge, ma": "cambridge_ma",
    "sydney, australia": "sydney_australia",
    "rio de janeiro, brazil": "rio_de_janeiro_brazil",
    "singapore": "singapore",
    "london, uk": "london_uk",
    "dubai, uae": "dubai_uae",
}


# --- UTILITY FUNCTIONS ---

def load_vulnerability_data(path):
    """Loads the city vulnerability factors from the pre-computed JSON file."""
    if not os.path.exists(path):
        print(f"WARNING: Vulnerability data not found at {path}. Using neutral factor (1.0) for all cities.")
        return {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"ERROR reading vulnerability data: {e}. Using neutral factor (1.0).")
        return {}

def load_data(path=DEFAULT_INPUT):
    # (Unchanged load_data function)
    print("Loading data...")
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found: {path}")
    df = pd.read_csv(path)
    print("Data loaded. Rows:", len(df))
    return df

def normalize_series(s):
    # (Unchanged normalize_series function)
    if s.max() == s.min():
        return np.zeros_like(s, dtype=float)
    return (s - s.min()) / (s.max() - s.min())

# MODIFIED: Added city_amp_col to scoring
def compute_damage_score(df, weights=None,
                         mag_col="Earthquake Magnitude",
                         height_col="Maximum Water Height (m)",
                         runups_col="Number of Runups",
                         deposits_col="Deposits",
                         city_amp_col="City Factor"):
    if weights is None:
        weights = DEFAULT_WEIGHTS

    required_cols = [mag_col, height_col, runups_col, deposits_col]
    for col in required_cols:
        if col not in df.columns:
            raise KeyError(f"Missing required column in data: {col}")

    df = df.copy()
    
    # 1. Handle missing City Factor column (e.g., in historical data)
    if city_amp_col not in df.columns:
        # For historical data, set factor to 0 (since it shouldn't apply to global events)
        df[city_amp_col] = 0.0
        
    # 2. Normalize hazard features
    df["_mag_n"] = normalize_series(df[mag_col].astype(float))
    df["_h_n"] = normalize_series(df[height_col].astype(float))
    df["_r_n"] = normalize_series(df[runups_col].astype(float))
    df["_d_n"] = normalize_series(df[deposits_col].astype(float))
    
    # 3. Normalize the City Factor (If all values are 0.0, normalization returns 0.0, which is fine)
    df["_city_n"] = normalize_series(df[city_amp_col].astype(float))

    # 4. Compute composite score (Weight sum is assumed to be 1.0 or weights will be renormalized in post-processing)
    score = (
        weights.get("magnitude", 0.0) * df["_mag_n"] +
        weights.get("max_height", 0.0) * df["_h_n"] +
        weights.get("runups", 0.0) * df["_r_n"] +
        weights.get("deposits", 0.0) * df["_d_n"] +
        weights.get("city_amp", 0.0) * df["_city_n"] # NEW: Include weighted city factor
    )
    
    # Normalize weights to sum to 1 if they don't, to ensure score is 0-1
    total_w = sum(weights.values())
    if total_w > 0:
        score = score / total_w
    
    score = np.clip(score, 0.0, 1.0)
    
    df["Damage Score"] = score
    # Remove aux cols
    aux_cols = ["_mag_n","_h_n","_r_n","_d_n", "_city_n"]
    df = df.drop(columns=aux_cols, errors='ignore')
    return df

# MODIFIED: Added city_amp_factor argument
def scenario_from_user_inputs(magnitude, max_height, runups, deposits, city_amp_factor, df_template):
    # (Updated scenario_from_user_inputs function)
    mag_col = "Earthquake Magnitude"
    height_col = "Maximum Water Height (m)"
    runups_col = "Number of Runups"
    deposits_col = "Deposits"
    city_amp_col = "City Factor" 

    newrow = {
        mag_col: magnitude, 
        height_col: max_height, 
        runups_col: runups, 
        deposits_col: deposits,
        city_amp_col: city_amp_factor
    }
    
    cols_to_keep = [mag_col, height_col, runups_col, deposits_col]
    if city_amp_col in df_template.columns:
        cols_to_keep.append(city_amp_col)
    
    df_temp = df_template[cols_to_keep].copy()
    newrow_df = pd.DataFrame([newrow])
    df_temp = pd.concat([df_temp, newrow_df], ignore_index=True)
    return df_temp, len(df_temp) - 1 

def estimate_loss_from_score(score, total_exposed_value_usd, calibration_factor=1.0):
    # (Unchanged estimate_loss_from_score function)
    loss = float(score) * float(total_exposed_value_usd) * float(calibration_factor)
    return loss

# (Functions: compute_calibration_factor_from_loss, compute_adjusted_weights_from_example, 
# save_summary_csv, plot_histogram_scores, plot_top_locations, create_folium_map, 
# _find_lat_lon_cols, _haversine_km, find_nearest_location, find_location_by_name are omitted for brevity)

# --- LOCATION FOCUSED REPORT (Copied from original) ---
def generate_location_report(args, df_scores, weights, vulnerability_factors):
    """Given args with city name, produce a human-readable report."""
    lat_col, lon_col = _find_lat_lon_cols(df_scores)
    
    # 1. Determine City Factor
    city_key = CITY_NAME_TO_KEY.get(args.location_name.lower())
    if city_key and city_key in vulnerability_factors:
        city_amp_factor = vulnerability_factors[city_key]
        print(f"Using Elevation Vulnerability Factor for {args.location_name}: {city_amp_factor:.4f}")
    else:
        city_amp_factor = 0.0 # Neutral or lowest factor if not found in geospatial data
        print(f"Warning: City '{args.location_name}' not found in vulnerability data. Using neutral factor (0.0).")

    # 2. Prepare the synthetic scenario based on hazard inputs and the derived City Factor
    df_template = df_scores
    df_temp, idx_in_temp = scenario_from_user_inputs(
        args.magnitude, args.max_height, args.runups, args.deposits, 
        city_amp_factor, df_template
    )
    df_temp_scored = compute_damage_score(df_temp, weights=weights)
    scenario_row = df_temp_scored.iloc[idx_in_temp]
    score = float(scenario_row["Damage Score"])

    # 3. Compute metrics and loss
    base_scores = df_scores["Damage Score"].dropna().astype(float)
    percentile = 100.0 * (base_scores < score).sum() / max(1, len(base_scores))
    est_loss = estimate_loss_from_score(score, args.total_exposed_value_usd, args.calibration_factor)

    # 4. Build human-readable output
    lines = []
    lines.append("LOCATION-BASED SCENARIO REPORT")
    lines.append("-" * 35)
    lines.append(f"Target City: {args.location_name.title()}")
    lines.append(f"Location Key: {city_key}")
    lines.append(f"Elevation Vulnerability Factor (0-1): {city_amp_factor:.4f}")
    lines.append("")
    lines.append("Hazard Inputs:")
    lines.append(f"- Magnitude: {args.magnitude}")
    lines.append(f"- Max Water Height (m): {args.max_height}")
    lines.append("")
    lines.append("Damage Score Calculation:")
    lines.append(f"- Damage Score (0..1): {score:.4f}")
    lines.append(f"- Percentile vs dataset: {percentile:.1f}th percentile")
    lines.append(f"- Estimated Loss USD: ${est_loss:,.0f}")
    lines.append("-" * 35)
    
    report_txt = "\n".join(lines)
    print(report_txt)

    # Save CSV summary for scenario
    out_csv = f"{args.out_prefix}_{city_key}_report.csv"
    summary_row = {
        "City Name": args.location_name,
        "City Factor (Vulnerability)": city_amp_factor,
        "Damage Score": score,
        "Percentile": percentile,
        "Estimated Loss USD": est_loss
    }
    pd.DataFrame([summary_row]).to_csv(out_csv, index=False)
    print(f"Saved location report summary: {out_csv}")


# ---------- MAIN PIPELINE (UPDATED) ----------
def run_pipeline(args):
    # Step 1: Run geospatial processor (or load simulated output)
    if not os.path.exists(VULNERABILITY_FILE):
        print("\n*** ACTION REQUIRED ***")
        print(f"Please run the 'geospatial_processor.py' script first to generate the necessary file: {VULNERABILITY_FILE}")
        print("Then re-run this script.")
        print("Exiting model run.")
        return

    vulnerability_factors = load_vulnerability_data(VULNERABILITY_FILE)
    
    # Step 2: Load Tsunami Historical Data
    df = load_data(args.input_csv)

    # Step 3: Compute scores
    weights = {
        "magnitude": args.w_magnitude,
        "max_height": args.w_max_height,
        "runups": args.w_runups,
        "deposits": args.w_deposits,
        "city_amp": args.w_city_amp
    }
    
    # We use a neutral data frame for computing historical scores (City Factor column = 0.0)
    df_scores = compute_damage_score(df, weights=weights)

    out_prefix = args.out_prefix or "tsunami_model"

    if args.mode == "historical":
        # ... (Historical mode logic remains mostly unchanged, using df_scores)
        pass # Omitted for brevity
        
    elif args.mode == "synthetic":
        # MODIFIED: Focus only on location-based synthetic reports now
        if args.location_name:
            generate_location_report(args, df_scores, weights, vulnerability_factors)
        else:
            print("\nError: In synthetic mode, you must specify --location_name with the new model.")
            print("Available cities:", ", ".join(CITY_NAME_TO_KEY.keys()))

    else:
        raise ValueError("Unknown mode. Choose 'historical' or 'synthetic'")


# --- CLI ---
def parse_args():
    p = argparse.ArgumentParser(description="Tsunami damage assessment model with geographic factors.")
    p.add_argument("--input_csv", default=DEFAULT_INPUT, help="Path to world_tsunamis.csv")
    p.add_argument("--mode", choices=["historical","synthetic"], default="synthetic", help="Mode: 'historical' or 'synthetic'")
    p.add_argument("--country", default=None, help="If historical mode, filter by country")
    p.add_argument("--top_n", type=int, default=50, help="Number of top events/locations to report (historical mode)")
    
    # Synthetic Scenario Inputs
    p.add_argument("--magnitude", type=float, default=8.5, help="Synthetic scenario earthquake magnitude")
    p.add_argument("--max_height", type=float, default=3.0, help="Synthetic scenario max water height (m)")
    p.add_argument("--runups", type=float, default=2.0, help="Synthetic scenario number of runups")
    p.add_argument("--deposits", type=float, default=1.0, help="Synthetic scenario deposits (severity proxy)")
    
    # LOCATION INPUT (NEW REQUIRED ARGUMENT FOR SYNTHETIC MODE)
    p.add_argument("--location_name", type=str, default=None, 
                     help="(REQUIRED for synthetic mode) City name (e.g., 'Crescent City, CA').")
    
    # Weights Arguments (must sum close to 1.0)
    p.add_argument("--w_magnitude", type=float, default=DEFAULT_WEIGHTS["magnitude"], help="Weight for magnitude")
    p.add_argument("--w_max_height", type=float, default=DEFAULT_WEIGHTS["max_height"], help="Weight for max height")
    p.add_argument("--w_runups", type=float, default=DEFAULT_WEIGHTS["runups"], help="Weight for runups")
    p.add_argument("--w_deposits", type=float, default=DEFAULT_WEIGHTS["deposits"], help="Weight for deposits")
    p.add_argument("--w_city_amp", type=float, default=DEFAULT_WEIGHTS["city_amp"], help="(NEW) Weight for the City Amplification Factor.")

    # Financial Mapping
    p.add_argument("--total_exposed_value_usd", type=float, default=1.0e9, help="Total exposed asset value in USD.")
    p.add_argument("--calibration_factor", type=float, default=1.0, help="Calibration factor.")
    p.add_argument("--out_prefix", default="tsunami_model", help="Prefix for saved outputs")
    p.add_argument("--verbose", action="store_true", help="Enable verbose printing")
    return p.parse_args()

if __name__ == "__main__":
    # Note: Calibration functions were removed to simplify the logic after the weight vector size changed.
    # If you need calibration, you must update the compute_adjusted_weights_from_example function 
    # to handle 5 dimensions (Mag, Height, Runups, Deposits, City Factor).
    run_pipeline(parse_args())