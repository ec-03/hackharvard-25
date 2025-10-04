import streamlit as st
import pandas as pd
import sys

from main_model import compute_damage_score, estimate_loss_from_score, load_data

DATA_PATH = "world_tsunamis.csv"
df = load_data(DATA_PATH)

def save_to_json(results_df, filename="tsunami_results.json"):
    results_df.to_json(filename, orient='records', indent=4)
    print(f"Saved JSON: {filename}")

def run_streamlit_ui():
    st.title("Tsunami Impact Simulator")

    st.sidebar.header("Simulation Settings")

    cities = sorted(df["Country"].dropna().unique())
    selected_city = st.sidebar.selectbox("Choose a country/region:", cities)

    # sliders for hazard inputs
    magnitude = st.sidebar.slider("Earthquake Magnitude", 5.0, 10.0, 8.5, 0.1)
    max_height = st.sidebar.slider("Max Water Height (m)", 0.0, 40.0, 5.0, 0.5)
    runups = st.sidebar.slider("Number of Runups", 0, 50, 5, 1)
    deposits = st.sidebar.slider("Deposits (proxy severity)", 0, 5, 2, 1)
    total_exposed = st.sidebar.number_input(
        "Total Exposed Assets (USD)", min_value=1e9, max_value=1e13, value=5e12, step=1e9
    )

    # --- Run model ---
    scenario = pd.DataFrame({
        "Earthquake Magnitude": [magnitude],
        "Maximum Water Height (m)": [max_height],
        "Number of Runups": [runups],
        "Deposits": [deposits],
    })
    
    scenario_row = {
    "Earthquake Magnitude": magnitude,
    "Maximum Water Height (m)": max_height,
    "Number of Runups": runups,
    "Deposits": deposits,
}
    new_scenario_df = pd.DataFrame([scenario_row])
    df_with_scenario = pd.concat([df,new_scenario_df], ignore_index=True)
    scored = compute_damage_score(df_with_scenario)
    damage_score = float(scored["Damage Score"].iloc[-1])

    estimated_loss = estimate_loss_from_score(damage_score, total_exposed)

    st.subheader("Simulation Report")
    st.write(f"**Region Selected:** {selected_city}")
    st.metric("Damage Score", f"{damage_score:.2f}")
    st.metric("Estimated Loss", f"${estimated_loss:,.0f}")

    # --- Optional map of city points ---
    if not df[df["Country"] == selected_city].empty and "Latitude" in df and "Longitude" in df:
        city_data = df[df["Country"] == selected_city].copy()
        city_data = city_data.rename(columns={"Latitude": "lat", "Longitude": "lon"})
        st.map(city_data[["lat", "lon"]])


def run_cli_ui():
    print("Tsunami Impact Simulator (CLI Mode)")
    city = input("Enter a country/region name: ")

    mag = float(input("Enter earthquake magnitude (e.g., 8.5): "))
    height = float(input("Enter max water height (m): "))
    runups = int(input("Enter number of runups: "))
    deposits = int(input("Enter deposits proxy (0–5): "))
    total_exposed = float(input("Enter total exposed assets (USD): "))
    
    DEFAULT_WEIGHTS = {
    "magnitude": 0.3,
    "max_height": 0.3,
    "runups": 0.2,
    "deposits": 0.2
    }

    scenario = pd.DataFrame({
        "Location": [city],
        "Earthquake Magnitude": [mag],
        "Maximum Water Height (m)": [height],
        "Number of Runups": [runups],
        "Deposits": [deposits],
    })

    df_with_scenario = pd.concat([df, scenario], ignore_index=True)
    scored = compute_damage_score(df_with_scenario)
    damage_score = float(scored["Damage Score"].iloc[-1])

    estimated_loss = estimate_loss_from_score(damage_score, total_exposed)

    print("\nSimulation Report")
    print(f"Region: {city}")
    print(f"Damage Score: {damage_score:.2f}")
    print(f"Estimated Loss: ${estimated_loss:,.0f}")
    
    save_option = input("Save results to JSON? (y/n): ").strip().lower()
    if save_option == 'y':
        result_row = pd.DataFrame([{
            "Location": city,
            "Earthquake Magnitude": mag,
            "Maximum Water Height (m)": height,
            "Number of Runups": runups,
            "Deposits": deposits,
            "Damage Score": damage_score,
            "Estimated Loss": estimated_loss
        }])
        save_to_json(result_row)


if __name__ == "__main__":
    try:
        import streamlit.runtime.scriptrunner as scriptrunner
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx() is not None:
            run_streamlit_ui()
        else:
            run_cli_ui()
    except Exception:
        run_cli_ui()
