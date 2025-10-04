"""
tsunami_baseline_pipeline.py

Formula-only tsunami damage baseline pipeline.

Usage examples:

# 1) Quick synthetic scenario (user-provided hazard toggles)
python tsunami_baseline_pipeline.py --mode synthetic --magnitude 8.5 --max_height 5.0 --runups 3 --deposits 2 --total_exposed 1000000000 --out_prefix crescent_demo

# 2) Analyze historical events for a country (e.g., Japan) and produce outputs
python tsunami_baseline_pipeline.py --mode historical --country Japan --top_n 30 --total_exposed 5000000000 --out_prefix japan_report

"""

import pandas as pd
import numpy as np
import argparse
import os
import math
import matplotlib.pyplot as plt
import folium
from folium.plugins import MarkerCluster

# ---------- Config / defaults ----------
DEFAULT_INPUT = "world_tsunamis.csv"

DEFAULT_WEIGHTS = {
    "magnitude": 0.3,
    "max_height": 0.3,
    "runups": 0.2,
    "deposits": 0.2
}

# ---------- Utility functions ----------
def load_data(path=DEFAULT_INPUT):
    print("Loading data...")
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found: {path}")
    df = pd.read_csv(path)
    print("Data loaded. Rows:", len(df))
    return df

def normalize_series(s):
    if s.max() == s.min():
        return np.zeros_like(s, dtype=float)
    return (s - s.min()) / (s.max() - s.min())

def compute_damage_score(df, weights=None,
                         mag_col="Earthquake Magnitude",
                         height_col="Maximum Water Height (m)",
                         runups_col="Number of Runups",
                         deposits_col="Deposits"):
    if weights is None:
        weights = DEFAULT_WEIGHTS

    for col in [mag_col, height_col, runups_col, deposits_col]:
        if col not in df.columns:
            raise KeyError(f"Missing required column in data: {col}")

    df = df.copy()
    df["_mag_n"] = normalize_series(df[mag_col].astype(float))
    df["_h_n"] = normalize_series(df[height_col].astype(float))
    df["_r_n"] = normalize_series(df[runups_col].astype(float))
    df["_d_n"] = normalize_series(df[deposits_col].astype(float))

    score = (
        weights.get("magnitude", 0.0) * df["_mag_n"] +
        weights.get("max_height", 0.0) * df["_h_n"] +
        weights.get("runups", 0.0) * df["_r_n"] +
        weights.get("deposits", 0.0) * df["_d_n"]
    )
    score = np.clip(score, 0.0, 1.0)
    df["Damage Score"] = score
    # remove aux cols
    df = df.drop(columns=["_mag_n","_h_n","_r_n","_d_n"], errors='ignore')
    return df

def scenario_from_user_inputs(magnitude, max_height, runups, deposits, df_template):
    """
    Build a one-row DataFrame representing a synthetic scenario.
    Use df_template only to keep same columns and to compute normalization baseline.
    """
    row = {}
    mag_col = "Earthquake Magnitude"
    height_col = "Maximum Water Height (m)"
    runups_col = "Number of Runups"
    deposits_col = "Deposits"

    # prepare a df with this new scenario appended to the dataset so normalization is consistent
    newrow = {mag_col: magnitude, height_col: max_height, runups_col: runups, deposits_col: deposits}
    df_temp = df_template[[mag_col, height_col, runups_col, deposits_col]].copy()
    newrow_df = pd.DataFrame([newrow])
    df_temp = pd.concat([df_temp, newrow_df], ignore_index=True)
    return df_temp, len(df_temp) - 1 

def estimate_loss_from_score(score, total_exposed_value_usd, calibration_factor=0.159469):
    """
    Map damage score (0..1) to USD loss.
    - total_exposed_value_usd: estimated total value of assets in the region (user-supplied)
    - calibration_factor: multiplicative factor for calibration to known losses
    """
    # simple proportional mapping
    loss = float(score) * float(total_exposed_value_usd) * float(calibration_factor)
    return loss


