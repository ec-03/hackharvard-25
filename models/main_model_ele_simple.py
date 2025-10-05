import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# =========================================================
# Dummy vulnerability dataset (city-specific scaling factor)
# =========================================================
dummy_vulnerability = {
    "crescent_city_ca": 0.85,
    "sendai_japan": 0.75,
    "aceh_indonesia": 0.95,
    "coquimbo_chile": 0.80,
    "kamchatka_russia": 0.40,
    "lemnos_greece": 0.55,
    "cambridge_ma": 0.10,
    "sydney_australia": 0.65,
    "rio_de_janeiro_brazil": 0.50,
    "singapore": 0.88,
    "london_uk": 0.05,
    "dubai_uae": 0.70,
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

# =========================================================
# Tsunami Damage Model Core
# =========================================================
def calculate_damage(depth, velocity, population_density, building_resilience, vulnerability_factor):
    """
    Core tsunami damage model combining physical + social parameters.

    Parameters:
        depth (float): Wave height (m)
        velocity (float): Wave velocity (m/s)
        population_density (float): Population density (people/km^2)
        building_resilience (float): Building structural resilience factor (0-1)
        vulnerability_factor (float): Social/environmental vulnerability (0-1)

    Returns:
        float: Final damage score (0-100)
    """
    # Normalize inputs to stable range
    depth_term = np.clip(depth / 30, 0, 1)
    velocity_term = np.clip(velocity / 50, 0, 1)
    pop_term = np.clip(population_density / 5000, 0, 1)
    resilience_term = np.clip(1 - building_resilience, 0, 1)
    vuln_term = np.clip(vulnerability_factor, 0, 1)

    # Weighted sum — physical + social risk
    damage = (
        0.35 * depth_term +
        0.25 * velocity_term +
        0.20 * pop_term +
        0.10 * resilience_term +
        0.10 * vuln_term
    ) * 100

    return np.clip(damage, 0, 100)


# =========================================================
# DataFrame-level computation (used by Streamlit)
# =========================================================
def compute_damage_dataframe(df, city_key="crescent_city_ca"):
    """
    Compute tsunami damage scores for all rows in a dataframe.
    Each row must have: depth, velocity, population_density, building_resilience.

    Parameters:
        df (pd.DataFrame): Input data
        city_key (str): City name (key from dummy_vulnerability)

    Returns:
        pd.DataFrame: Updated with 'damage_score' column
    """
    vuln = dummy_vulnerability.get(city_key.lower(), 0.5)
    df["damage_score"] = df.apply(
        lambda row: calculate_damage(
            row["depth"],
            row["velocity"],
            row["population_density"],
            row["building_resilience"],
            vuln
        ),
        axis=1
    )
    return df


# =========================================================
# Summary + Statistical Analysis Functions
# =========================================================
def summarize_damage(df):
    """
    Compute key statistical summaries for damage results.
    """
    if "damage_score" not in df:
        raise ValueError("DataFrame missing 'damage_score' column.")
    summary = {
        "mean_damage": float(df["damage_score"].mean()),
        "max_damage": float(df["damage_score"].max()),
        "min_damage": float(df["damage_score"].min()),
        "std_dev": float(df["damage_score"].std()),
        "median_damage": float(df["damage_score"].median()),
    }
    return summary


def compute_sensitivity(df, city_key="crescent_city_ca"):
    """
    Simple sensitivity analysis:
    Measures how small perturbations in each factor affect the final damage score.
    """
    base_df = df.copy()
    base_damage = compute_damage_dataframe(base_df, city_key)["damage_score"]

    sensitivity = {}
    factors = ["depth", "velocity", "population_density", "building_resilience"]

    for factor in factors:
        perturbed = df.copy()
        perturbed[factor] *= 1.1  # +10% increase
        new_damage = compute_damage_dataframe(perturbed, city_key)["damage_score"]
        diff = new_damage.mean() - base_damage.mean()
        sensitivity[factor] = float(diff)

    return sensitivity


# =========================================================
# Visualization Hooks (to be called in Streamlit)
# =========================================================
def plot_damage_distribution(df):
    """
    Generates a simple damage histogram.
    """
    if "damage_score" not in df:
        raise ValueError("DataFrame missing 'damage_score' column.")
    plt.figure(figsize=(6, 4))
    plt.hist(df["damage_score"], bins=20, color="royalblue", edgecolor="black")
    plt.title("Distribution of Tsunami Damage Scores")
    plt.xlabel("Damage Score")
    plt.ylabel("Frequency")
    plt.tight_layout()
    return plt


def plot_factor_correlation(df):
    """
    Visualize correlation heatmap among model factors.
    """
    import seaborn as sns
    corr = df[["depth", "velocity", "population_density", "building_resilience", "damage_score"]].corr()
    plt.figure(figsize=(6, 4))
    sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f")
    plt.title("Correlation Heatmap of Model Variables")
    plt.tight_layout()
    return plt


# =========================================================
# Example Run (CLI Testing)
# =========================================================
if __name__ == "__main__":
    # Example dataset
    data = {
        "depth": [5, 10, 15, 20, 25],
        "velocity": [10, 20, 30, 40, 50],
        "population_density": [500, 1000, 2500, 4000, 5000],
        "building_resilience": [0.9, 0.8, 0.6, 0.4, 0.2],
    }
    df = pd.DataFrame(data)

    # Run model
    city = "sendai_japan"
    df = compute_damage_dataframe(df, city)
    summary = summarize_damage(df)
    sensitivity = compute_sensitivity(df, city)

    print(f"=== Damage Results for {city} ===")
    print(df)
    print("\nSummary Statistics:", summary)
    print("\nSensitivity Analysis:", sensitivity)
