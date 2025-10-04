import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import json
import os

# ==========================================================
# 1. Data Loading & Preprocessing
# ==========================================================

def load_data(filepath: str) -> pd.DataFrame:
    """Load tsunami dataset from a CSV file."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Dataset not found at: {filepath}")
    df = pd.read_csv(filepath)
    return df


def normalize_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Normalize selected numeric columns to [0, 1] range."""
    for col in cols:
        if col in df.columns:
            min_val, max_val = df[col].min(), df[col].max()
            df[col] = (df[col] - min_val) / (max_val - min_val + 1e-9)
    return df


def validate_inputs(magnitude: float, height: float, runups: float, deposits: float):
    """Ensure realistic ranges for tsunami parameters."""
    if not (0 <= magnitude <= 10):
        raise ValueError("Magnitude must be between 0 and 10.")
    if height < 0 or runups < 0 or deposits < 0:
        raise ValueError("Physical parameters cannot be negative.")


# ==========================================================
# 2. Core Modeling Functions
# ==========================================================

def scenario_from_user_inputs(magnitude, max_height, runups, deposits, df):
    """Generate a new scenario row from user-provided inputs."""
    scenario = {
        "Magnitude": magnitude,
        "Max Water Height (m)": max_height,
        "Runups": runups,
        "Deposits": deposits,
    }
    return pd.concat([df, pd.DataFrame([scenario])], ignore_index=True)


def compute_damage_score(df: pd.DataFrame) -> pd.DataFrame:
    """Compute damage score as a normalized weighted sum of tsunami variables."""
    weights = {"Magnitude": 0.4, "Max Water Height (m)": 0.3, "Runups": 0.2, "Deposits": 0.1}
    df = df.copy()

    # Normalize features to prevent scale bias
    for key in weights.keys():
        if key in df.columns:
            df[key] = (df[key] - df[key].min()) / (df[key].max() - df[key].min() + 1e-9)

    df["Damage Score"] = (
        weights["Magnitude"] * df["Magnitude"]
        + weights["Max Water Height (m)"] * df["Max Water Height (m)"]
        + weights["Runups"] * df["Runups"]
        + weights["Deposits"] * df["Deposits"]
    )

    return df


def estimate_loss_from_score(score: float, total_exposed: float = 1e9, calibration_factor: float = 0.75) -> float:
    """Estimate financial loss from damage score."""
    return calibration_factor * score * total_exposed


# ==========================================================
# 3. Model Diagnostics & Statistical Analyses
# ==========================================================

def model_diagnostics(df: pd.DataFrame):
    """Return descriptive statistics and correlation with damage score."""
    desc = df.describe()
    correlations = df.corr(numeric_only=True)["Damage Score"].sort_values(ascending=False)
    return desc, correlations


def sensitivity_analysis(df: pd.DataFrame, idx: int):
    """
    Compute sensitivity of the damage score to small perturbations
    in each input parameter for a single scenario.
    """
    base = df.iloc[idx].copy()
    results = {}
    for col in ["Magnitude", "Max Water Height (m)", "Runups", "Deposits"]:
        if col in df.columns:
            df_temp = df.copy()
            perturb = 0.1 * (base[col] if base[col] != 0 else 1)
            df_temp.loc[idx, col] += perturb
            new_df = compute_damage_score(df_temp)
            delta_score = new_df.loc[idx, "Damage Score"] - base["Damage Score"]
            results[col] = delta_score / perturb
    return results


def calibrate_model(df: pd.DataFrame, target_col: str = "Actual Damage Ratio"):
    """
    Fit a linear regression model to calibrate the damage score
    against actual observed damages (if available).
    """
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataset.")

    features = ["Magnitude", "Max Water Height (m)", "Runups", "Deposits"]
    X = df[features]
    y = df[target_col]

    model = LinearRegression()
    model.fit(X, y)

    df["Predicted Damage"] = model.predict(X)
    r2 = model.score(X, y)

    return {
        "coefficients": dict(zip(features, model.coef_)),
        "intercept": model.intercept_,
        "r2_score": r2,
    }


def compare_scenarios(df: pd.DataFrame, idx1: int, idx2: int) -> pd.Series:
    """Compare two scenario rows by difference in features and damage score."""
    cols = ["Magnitude", "Max Water Height (m)", "Runups", "Deposits", "Damage Score"]
    return df.iloc[idx1][cols] - df.iloc[idx2][cols]

def get_correlation_matrix(df: pd.DataFrame):
    """Return numeric correlation matrix for plotting heatmaps."""
    return df.corr(numeric_only=True)

def damage_vs_parameter(df: pd.DataFrame, param: str):
    """Return parameter values and corresponding damage scores for trend visualization."""
    return df[param], df["Damage Score"]

def sensitivity_dataframe(df: pd.DataFrame):
    """Compute sensitivity for all scenarios and return as a DataFrame."""
    sensitivities = []
    for i in range(len(df)):
        sa = sensitivity_analysis(df, i)
        sa["Scenario"] = i
        sensitivities.append(sa)
    return pd.DataFrame(sensitivities)

# ==========================================================
# 4. Utility & Output
# ==========================================================

def save_results(df: pd.DataFrame, output_path: str = "output.json"):
    """Save results as JSON."""
    try:
        df.to_json(output_path, orient="records", indent=2)
        print(f"Results saved to {output_path}")
    except Exception as e:
        print("Error saving results:", e)


# ==========================================================
# 5. CLI Integration (to run quickly here without Streamlit)
# ==========================================================

def run_pipeline(filepath: str, magnitude: float, height: float, runups: float, deposits: float):
    """Run full CLI pipeline (for testing without Streamlit)."""
    df = load_data(filepath)
    df = scenario_from_user_inputs(magnitude, height, runups, deposits, df)
    df = compute_damage_score(df)
    score = df.iloc[-1]["Damage Score"]
    loss = estimate_loss_from_score(score)

    desc, corr = model_diagnostics(df)
    sens = sensitivity_analysis(df, -1)

    print(f"Damage Score: {score:.3f}")
    print(f"Estimated Loss: ${loss:,.0f}")
    print("\nTop Correlations:\n", corr)
    print("\nSensitivity Analysis:\n", sens)

    save_results(df, "latest_results.json")
    return df