def compute_calibration_factor_from_loss(score, actual_loss, total_exposed_value_usd):
    """
    Given a predicted damage score (0..1), observed actual_loss (USD) and the total exposed USD,
    compute a scalar calibration factor so that: actual_loss = score * total_exposed_value_usd * calibration_factor
    Returns calibration_factor (float) or None if not computable (e.g., score == 0).
    """
    score = float(score)
    if score <= 0 or total_exposed_value_usd == 0:
        return None
    return float(actual_loss) / (score * float(total_exposed_value_usd))

def compute_adjusted_weights_from_example(x_vec, w0, target_score, enforce_nonneg=True):
    """
    Solve for a new weight vector w that is as close as possible to w0 (minimize ||w-w0||^2)
    subject to the linear equality constraints:
      w.dot(x_vec) == target_score
      sum(w) == 1

    This has an analytic solution via projection onto the affine subspace. We do not enforce
    inequality constraints (w>=0) in the analytic projection; if enforce_nonneg is True,
    we clip negatives and renormalize sum to 1 as a simple postprocess.

    Inputs:
      x_vec: array-like length 4 (normalized feature values for the example)
      w0: array-like length 4 (initial weights)
      target_score: desired score for the example (scalar)
      enforce_nonneg: if True, clip negatives after projection and renormalize to sum 1

    Returns: numpy array of adjusted weights (length 4)
    """
    x = np.asarray(x_vec, dtype=float).reshape(4)
    w0 = np.asarray(w0, dtype=float).reshape(4)

    # Build A and b such that A @ w = b. A shape (2,4): [x; ones]
    A = np.vstack([x, np.ones_like(x)])
    b = np.array([float(target_score), 1.0])

    # Compute projection: w = w0 - A^T (A A^T)^{-1} (A w0 - b)
    ATA = A @ A.T  # 2x2
    try:
        inv_ATA = np.linalg.inv(ATA)
    except np.linalg.LinAlgError:
        # Degenerate (e.g., x and ones are linearly dependent) -> fall back to returning w0
        return w0

    correction = A.T @ (inv_ATA @ (A @ w0 - b))
    w = w0 - correction

    if enforce_nonneg:
        w = np.clip(w, 0.0, None)
        s = w.sum()
        if s == 0:
            # can't renormalize; return original
            return w0
        w = w / s

    return w


def save_summary_csv(df, path):
    df.to_csv(path, index=False)
    print(f"Saved CSV: {path}")

# ---------- Reporting helpers ----------
def plot_histogram_scores(df, out_png):
    plt.figure(figsize=(6,4))
    plt.hist(df["Damage Score"].dropna(), bins=25, edgecolor="k")
    plt.title("Distribution of Damage Scores")
    plt.xlabel("Damage Score")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()
    print(f"Saved plot: {out_png}")

def plot_top_locations(df, out_png, top_n=50):
    # If coordinates exist, plot scatter of top_n points by score (lat/lon expected)
    lat_col = None
    lon_col = None
    for c in ["Latitude", "Lat", "latitude", "LAT"]:
        if c in df.columns:
            lat_col = c
            break
    for c in ["Longitude", "Lon", "longitude", "LON"]:
        if c in df.columns:
            lon_col = c
            break
    if lat_col is None or lon_col is None:
        print("No lat/lon columns found; skipping map scatter plot.")
        return

    sub = df.dropna(subset=[lat_col, lon_col, "Damage Score"]).copy()
    sub = sub.sort_values("Damage Score", ascending=False).head(top_n)
    plt.figure(figsize=(6,4))
    plt.scatter(sub[lon_col], sub[lat_col], c=sub["Damage Score"], cmap="Reds", s=40)
    plt.colorbar(label="Damage Score")
    plt.title(f"Top {top_n} vulnerable locations (by Damage Score)")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()
    print(f"Saved scatter plot: {out_png}")

