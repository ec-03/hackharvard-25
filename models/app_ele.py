# app.py

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

from main_model_ele_simple import (
    compute_damage_dataframe,
    summarize_damage,
    compute_sensitivity,
    dummy_vulnerability,
    city_coordinates,
)

# Approximate GDP per capita (USD) by city/country for realism
city_gdp = {
    "crescent_city_ca": 65000,
    "sendai_japan": 48000,
    "aceh_indonesia": 11000,
    "coquimbo_chile": 22000,
    "kamchatka_russia": 16000,
    "lemnos_greece": 27000,
    "cambridge_ma": 85000,
    "sydney_australia": 62000,
    "rio_de_janeiro_brazil": 20000,
    "singapore": 87000,
    "london_uk": 55000,
    "dubai_uae": 60000,
}

# --- Calibration section ---
# Define baseline calibration constants for realism
BASE_DAMAGE_REF = 50        # typical mid-scale damage score
BASE_POP_REF = 2000         # moderate population density
BASE_GDP_REF = 50000        # reference GDP per capita
TARGET_COST = 1e8           # target cost scale ≈ $100M for moderate scenario

# Compute calibrated cost scale
COST_SCALE = TARGET_COST / ((BASE_DAMAGE_REF**2) * BASE_POP_REF * (BASE_GDP_REF / 50000))
# Now cost outputs should hover around 10M–500M for realistic inputs


st.set_page_config(page_title="🌊 Tsunami Impact Simulator", layout="wide")


def sidebar_inputs():
    st.sidebar.header("Simulation Settings")

    city = st.sidebar.selectbox("Select City", sorted(dummy_vulnerability.keys()))
    depth = st.sidebar.slider("Wave Depth (m)", 0.0, 30.0, 5.0, 0.5)
    velocity = st.sidebar.slider("Wave Velocity (m/s)", 0.0, 50.0, 10.0, 1.0)
    pop_density = st.sidebar.number_input(
        "Population Density (people/km²)",
        min_value=0,
        max_value=10000,
        value=1000,
        step=100,
    )
    building_resilience = st.sidebar.slider(
        "Building Resilience (0 = weak, 1 = very strong)", 0.0, 1.0, 0.8, 0.05
    )

    return city, depth, velocity, pop_density, building_resilience


def compute_cost(damage_score, city, pop_density):
    vuln = dummy_vulnerability.get(city, 0.5)
    gdp = city_gdp.get(city, 30000)
    gdp_factor = gdp / 50000

    # Nonlinear damage scaling model
    cost = (damage_score**2) * vuln * pop_density * gdp_factor * COST_SCALE
    return cost, vuln, gdp_factor


def main():
    st.title("🌊 Tsunami Impact Simulator")

    city, depth, velocity, pop_density, building_resilience = sidebar_inputs()

    df = pd.DataFrame(
        [
            {
                "depth": depth,
                "velocity": velocity,
                "population_density": pop_density,
                "building_resilience": building_resilience,
            }
        ]
    )

    df = compute_damage_dataframe(df, city_key=city)
    damage_score = float(df.loc[0, "damage_score"])

    # --- Compute cost and factors
    cost_estimate, vuln, gdp_factor = compute_cost(
        damage_score, city, pop_density
    )

    st.subheader("Simulation Output")
    st.metric("City", city.replace("_", " ").title())
    st.metric("Damage Score", f"{damage_score:.2f} / 100")
    st.metric("Estimated Economic Cost", f"${cost_estimate:,.0f}")

    # --- Transparent factor display (compact)
    with st.expander("View Economic Factors"):
        transparency_data = pd.DataFrame(
            {
                "Factor": ["Vulnerability", "GDP Factor", "Population Density"],
                "Value": [
                    f"{vuln:.2f}",
                    f"{gdp_factor:.2f}",
                    f"{pop_density:,} ppl/km²",
                ],
            }
        )
        st.table(transparency_data)

    # --- Sensitivity
    sensitivity = compute_sensitivity(df, city_key=city)
    with st.expander("Sensitivity Analysis"):
        st.write(
            "Change in damage score (mean) when each factor is increased by 10%:"
        )
        st.write(sensitivity)

    # --- Map Visualization
    st.subheader("Geographic Impact Visualization")

    if city in city_coordinates:
        lat, lon = city_coordinates[city]
        m = folium.Map(location=[lat, lon], zoom_start=5, tiles="CartoDB positron")

        color = (
            "green" if damage_score < 25 else "orange" if damage_score < 60 else "red"
        )

        folium.CircleMarker(
            location=[lat, lon],
            radius=10 + damage_score / 10,
            color=color,
            fill=True,
            fill_opacity=0.6,
            popup=folium.Popup(
                f"<b>{city.replace('_', ' ').title()}</b><br>"
                f"Damage Score: {damage_score:.2f}<br>"
                f"Estimated Cost: ${cost_estimate:,.0f}",
                max_width=250,
            ),
        ).add_to(m)

        st_folium(m, width=700, height=500)
    else:
        st.warning("City coordinates not found — map visualization unavailable.")

    st.caption(
        "Model: Estimated costs incorporate damage score, vulnerability, population density, and GDP per capita to approximate local impact."
    )


if __name__ == "__main__":
    main()


