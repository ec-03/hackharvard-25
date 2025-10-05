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
    CITY_COORDS
)

st.set_page_config(page_title="🌊 Tsunami Impact Simulator", layout="wide")

def sidebar_inputs():
    st.sidebar.header("Simulation Settings")

    city = st.sidebar.selectbox("Select City", sorted(dummy_vulnerability.keys()))
    depth = st.sidebar.slider("Wave Depth (m)", 0.0, 30.0, 5.0, 0.5)
    velocity = st.sidebar.slider("Wave Velocity (m/s)", 0.0, 50.0, 10.0, 1.0)
    pop_density = st.sidebar.number_input(
        "Population Density (people/km²)", min_value=0, max_value=10000, value=1000, step=100
    )
    building_resilience = st.sidebar.slider(
        "Building Resilience (0 = weak, 1 = very strong)", 0.0, 1.0, 0.8, 0.05
    )

    return city, depth, velocity, pop_density, building_resilience

def main():
    st.title("🌊 Tsunami Impact Simulator")

    city, depth, velocity, pop_density, building_resilience = sidebar_inputs()

    df = pd.DataFrame([{
        "depth": depth,
        "velocity": velocity,
        "population_density": pop_density,
        "building_resilience": building_resilience
    }])

    df = compute_damage_dataframe(df, city_key=city)
    damage_score = float(df.loc[0, "damage_score"])

    st.subheader("Simulation Output")
    st.metric("City", city.title())
    st.metric("Damage Score", f"{damage_score:.2f} / 100")

    # --- Estimated Cost (scaled by damage and population)
    cost_estimate = damage_score * pop_density * (1 - building_resilience) * 10
    st.metric("Estimated Economic Cost", f"${cost_estimate:,.0f}")

    # --- Summary and Sensitivity
    summary = summarize_damage(df)
    with st.expander("View Summary Statistics"):
        st.write(summary)

    sensitivity = compute_sensitivity(df, city_key=city)
    with st.expander("Sensitivity Analysis"):
        st.write("Change in damage score (mean) when each factor is increased by 10%")
        st.write(sensitivity)

    # --- Map Visualization
    st.subheader("Geographic Impact Visualization")

    if city in CITY_COORDS:
        lat, lon = CITY_COORDS[city]
        m = folium.Map(location=[lat, lon], zoom_start=5, tiles="CartoDB positron")

        color = (
            "green" if damage_score < 25 else
            "orange" if damage_score < 60 else
            "red"
        )

        folium.CircleMarker(
            location=[lat, lon],
            radius=10 + damage_score / 10,
            color=color,
            fill=True,
            fill_opacity=0.6,
            popup=f"{city.title()}\nDamage Score: {damage_score:.2f}\nEstimated Cost: ${cost_estimate:,.0f}",
        ).add_to(m)

        st_folium(m, width=700, height=500)
    else:
        st.warning("City coordinates not found — map visualization unavailable.")

    # --- Vulnerability Info
    vuln = dummy_vulnerability.get(city, None)
    if vuln is not None:
        st.write(f"**Vulnerability Factor for {city.title()}:** {vuln:.2f}")

if __name__ == "__main__":
    main()