def create_folium_map(df, out_html, top_k=200):
    # Create a map centered at median location
    lat_col = None
    lon_col = None
    for c in ["Latitude", "Lat", "latitude", "LAT"]:
        if c in df.columns:
            lat_col = c
            break
    for c in ["Longitude", "Lon", "longitude", "LON"]:
        if c in df.columns:
            lon_col = c
            break
    if lat_col is None or lon_col is None:
        print("No lat/lon columns present; cannot create folium map.")
        return

    dfp = df.dropna(subset=[lat_col, lon_col, "Damage Score"]).copy()
    if dfp.empty:
        print("No point data with lat/lon + scores.")
        return

    cen_lat = float(dfp[lat_col].median())
    cen_lon = float(dfp[lon_col].median())
    fmap = folium.Map(location=[cen_lat, cen_lon], zoom_start=5, tiles="CartoDB positron")
    mc = MarkerCluster()
    # add top_k points by score
    dfp = dfp.sort_values("Damage Score", ascending=False).head(top_k)
    for _, r in dfp.iterrows():
        lat = float(r[lat_col])
        lon = float(r[lon_col])
        score = float(r["Damage Score"])
        txt = f"{r.get('Location Name','')}<br>Score: {score:.3f}"
        folium.CircleMarker(
            location=[lat, lon],
            radius=4 + score*6,
            color=None,
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(txt, max_width=300)
        ).add_to(mc)
    fmap.add_child(mc)
    fmap.save(out_html)
    print(f"Saved folium map: {out_html}")


# ---------- Location helpers & reporting ----------
def _find_lat_lon_cols(df):
    lat_col = None
    lon_col = None
    for c in ["Latitude", "Lat", "latitude", "LAT"]:
        if c in df.columns:
            lat_col = c
            break
    for c in ["Longitude", "Lon", "longitude", "LON"]:
        if c in df.columns:
            lon_col = c
            break
    return lat_col, lon_col

def _haversine_km(lat1, lon1, lat2, lon2):
    # vectorized haversine: inputs in degrees, returns km
    lat1r = np.radians(lat1)
    lon1r = np.radians(lon1)
    lat2r = np.radians(lat2)
    lon2r = np.radians(lon2)
    dlat = lat2r - lat1r
    dlon = lon2r - lon1r
    a = np.sin(dlat/2.0)**2 + np.cos(lat1r) * np.cos(lat2r) * np.sin(dlon/2.0)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return 6371.0 * c

def find_nearest_location(df, lat, lon):
    lat_col, lon_col = _find_lat_lon_cols(df)
    if lat_col is None or lon_col is None:
        return None, None
    dfp = df.dropna(subset=[lat_col, lon_col]).copy()
    if dfp.empty:
        return None, None
    dists = _haversine_km(lat, lon, dfp[lat_col].astype(float).values, dfp[lon_col].astype(float).values)
    imin = int(np.argmin(dists))
    idx = dfp.index[imin]
    return idx, float(dists[imin])

def find_location_by_name(df, name):
    # search common location-name columns and (optionally) use fuzzy matching
    name_cols = [c for c in df.columns if c.lower() in ("location name","location","place","name")] or [c for c in df.columns if 'location' in c.lower()]
    raw_name = (name or '').strip()
    if not name_cols or not raw_name:
        return None, None

    # try to use rapidfuzz for fuzzy search; fall back to substring match
    try:
        from rapidfuzz import process, fuzz
        use_rapid = True
    except Exception:
        use_rapid = False

    # iterate candidate columns
    best_idx = None
    best_score = -1.0
    for col in name_cols:
        col_vals = df[col].astype(str).fillna("").tolist()
        if use_rapid:
            # rapidfuzz returns tuples (match, score, index)
            try:
                matches = process.extract(raw_name, col_vals, scorer=fuzz.WRatio, limit=3)
                if matches:
                    m_match, m_score, m_i = matches[0]
                    if m_score > best_score:
                        best_score = float(m_score)
                        best_idx = df.index[int(m_i)]
            except Exception:
                pass
        else:
            # simple substring search (case-insensitive)
            lower = raw_name.lower()
            for i, v in enumerate(col_vals):
                if lower in v.lower():
                    # assign a high confidence for substring
                    best_idx = df.index[i]
                    best_score = 100.0
                    break
            if best_score == 100.0:
                break

    if best_idx is None:
        return None, None
    return best_idx, best_score

def generate_location_report(args, df_scores, weights):
    """Given args with either lat/lon or location_name, produce a human-readable report and CSVs."""
    lat_col, lon_col = _find_lat_lon_cols(df_scores)
    # locate target index
    target_idx = None
    distance_km = None
    if args.location_name:
        target_idx, match_score = find_location_by_name(df_scores, args.location_name)
        if target_idx is None and args.verbose:
            print(f"No name match for '{args.location_name}'")
    if target_idx is None and args.lat is not None and args.lon is not None:
        target_idx, distance_km = find_nearest_location(df_scores, args.lat, args.lon)

    # If still not found, fall back to nearest by provided coords (if any), else None
    if target_idx is None and args.lat is not None and args.lon is not None:
        target_idx, distance_km = find_nearest_location(df_scores, args.lat, args.lon)

    # Prepare the template for normalization (use the full dataset so scores are comparable)
    df_template = df_scores

    # Create the synthetic scenario and append
    df_temp, idx_in_temp = scenario_from_user_inputs(args.magnitude, args.max_height, args.runups, args.deposits, df_template)
    df_temp_scored = compute_damage_score(df_temp, weights=weights)
    scenario_row = df_temp_scored.iloc[idx_in_temp]
    score = float(scenario_row["Damage Score"])

    # Compute percentile relative to original dataset (exclude any NaNs)
    base_scores = df_scores["Damage Score"].dropna().astype(float)
    percentile = 100.0 * (base_scores < score).sum() / max(1, len(base_scores))

    est_loss = estimate_loss_from_score(score, args.total_exposed_value_usd, args.calibration_factor)

    # Nearby context
    nearby_summary = None
    if lat_col and lon_col:
        # choose a reference point: if user provided coords use them, else use matched location coordinates
        if args.lat is not None and args.lon is not None:
            ref_lat, ref_lon = float(args.lat), float(args.lon)
        elif target_idx is not None:
            ref_lat = float(df_scores.loc[target_idx, lat_col])
            ref_lon = float(df_scores.loc[target_idx, lon_col])
        else:
            ref_lat = ref_lon = None

        if ref_lat is not None:
            dfp = df_scores.dropna(subset=[lat_col, lon_col]).copy()
            dists = _haversine_km(ref_lat, ref_lon, dfp[lat_col].astype(float).values, dfp[lon_col].astype(float).values)
            dfp = dfp.assign(_dist_km=dists)
            nearby = dfp[dfp._dist_km <= args.nearby_km].sort_values("Damage Score", ascending=False).head(10)
            nearby_summary = nearby[[lat_col, lon_col, "Damage Score"]].copy()

    # Build human-readable output
    lines = []
    lines.append("LOCATION-BASED SCENARIO REPORT")
    if target_idx is not None:
        lines.append(f"Matched dataset row index: {target_idx}")
        if 'match_score' in locals() and match_score is not None:
            lines.append(f"Name match score: {match_score:.1f} (0-100, higher better)")
        # show some identifying cols if available
        id_cols = [c for c in ("Country","Location Name","Place","Name") if c in df_scores.columns]
        for c in id_cols:
            lines.append(f"{c}: {df_scores.loc[target_idx, c]}")
        if lat_col and lon_col:
            lines.append(f"Matched coordinates: {df_scores.loc[target_idx, lat_col]}, {df_scores.loc[target_idx, lon_col]}")
            if distance_km is not None:
                lines.append(f"Distance from query point: {distance_km:.1f} km")
    else:
        lines.append("No matching location found in dataset. Report is for the provided coordinates/scenario.")

    lines.append("")
    lines.append("Scenario inputs:")
    lines.append(f"- Magnitude: {args.magnitude}")
    lines.append(f"- Max Water Height (m): {args.max_height}")
    lines.append(f"- Number of Runups: {args.runups}")
    lines.append(f"- Deposits: {args.deposits}")
    lines.append("")
    lines.append(f"Damage Score (0..1): {score:.4f}")
    lines.append(f"Percentile vs dataset: {percentile:.1f}th percentile (higher = more severe)")
    lines.append(f"Estimated Loss USD (using Total Exposed = ${args.total_exposed_value_usd:,.0f}): ${est_loss:,.0f}")

    if nearby_summary is not None and not nearby_summary.empty:
        lines.append("")
        lines.append(f"Nearby events within {args.nearby_km} km (top by Damage Score):")
        for _, r in nearby_summary.iterrows():
            lines.append(f" - {r[lat_col]:.3f},{r[lon_col]:.3f} : Damage Score={r['Damage Score']:.3f}")

    report_txt = "\n".join(lines)
    print(report_txt)

    # Save CSV summary for scenario and nearby
    out_csv = f"{args.out_prefix}_location_report.csv"
    summary_row = {
        "Matched Index": target_idx,
        "Match Score": match_score if 'match_score' in locals() else None,
        "Latitude Query": args.lat,
        "Longitude Query": args.lon,
        "Damage Score": score,
        "Percentile": percentile,
        "Estimated Loss USD": est_loss
    }
    pd.DataFrame([summary_row]).to_csv(out_csv, index=False)
    print(f"Saved location report summary: {out_csv}")
    if nearby_summary is not None and not nearby_summary.empty:
        nearby_csv = f"{args.out_prefix}_nearby_events.csv"
        nearby_summary.to_csv(nearby_csv, index=False)
        print(f"Saved nearby events: {nearby_csv}")


# ---------- Main pipeline ----------
def run_pipeline(args):
    df = load_data(args.input_csv)

    # compute damage score with chosen weights
    weights = {
        "magnitude": args.w_magnitude,
        "max_height": args.w_max_height,
        "runups": args.w_runups,
        "deposits": args.w_deposits
    }
    df_scores = compute_damage_score(df, weights=weights)

    out_prefix = args.out_prefix or "tsunami_baseline"

    if args.mode == "historical":
        # Filter by country if requested
        if args.country:
            df_hist = df_scores[df_scores["Country"].str.lower().str.contains(args.country.lower(), na=False)].copy()
            if df_hist.empty:
                print(f"No historical records found for country matching '{args.country}'. Using full dataset instead.")
                df_hist = df_scores.copy()
        else:
            df_hist = df_scores.copy()

        # Aggregate top N events / locations by Damage Score
        top_n = args.top_n
        df_top = df_hist.sort_values("Damage Score", ascending=False).head(top_n)
        # Compute estimated losses per row
        df_top["Estimated Loss USD"] = df_top["Damage Score"].apply(
            lambda s: estimate_loss_from_score(s, args.total_exposed_value_usd, args.calibration_factor)
        )

        # Save top list
        csv_out = f"{out_prefix}_historical_top{top_n}.csv"
        save_summary_csv(df_top, csv_out)

        # plots and map
        plot_histogram_scores(df_hist, f"{out_prefix}_hist_scores_hist.png")
        plot_top_locations(df_hist, f"{out_prefix}_top_locations_scatter.png", top_n=min(200, top_n))
        create_folium_map(df_hist, f"{out_prefix}_map_top{top_n}.html", top_k=min(400, top_n))

        # summary print
        total_est = df_top["Estimated Loss USD"].sum()
        print("\nHISTORICAL SUMMARY")
        print(f"Number of events considered: {len(df_hist)}")
        print(f"Top {top_n} events estimated total loss (sum): ${total_est:,.0f}")
        print(f"Saved outputs with prefix: {out_prefix}_*")

    elif args.mode == "synthetic":
        # If a location is requested, generate a location-focused report
        if args.location_name or (args.lat is not None and args.lon is not None):
            generate_location_report(args, df_scores, weights)
        else:
            # Build synthetic scenario
            df_template = df_scores
            df_temp, idx = scenario_from_user_inputs(args.magnitude, args.max_height, args.runups, args.deposits, df_template)
            # Compute scores on extended table
            df_temp_scored = compute_damage_score(df_temp, weights=weights)
            # Our synthetic scenario is the last row
            scenario_row = df_temp_scored.iloc[idx]
            score = float(scenario_row["Damage Score"])
            est_loss = estimate_loss_from_score(score, args.total_exposed_value_usd, args.calibration_factor)

            # Create a small report CSV
            out_csv = f"{out_prefix}_synthetic_summary.csv"
            row_out = {
                "Magnitude": args.magnitude,
                "Max Water Height (m)": args.max_height,
                "Number of Runups": args.runups,
                "Deposits": args.deposits,
                "Damage Score": score,
                "Estimated Loss USD": est_loss,
                "Total Exposed USD (input)": args.total_exposed_value_usd,
                "Calibration Factor": args.calibration_factor
            }
            pd.DataFrame([row_out]).to_csv(out_csv, index=False)
            print(f"Synthetic scenario saved to {out_csv}")
            # simple printout
            print("\nSYNTHETIC SCENARIO SUMMARY")
            for k,v in row_out.items():
                if isinstance(v, float):
                    if "USD" in k:
                        print(f"{k}: ${v:,.0f}")
                    else:
                        print(f"{k}: {v:.4f}")
                else:
                    print(f"{k}: {v}")

            # Also produce a histogram of full dataset and mark the scenario
            plot_histogram_scores(df_scores, f"{out_prefix}_all_scores_hist.png")
            # Save a tiny map with dataset + scenario point if lat/lon provided or default to center
            try:
                create_folium_map(df_scores, f"{out_prefix}_all_map.html", top_k=200)
            except Exception as e:
                print("Map creation issue:", e)

    else:
        raise ValueError("Unknown mode. Choose 'historical' or 'synthetic'")

# ---------- CLI ----------
def parse_args():
    p = argparse.ArgumentParser(description="Tsunami formula-only baseline pipeline")
    p.add_argument("--input_csv", default=DEFAULT_INPUT, help="Path to world_tsunamis.csv")
    p.add_argument("--mode", choices=["historical","synthetic"], default="synthetic",
                   help="Mode: 'historical'=analyze historical events, 'synthetic'=user-provided scenario")
    p.add_argument("--country", default=None, help="If historical mode, filter by country (substring match)")
    p.add_argument("--top_n", type=int, default=50, help="Number of top events/locations to report (historical mode)")
    p.add_argument("--magnitude", type=float, default=8.5, help="Synthetic scenario earthquake magnitude")
    p.add_argument("--max_height", type=float, default=3.0, help="Synthetic scenario max water height (m)")
    p.add_argument("--runups", type=float, default=2.0, help="Synthetic scenario number of runups")
    p.add_argument("--deposits", type=float, default=1.0, help="Synthetic scenario deposits (severity proxy)")
    # location-based reporting
    p.add_argument("--location_name", type=str, default=None, help="(Optional) location name to match in dataset for localized report")
    p.add_argument("--lat", type=float, default=None, help="(Optional) latitude of query location for localized report")
    p.add_argument("--lon", type=float, default=None, help="(Optional) longitude of query location for localized report")
    p.add_argument("--nearby_km", type=float, default=50.0, help="Radius (km) for listing nearby historical events")

    # weights
    p.add_argument("--w_magnitude", type=float, default=DEFAULT_WEIGHTS["magnitude"], help="Weight for magnitude (sum weights should ideally be 1.0)")
    p.add_argument("--w_max_height", type=float, default=DEFAULT_WEIGHTS["max_height"], help="Weight for max height")
    p.add_argument("--w_runups", type=float, default=DEFAULT_WEIGHTS["runups"], help="Weight for runups")
    p.add_argument("--w_deposits", type=float, default=DEFAULT_WEIGHTS["deposits"], help="Weight for deposits")

    # financial mapping
    p.add_argument("--total_exposed_value_usd", type=float, default=1.0e9,
                   help="Total exposed asset value in USD for region (used to convert damage score -> USD).")
    p.add_argument("--calibration_factor", type=float, default=1.0,
                   help="Calibration factor multiply applied to estimated losses (tune if you have known losses).")
    p.add_argument("--calibrate_actual_loss", type=float, default=None,
                   help="(Optional) If provided, compute and save a calibration factor so that the model's predicted loss for the synthetic scenario equals this actual loss amount (USD).")
    p.add_argument("--calibrate_weights_from_actual", action='store_true',
                   help="If set along with --calibrate_actual_loss in synthetic mode, adjust feature weights so the synthetic scenario's normalized feature blend matches the implied score from the actual loss. Saves adjusted weights to <out_prefix>_weights.json.")

    p.add_argument("--out_prefix", default="tsunami_baseline", help="Prefix for saved outputs")
    p.add_argument("--verbose", action="store_true", help="Enable verbose printing")
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    # If user asked for calibration, perform compute after running synthetic scoring
    run_pipeline(args)
    if args.calibrate_actual_loss is not None and args.mode == 'synthetic':
        # Recompute score for the exact synthetic scenario using full dataset template
        df = load_data(args.input_csv)
        df_scores = compute_damage_score(df, weights={
            "magnitude": args.w_magnitude,
            "max_height": args.w_max_height,
            "runups": args.w_runups,
            "deposits": args.w_deposits
        })
        df_temp, idx = scenario_from_user_inputs(args.magnitude, args.max_height, args.runups, args.deposits, df_scores)
        df_temp_scored = compute_damage_score(df_temp, weights={
            "magnitude": args.w_magnitude,
            "max_height": args.w_max_height,
            "runups": args.w_runups,
            "deposits": args.w_deposits
        })
        scenario_row = df_temp_scored.iloc[idx]
        score = float(scenario_row["Damage Score"])
        actual_loss = float(args.calibrate_actual_loss)
        calib = compute_calibration_factor_from_loss(score, actual_loss, args.total_exposed_value_usd)
        if calib is None:
            print("Calibration could not be computed (score==0 or total_exposed==0)")
        else:
            print(f"Computed calibration factor: {calib:.6f}")
            # save to file
            outf = f"{args.out_prefix}_calibration.txt"
            with open(outf, 'w') as fh:
                fh.write(str(calib))
            print(f"Saved calibration factor to {outf}")
            # Optionally adjust weights to match the implied score
            if args.calibrate_weights_from_actual:
                # Build normalized feature vector for the synthetic example (we used df_temp_scored)
                # Need the normalized features before scoring: recompute normalized series on full dataset
                df_base = df_scores
                mag_col = "Earthquake Magnitude"
                height_col = "Maximum Water Height (m)"
                runups_col = "Number of Runups"
                deposits_col = "Deposits"
                # compute normalized series on df_base
                x_mag = normalize_series(df_base[mag_col].astype(float))
                x_h = normalize_series(df_base[height_col].astype(float))
                x_r = normalize_series(df_base[runups_col].astype(float))
                x_d = normalize_series(df_base[deposits_col].astype(float))
                # The synthetic point values used earlier are the last row of df_temp (idx)
                # Recreate the same temp and pick the raw feature values
                df_temp_raw, idx_temp = scenario_from_user_inputs(args.magnitude, args.max_height, args.runups, args.deposits, df_base)
                raw = df_temp_raw.iloc[idx_temp]
                # Normalize the raw values using the same min/max as df_base
                def norm_val(series, val):
                    mn = series.min(); mx = series.max()
                    if mx == mn:
                        return 0.0
                    return (val - mn) / (mx - mn)

                x_vec = np.array([
                    norm_val(df_base[mag_col].astype(float), raw[mag_col]),
                    norm_val(df_base[height_col].astype(float), raw[height_col]),
                    norm_val(df_base[runups_col].astype(float), raw[runups_col]),
                    norm_val(df_base[deposits_col].astype(float), raw[deposits_col])
                ], dtype=float)

                # current weights
                w0 = np.array([args.w_magnitude, args.w_max_height, args.w_runups, args.w_deposits], dtype=float)
                # implied target score from actual loss
                implied_score = actual_loss / float(args.total_exposed_value_usd) / float(calib)
                # compute adjusted weights
                w_new = compute_adjusted_weights_from_example(x_vec, w0, implied_score, enforce_nonneg=True)
                import json
                outf_w = f"{args.out_prefix}_weights.json"
                with open(outf_w, 'w') as fh:
                    json.dump({
                        "magnitude": float(w_new[0]),
                        "max_height": float(w_new[1]),
                        "runups": float(w_new[2]),
                        "deposits": float(w_new[3])
                    }, fh, indent=2)
                print(f"Saved adjusted weights to {outf_w}")
