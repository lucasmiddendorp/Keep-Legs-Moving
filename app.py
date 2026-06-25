import streamlit as st
import pandas as pd
import numpy as np
import config
import os
import math
import subprocess
import sys
import xml.etree.ElementTree as ET
import plotly.graph_objects as go
from datetime import date

st.set_page_config(layout="wide")

G = 9.80665


def haversine_m(lat1, lon1, lat2, lon2):
    radius = 6371000
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return radius * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def bearing_deg(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def parse_gpx(uploaded_file):
    root = ET.fromstring(uploaded_file.getvalue())
    points = []

    for point in root.iter():
        tag = point.tag.split("}")[-1]
        if tag not in {"trkpt", "rtept"}:
            continue

        lat = float(point.attrib["lat"])
        lon = float(point.attrib["lon"])
        ele = np.nan
        for child in point:
            if child.tag.split("}")[-1] == "ele" and child.text:
                ele = float(child.text)
                break
        points.append({"lat": lat, "lon": lon, "ele": ele})

    return pd.DataFrame(points)


def build_route_segments(points):
    rows = []
    for idx in range(len(points) - 1):
        start = points.iloc[idx]
        end = points.iloc[idx + 1]
        distance = haversine_m(start["lat"], start["lon"], end["lat"], end["lon"])
        if distance < 1:
            continue

        elevation_gain = end["ele"] - start["ele"]
        rows.append(
            {
                "distance_m": distance,
                "start_elevation_m": start["ele"],
                "end_elevation_m": end["ele"],
                "elevation_change_m": elevation_gain,
                "grade": np.clip(elevation_gain / distance, -0.25, 0.25),
                "bearing": bearing_deg(start["lat"], start["lon"], end["lat"], end["lon"]),
            }
        )

    segments = pd.DataFrame(rows)
    if segments.empty:
        return segments

    segments["distance_km"] = segments["distance_m"].cumsum() / 1000
    return segments


def wheel_power_required(speed, grade, mass, cda, crr, rho, drivetrain_efficiency, wind_speed, wind_from_deg, bearing):
    slope_angle = math.atan(grade)
    headwind = wind_speed * math.cos(math.radians(wind_from_deg - bearing))
    apparent_air_speed = max(0.0, speed + headwind)
    gravity_power = mass * G * math.sin(slope_angle) * speed
    rolling_power = mass * G * math.cos(slope_angle) * crr * speed
    aero_power = 0.5 * rho * cda * apparent_air_speed**2 * speed
    wheel_power = gravity_power + rolling_power + aero_power
    return wheel_power / drivetrain_efficiency


def solve_speed_for_power(target_power, grade, mass, cda, crr, rho, drivetrain_efficiency, wind_speed, wind_from_deg, bearing, max_speed):
    low = 0.1
    high = max_speed
    if wheel_power_required(high, grade, mass, cda, crr, rho, drivetrain_efficiency, wind_speed, wind_from_deg, bearing) <= target_power:
        return high

    for _ in range(45):
        mid = (low + high) / 2
        required = wheel_power_required(
            mid, grade, mass, cda, crr, rho, drivetrain_efficiency, wind_speed, wind_from_deg, bearing
        )
        if required > target_power:
            high = mid
        else:
            low = mid

    return low


def normalized_power(power, duration_s):
    if len(power) == 0:
        return np.nan

    samples = []
    for watts, seconds in zip(power, duration_s):
        repeat = max(1, int(round(seconds / 5)))
        samples.extend([watts] * repeat)

    power_series = pd.Series(samples)
    rolling_30s = power_series.rolling(6, min_periods=1).mean()
    return (rolling_30s.pow(4).mean()) ** 0.25


def estimate_course_pacing(segments, settings):
    modeled = segments.copy()
    total_mass = settings["rider_weight"] + settings["bike_weight"] + settings["gear_weight"]
    ftp = settings["ftp"]
    target_np = ftp * settings["target_if"]
    max_power = ftp * settings["max_ftp_fraction"]
    min_power = ftp * settings["min_ftp_fraction"]

    load_scores = []
    for _, segment in modeled.iterrows():
        reference_power = wheel_power_required(
            settings["reference_speed_kmh"] / 3.6,
            segment["grade"],
            total_mass,
            settings["cda"],
            settings["crr"],
            settings["air_density"],
            settings["drivetrain_efficiency"],
            settings["wind_speed"],
            settings["wind_from_deg"],
            segment["bearing"],
        )
        load_scores.append(max(0.0, reference_power))

    load_scores = np.asarray(load_scores)
    if np.nanmax(load_scores) > 0:
        load_scores = (load_scores - np.nanmedian(load_scores)) / (np.nanpercentile(load_scores, 90) - np.nanmedian(load_scores) + 1e-9)
    else:
        load_scores = np.zeros(len(modeled))

    # Allocate more power where extra watts buy more time: climbs, rough/high-resistance sections, and headwinds.
    power_shape = 1 + settings["pacing_aggression"] * np.clip(load_scores, -0.6, 1.2)
    power_shape = np.clip(power_shape, settings["min_ftp_fraction"] / settings["target_if"], settings["max_ftp_fraction"] / settings["target_if"])

    best_powers = np.full(len(modeled), target_np)
    best_speeds = np.zeros(len(modeled))
    best_np = target_np

    low_scale = 0.5
    high_scale = 1.5
    for _ in range(35):
        scale = (low_scale + high_scale) / 2
        powers = np.clip(target_np * power_shape * scale, min_power, max_power)

        speeds = []
        for power, (_, segment) in zip(powers, modeled.iterrows()):
            speeds.append(
                solve_speed_for_power(
                    power,
                    segment["grade"],
                    total_mass,
                    settings["cda"],
                    settings["crr"],
                    settings["air_density"],
                    settings["drivetrain_efficiency"],
                    settings["wind_speed"],
                    settings["wind_from_deg"],
                    segment["bearing"],
                    settings["max_speed_kmh"] / 3.6,
                )
            )

        duration_s = modeled["distance_m"].to_numpy() / np.asarray(speeds)
        current_np = normalized_power(powers, duration_s)
        best_powers = powers
        best_speeds = np.asarray(speeds)
        best_np = current_np

        if current_np > target_np:
            high_scale = scale
        else:
            low_scale = scale

    modeled["target_power_w"] = best_powers
    modeled["speed_kmh"] = best_speeds * 3.6
    modeled["segment_time_s"] = modeled["distance_m"] / best_speeds
    modeled["elapsed_time_s"] = modeled["segment_time_s"].cumsum()
    modeled.attrs["target_np"] = target_np
    modeled.attrs["modeled_np"] = best_np
    return modeled


def time_weighted_average(values, weights):
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    valid = ~np.isnan(values) & ~np.isnan(weights) & (weights > 0)
    if not valid.any():
        return np.nan
    return np.average(values[valid], weights=weights[valid])


def wind_component_kmh(row, settings):
    headwind_ms = settings["wind_speed"] * math.cos(math.radians(settings["wind_from_deg"] - row["bearing"]))
    return headwind_ms * 3.6


def pacing_cheat_sheet(modeled, settings):
    category_order = [
        "Flat/Roll\nHeadwind",
        "Flat/Roll\nTailwind",
        "Flat/Roll\nCrosswind",
        "Minor Hill\n(1-2%)",
        "Medium Hill\n(2-4%)",
        "Major Hill\n(4-6%)",
        "Extreme Hill\n(>6%)",
        "Minor\nDescent",
    ]

    cheat = modeled.copy()
    cheat["grade_percent"] = cheat["grade"] * 100
    cheat["headwind_kmh"] = cheat.apply(lambda row: wind_component_kmh(row, settings), axis=1)

    def category(row):
        grade = row["grade_percent"]
        if grade <= -1:
            return "Minor\nDescent"
        if grade >= 6:
            return "Extreme Hill\n(>6%)"
        if grade >= 4:
            return "Major Hill\n(4-6%)"
        if grade >= 2:
            return "Medium Hill\n(2-4%)"
        if grade >= 1:
            return "Minor Hill\n(1-2%)"
        if row["headwind_kmh"] >= 2:
            return "Flat/Roll\nHeadwind"
        if row["headwind_kmh"] <= -2:
            return "Flat/Roll\nTailwind"
        return "Flat/Roll\nCrosswind"

    cheat["category"] = cheat.apply(category, axis=1)
    rows = []
    for category_name in category_order:
        category_rows = cheat[cheat["category"] == category_name]
        watts = time_weighted_average(category_rows["target_power_w"], category_rows["segment_time_s"])
        rows.append(
            {
                "CATEGORY": category_name,
                "WATTS": "" if np.isnan(watts) else int(round(watts)),
            }
        )

    return pd.DataFrame(rows)


def course_section_summary(modeled, min_distance_km=1.0):
    sections = modeled.copy()
    smoothing_window = max(3, min(21, len(sections) // 60))
    if smoothing_window % 2 == 0:
        smoothing_window += 1
    sections["smoothed_grade"] = sections["grade"].rolling(smoothing_window, min_periods=1, center=True).mean()

    def terrain_type(grade):
        if grade >= 0.015:
            return "Climb"
        if grade <= -0.015:
            return "Descent"
        return "Flat/Roll"

    sections["terrain"] = sections["smoothed_grade"].apply(terrain_type)
    sections["section_id"] = (sections["terrain"] != sections["terrain"].shift()).cumsum()

    rows = []
    for _, section in sections.groupby("section_id", sort=False):
        distance_km = section["distance_m"].sum() / 1000
        if distance_km < min_distance_km:
            continue

        start_km = section["distance_km"].iloc[0] - section["distance_m"].iloc[0] / 1000
        end_km = section["distance_km"].iloc[-1]
        time_s = section["segment_time_s"].sum()
        elevation_change_m = section["elevation_change_m"].sum()
        avg_grade = elevation_change_m / section["distance_m"].sum() * 100
        avg_watts = time_weighted_average(section["target_power_w"], section["segment_time_s"])
        avg_speed = distance_km / (time_s / 3600)

        rows.append(
            {
                "Type": section["terrain"].iloc[0],
                "Start km": round(start_km, 2),
                "End km": round(end_km, 2),
                "Distance km": round(distance_km, 2),
                "Avg grade %": round(avg_grade, 1),
                "Elevation change m": round(elevation_change_m, 0),
                "Avg watts": int(round(avg_watts)),
                "Avg speed km/h": round(avg_speed, 1),
                "Time min": round(time_s / 60, 1),
            }
        )

    return pd.DataFrame(rows)


def run_strava_update():
    return subprocess.run(
        [sys.executable, "strava_client.py"],
        cwd=os.getcwd(),
        capture_output=True,
        text=True,
        timeout=900,
        errors="replace",
    )


def format_duration(seconds):
    if pd.isna(seconds):
        return ""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"


def render_course_pacing_page():
    st.title("Course Pacing Model")

    uploaded_file = st.file_uploader("Import GPX file", type=["gpx"])

    st.sidebar.header("Rider And Bike")
    rider_weight = st.sidebar.number_input("Rider weight (kg)", min_value=30.0, max_value=130.0, value=75.0, step=0.5)
    bike_weight = st.sidebar.number_input("Bike weight (kg)", min_value=4.0, max_value=25.0, value=8.0, step=0.5)
    gear_weight = st.sidebar.number_input("Bottles and gear (kg)", min_value=0.0, max_value=20.0, value=2.0, step=0.5)

    st.sidebar.header("NP Pacing Target")
    pacing_ftp = st.sidebar.number_input("FTP (W)", min_value=100, max_value=600, value=int(config.FTP), step=5)
    target_if_percent = st.sidebar.number_input("Target IF (% FTP)", min_value=40, max_value=120, value=82, step=1)
    max_ftp_percent = st.sidebar.number_input("Max short effort (% FTP)", min_value=target_if_percent, max_value=180, value=115, step=1)
    min_ftp_percent = st.sidebar.number_input("Minimum pedaling (% FTP)", min_value=0, max_value=target_if_percent, value=25, step=1)
    pacing_aggression = st.sidebar.slider("Pacing variability", min_value=0.0, max_value=1.0, value=0.45, step=0.05)
    min_section_km = st.sidebar.number_input("Minimum section length (km)", min_value=0.2, max_value=10.0, value=1.0, step=0.1)
    max_speed_kmh = st.sidebar.number_input("Max descending speed (km/h)", min_value=20.0, max_value=120.0, value=75.0, step=1.0)

    st.sidebar.header("Model Assumptions")
    cda = st.sidebar.number_input("CdA (m2)", min_value=0.15, max_value=0.70, value=0.32, step=0.01)
    crr = st.sidebar.number_input("Rolling resistance Crr", min_value=0.0010, max_value=0.0200, value=0.0045, step=0.0005, format="%.4f")
    drivetrain_efficiency = st.sidebar.number_input("Drivetrain efficiency", min_value=0.85, max_value=1.00, value=0.975, step=0.005)
    air_density = st.sidebar.number_input("Air density (kg/m3)", min_value=0.90, max_value=1.35, value=1.18, step=0.01)
    wind_speed_kmh = st.sidebar.number_input("Wind speed (km/h)", min_value=0.0, max_value=80.0, value=0.0, step=1.0)
    wind_from_deg = st.sidebar.number_input("Wind from direction (degrees)", min_value=0, max_value=359, value=0, step=5)

    settings = {
        "rider_weight": rider_weight,
        "bike_weight": bike_weight,
        "gear_weight": gear_weight,
        "ftp": pacing_ftp,
        "target_if": target_if_percent / 100,
        "max_ftp_fraction": max_ftp_percent / 100,
        "min_ftp_fraction": min_ftp_percent / 100,
        "pacing_aggression": pacing_aggression,
        "reference_speed_kmh": 35,
        "max_speed_kmh": max_speed_kmh,
        "cda": cda,
        "crr": crr,
        "drivetrain_efficiency": drivetrain_efficiency,
        "air_density": air_density,
        "wind_speed": wind_speed_kmh / 3.6,
        "wind_from_deg": wind_from_deg,
    }

    if uploaded_file is None:
        st.info("Upload a GPX route with elevation data to estimate pacing and course time.")
        return

    try:
        points = parse_gpx(uploaded_file)
    except ET.ParseError:
        st.error("This GPX file could not be parsed.")
        return

    if len(points) < 2:
        st.warning("The GPX file does not contain enough route points.")
        return

    if points["ele"].isna().any():
        st.warning("Some GPX points are missing elevation. The model needs elevation for reliable climbing and descending estimates.")
        points["ele"] = points["ele"].interpolate().bfill().ffill()

    segments = build_route_segments(points)
    if segments.empty:
        st.warning("The GPX route does not contain enough distance between points to model.")
        return

    modeled = estimate_course_pacing(segments, settings)

    total_distance_km = modeled["distance_m"].sum() / 1000
    total_time_s = modeled["segment_time_s"].sum()
    elevation_gain_m = modeled.loc[modeled["elevation_change_m"] > 0, "elevation_change_m"].sum()
    avg_speed_kmh = total_distance_km / (total_time_s / 3600)
    modeled_np = modeled.attrs["modeled_np"]
    target_np = modeled.attrs["target_np"]

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Distance", f"{total_distance_km:.1f} km")
    col2.metric("Estimated Time", f"{int(total_time_s // 3600)}h {int((total_time_s % 3600) // 60)}m")
    col3.metric("Avg Speed", f"{avg_speed_kmh:.1f} km/h")
    col4.metric("Modeled NP", f"{modeled_np:.0f} W", f"target {target_np:.0f} W")
    col5.metric("Elevation Gain", f"{elevation_gain_m:.0f} m")

    st.subheader("Route Profile And Pacing")
    smoothing_window = max(3, min(31, len(modeled) // 40))
    if smoothing_window % 2 == 0:
        smoothing_window += 1
    modeled["smoothed_speed_kmh"] = (
        modeled["speed_kmh"]
        .rolling(window=smoothing_window, min_periods=1, center=True)
        .mean()
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=modeled["distance_km"],
            y=modeled["target_power_w"],
            name="Power",
            mode="lines",
            line=dict(color="rgba(134, 188, 203, 0.75)", width=1, shape="hv"),
            fill="tozeroy",
            fillcolor="rgba(134, 188, 203, 0.35)",
            hovertemplate="<b>Distance</b>: %{x:.2f} km<br><b>Power</b>: %{y:.0f} W<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=modeled["distance_km"],
            y=modeled["smoothed_speed_kmh"],
            name="Speed",
            yaxis="y2",
            mode="lines",
            line=dict(color="#ff7f0e", width=2.5),
            hovertemplate="<b>Distance</b>: %{x:.2f} km<br><b>Speed</b>: %{y:.1f} km/h<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=modeled["distance_km"],
            y=modeled["end_elevation_m"],
            name="Elevation",
            yaxis="y3",
            mode="lines",
            line=dict(color="#1e90ff", width=2.5),
            hovertemplate="<b>Distance</b>: %{x:.2f} km<br><b>Elevation</b>: %{y:.0f} m<extra></extra>",
        )
    )
    fig.update_layout(
        height=520,
        margin=dict(l=65, r=130, t=35, b=55),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis_title="Distance (km)",
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            rangeslider=dict(visible=True, thickness=0.06),
        ),
        yaxis=dict(
            title=dict(text="Power (watts)", font=dict(color="#2459a6")),
            tickfont=dict(color="#2459a6"),
            showgrid=True,
            gridcolor="rgba(0, 0, 0, 0.12)",
            zeroline=False,
            rangemode="tozero",
        ),
        yaxis2=dict(
            title=dict(text="Speed (km/h)", font=dict(color="#ff7f0e")),
            tickfont=dict(color="#ff7f0e"),
            overlaying="y",
            side="right",
            showgrid=False,
            zeroline=False,
            rangemode="tozero",
        ),
        yaxis3=dict(
            title=dict(text="Elevation (m)", font=dict(color="#1e90ff")),
            tickfont=dict(color="#1e90ff"),
            overlaying="y",
            side="right",
            anchor="free",
            position=1.0,
            showgrid=False,
            zeroline=False,
            rangemode="tozero",
        ),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    st.caption("Drag across the chart or use the range slider to inspect a route section.")
    st.plotly_chart(fig, width="stretch")

    st.subheader("Assumptions")
    assumptions = pd.DataFrame(
        [
            ("Total system mass", f"{rider_weight + bike_weight + gear_weight:.1f} kg"),
            ("Rolling resistance", f"Crr {crr:.4f}"),
            ("Aerodynamics", f"CdA {cda:.2f} m2"),
            ("Drivetrain efficiency", f"{drivetrain_efficiency * 100:.1f}%"),
            ("Air density", f"{air_density:.2f} kg/m3"),
            ("Wind vector", f"{wind_speed_kmh:.1f} km/h from {wind_from_deg} degrees"),
            ("FTP", f"{pacing_ftp:.0f} W"),
            ("Target Normalized Power", f"{target_np:.0f} W ({target_if_percent:.0f}% FTP)"),
            ("Short-effort cap", f"{pacing_ftp * max_ftp_percent / 100:.0f} W ({max_ftp_percent:.0f}% FTP)"),
            ("Minimum pedaling floor", f"{pacing_ftp * min_ftp_percent / 100:.0f} W ({min_ftp_percent:.0f}% FTP)"),
            ("Pacing variability", f"{pacing_aggression:.2f}; higher values bias more power toward slower, higher-resistance segments"),
            ("Speed cap", f"{max_speed_kmh:.1f} km/h"),
            ("NP model", "Power is shaped by route resistance, capped by max FTP %, then scaled until estimated NP matches the target IF."),
            ("Model scope", "Steady-state physics per GPX segment; no braking model, cornering limits, traffic, road surface changes, altitude-varying air density, W prime, stochastic gusts, or formal Best Bike Split optimization."),
        ],
        columns=["Assumption", "Value"],
    )
    st.dataframe(assumptions, width="stretch", hide_index=True)

    st.subheader("Course Power Cheat Sheet")
    st.dataframe(
        pacing_cheat_sheet(modeled, settings),
        width="stretch",
        hide_index=True,
    )

    st.subheader("Course Sections")
    section_summary = course_section_summary(modeled, min_distance_km=min_section_km)
    if section_summary.empty:
        st.info(f"No climb, descent, or flat/rolling sections longer than {min_section_km:.1f} km.")
    else:
        st.dataframe(section_summary, width="stretch", hide_index=True)


page = st.sidebar.radio("Page", ["Training Dashboard", "Course Pacing"])

st.markdown("""
<style>
.block-container {
    max-width: 95vw;
    padding-left: 2rem;
    padding-right: 2rem;
}
</style>
""", unsafe_allow_html=True)

if page == "Course Pacing":
    render_course_pacing_page()
    st.stop()

st.title("Cycling Training Dashboard")

# SETTINGS
ftp = st.sidebar.number_input("FTP", value=340)

st.sidebar.header("Data Sync")
if st.sidebar.button("Update Strava Data", type="primary"):
    with st.spinner("Fetching latest Strava activities and power streams..."):
        try:
            update_result = run_strava_update()
        except subprocess.TimeoutExpired:
            st.session_state["strava_update_status"] = "timeout"
            st.session_state["strava_update_output"] = "The Strava update timed out after 15 minutes."
        except Exception as exc:
            st.session_state["strava_update_status"] = "error"
            st.session_state["strava_update_output"] = str(exc)
        else:
            st.session_state["strava_update_status"] = "success" if update_result.returncode == 0 else "error"
            st.session_state["strava_update_output"] = "\n".join(
                part for part in [update_result.stdout, update_result.stderr] if part
            )
            if update_result.returncode == 0:
                st.cache_data.clear()
        st.rerun()

if "strava_update_status" in st.session_state:
    if st.session_state["strava_update_status"] == "success":
        st.sidebar.success("Strava data updated.")
    elif st.session_state["strava_update_status"] == "timeout":
        st.sidebar.warning("Strava update timed out.")
    else:
        st.sidebar.error("Strava update failed.")

    with st.sidebar.expander("Update log"):
        st.code(st.session_state.get("strava_update_output", "No output captured."))

CTL_TC = config.CTL_TIME_CONSTANT
ATL_TC = config.ATL_TIME_CONSTANT


# LOAD DATA
df = pd.read_csv("activities_cache.csv")
df["date"] = pd.to_datetime(df["date"], format="mixed", errors="coerce")
df = df.dropna(subset=["date"])

# CALCULATIONS
df["IF"] = df["weighted_average_watts"] / ftp
df["TSS"] = (df["moving_time"] * df["weighted_average_watts"] * df["IF"]) / (ftp * 3600) * 100

# DAILY AGGREGATION
daily = (
    df.groupby(pd.Grouper(key="date", freq="D"))["TSS"]
    .sum()
    .to_frame()
    .asfreq("D", fill_value=0)
)

# Extend to today so CTL/ATL/TSB decay forward from last training day
today = pd.Timestamp(date.today())
if daily.index[-1] < today:
    daily = daily.reindex(
        pd.date_range(daily.index[0], today, freq="D"),
        fill_value=0
    )

# CTL ATL TSB
daily["CTL"] = daily["TSS"].ewm(span=CTL_TC).mean()
daily["ATL"] = daily["TSS"].ewm(span=ATL_TC).mean()
daily["TSB"] = daily["CTL"].shift(1) - daily["ATL"].shift(1)

# DATE RANGE SELECTOR
st.sidebar.header("Date Range")

start_date = st.sidebar.date_input(
    "Start date",
    daily.index.min()
)

end_date = st.sidebar.date_input(
    "End date",
    value=date.today(),
)

rolling_days = st.sidebar.slider("Rolling Average", min_value=1, max_value=28, value=1, step=1, format="%d days")

filtered = daily.loc[pd.Timestamp(start_date):pd.Timestamp(end_date)]

smoothed = filtered.copy()
if rolling_days > 1:
    smoothed["CTL"] = filtered["CTL"].rolling(rolling_days, min_periods=1, center=True).mean()
    smoothed["ATL"] = filtered["ATL"].rolling(rolling_days, min_periods=1, center=True).mean()
    smoothed["TSB"] = filtered["TSB"].rolling(rolling_days, min_periods=1, center=True).mean()
    
# DASHBOARD

# --- CSS for vertical alignment ---
st.markdown("""
<style>
div[data-testid="stMetric"] {
    text-align: center;
}
.centered {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100%;
}
</style>
""", unsafe_allow_html=True)

ctl = daily["CTL"].iloc[-1]
atl = daily["ATL"].iloc[-1]
tsb = daily["TSB"].iloc[-1]
ctl_7_days_ago = daily["CTL"].iloc[-8] if len(daily) >= 8 else daily["CTL"].iloc[0]
atl_7_days_ago = daily["ATL"].iloc[-8] if len(daily) >= 8 else daily["ATL"].iloc[0]
tsb_history = daily["TSB"].dropna()
tsb_7_days_ago = tsb_history.iloc[-8] if len(tsb_history) >= 8 else (tsb_history.iloc[0] if len(tsb_history) else tsb)
fitness_delta = ctl - ctl_7_days_ago
fatigue_delta = atl - atl_7_days_ago
form_delta = tsb - tsb_7_days_ago
fitness_ramp_rate = fitness_delta / 7

if fitness_ramp_rate < 0:
    ramp_label = "Recovering"
    ramp_position = 12
elif fitness_ramp_rate < 0.4:
    ramp_label = "Building"
    ramp_position = 38
elif fitness_ramp_rate < 0.8:
    ramp_label = "Productive"
    ramp_position = 64
else:
    ramp_label = "Going Hard"
    ramp_position = 88

if tsb < -30:
    readiness_label = "Recovery Needed"
    readiness_note = "Very negative form. Keep today easy or rest."
    readiness_color = "#ef4444"
elif tsb < -10:
    readiness_label = "Train With Care"
    readiness_note = "Useful load, but fatigue is high."
    readiness_color = "#f97316"
elif tsb < 10:
    readiness_label = "Ready To Train"
    readiness_note = "Balanced enough for quality work."
    readiness_color = "#2563eb"
elif tsb <= 25:
    readiness_label = "Race Ready"
    readiness_note = "Fresh and sharp."
    readiness_color = "#16a34a"
else:
    readiness_label = "Very Fresh"
    readiness_note = "You may be under-loaded."
    readiness_color = "#7c3aed"

if atl < 40:
    fatigue_label = "Low"
elif atl < 75:
    fatigue_label = "Moderate"
elif atl < 110:
    fatigue_label = "High"
else:
    fatigue_label = "Very High"

st.markdown("""
<style>
.insight-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.75rem;
    margin-bottom: 0.75rem;
}
.insight-card {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.85rem 1rem;
    background: #ffffff;
    box-shadow: 0 1px 4px rgba(15, 23, 42, 0.06);
}
.insight-card.primary {
    border: 2px solid #5b74ff;
}
.insight-value {
    font-size: 2.1rem;
    font-weight: 800;
    line-height: 1;
}
.insight-label {
    margin-top: 0.35rem;
    color: #475569;
    font-weight: 700;
}
.insight-row {
    display: grid;
    grid-template-columns: minmax(280px, 1.1fr) minmax(280px, 1fr) minmax(220px, 0.8fr);
    gap: 0.75rem;
    margin-bottom: 1.5rem;
}
.wide-insight {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.9rem 1rem 1rem;
    background: #ffffff;
    box-shadow: 0 1px 4px rgba(15, 23, 42, 0.06);
}
.wide-insight-title {
    color: #334155;
    font-size: 0.95rem;
    font-weight: 800;
}
.wide-insight-main {
    margin-top: 0.35rem;
    font-size: 1.45rem;
    font-weight: 800;
}
.wide-insight-note {
    margin-top: 0.25rem;
    color: #64748b;
    font-size: 0.9rem;
}
.ramp-track {
    position: relative;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 3px;
    margin-top: 1.05rem;
}
.ramp-segment {
    height: 5px;
    border-radius: 99px;
    background: #c7d2fe;
}
.ramp-segment:nth-child(2) { background: #93c5fd; }
.ramp-segment:nth-child(3) { background: #60a5fa; }
.ramp-segment:nth-child(4) { background: #2563eb; }
.ramp-marker {
    position: absolute;
    top: -9px;
    width: 0;
    height: 0;
    border-left: 8px solid transparent;
    border-right: 8px solid transparent;
    border-top: 10px solid #1d4ed8;
    transform: translateX(-50%);
}
.ramp-labels {
    display: flex;
    justify-content: space-between;
    margin-top: 0.35rem;
    color: #64748b;
    font-size: 0.82rem;
}
</style>
""", unsafe_allow_html=True)

st.subheader("Performance Insights")
st.markdown(
    f"""
    <div class="insight-grid">
        <div class="insight-card primary">
            <div class="insight-value" style="color:#1d4ed8;">{ctl:.0f} {'↑' if fitness_delta >= 0 else '↓'}</div>
            <div class="insight-label">Fitness</div>
        </div>
        <div class="insight-card">
            <div class="insight-value" style="color:#f97316;">{tsb:.0f} {'↑' if form_delta >= 0 else '↓'}</div>
            <div class="insight-label">Form</div>
        </div>
        <div class="insight-card">
            <div class="insight-value" style="color:#db2777;">{atl:.0f} {'↑' if fatigue_delta >= 0 else '↓'}</div>
            <div class="insight-label">Fatigue</div>
        </div>
    </div>
    <div class="insight-row">
        <div class="wide-insight">
            <div class="wide-insight-title">Fitness Ramp Rate</div>
            <div class="wide-insight-main" style="color:#1d4ed8;">{ramp_label}</div>
            <div class="wide-insight-note">{fitness_ramp_rate:+.2f} CTL/day over the last 7 days</div>
            <div class="ramp-track">
                <div class="ramp-marker" style="left:{ramp_position}%;"></div>
                <div class="ramp-segment"></div><div class="ramp-segment"></div><div class="ramp-segment"></div><div class="ramp-segment"></div>
            </div>
            <div class="ramp-labels"><span>Recovering</span><span>Building</span><span>Productive</span><span>Going Hard</span></div>
        </div>
        <div class="wide-insight">
            <div class="wide-insight-title">Today's Training Readiness</div>
            <div class="wide-insight-main" style="color:{readiness_color};">{readiness_label}</div>
            <div class="wide-insight-note">{readiness_note}</div>
        </div>
        <div class="wide-insight">
            <div class="wide-insight-title">Fatigue Level</div>
            <div class="wide-insight-main" style="color:#db2777;">{fatigue_label}</div>
            <div class="wide-insight-note">ATL {atl:.1f}, changed {fatigue_delta:+.1f} this week</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("Performance Management Chart")

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=filtered.index,
        y=filtered["TSS"],
        name="Stress (TSS)",
        mode="markers",
        marker=dict(color="#991b1b", size=4, opacity=0.75),
        yaxis="y2"
    )
)

fig.add_trace(
    go.Scatter(
        x=smoothed.index,
        y=smoothed["CTL"],
        name="Fitness (CTL)",
        mode="lines",
        line=dict(color="#5f8fb3", width=2.5),
        fill="tozeroy",
        fillcolor="rgba(95, 143, 179, 0.22)",
        hovertemplate="<b>Fitness</b>: %{y:.1f}<extra></extra>",
    )
)

fig.add_trace(
    go.Scatter(
        x=smoothed.index,
        y=smoothed["ATL"],
        name="Fatigue (ATL)",
        mode="lines",
        line=dict(color="#f0a4e8", width=1.8),
        hovertemplate="<b>Fatigue</b>: %{y:.1f}<extra></extra>",
    )
)

fig.add_trace(
    go.Scatter(
        x=smoothed.index,
        y=smoothed["TSB"],
        name="Form (TSB)",
        mode="lines",
        line=dict(color="#f2c14e", width=1.8),
        yaxis="y3",
        hovertemplate="<b>Form</b>: %{y:.1f}<extra></extra>",
    )
)

fig.update_layout(
    height=560,
    margin=dict(l=55, r=80, t=70, b=45),
    plot_bgcolor="#fffdf5",
    paper_bgcolor="#fffdf5",
    title=dict(
        text=(
            "<span style='color:#991b1b'>Stress</span> &nbsp;&nbsp; "
            "<span style='color:#d946ef'>Fatigue</span> &nbsp;&nbsp; "
            "<span style='color:#3b82a0'>Fitness</span> &nbsp;&nbsp; "
            "<span style='color:#eab308'>Form</span>"
        ),
        x=0.5,
        xanchor="center",
        font=dict(size=26),
    ),
    xaxis=dict(
        title="Date",
        showgrid=False,
        rangeslider=dict(visible=True, thickness=0.05),
    ),
    yaxis=dict(
        title="Fitness / Fatigue",
        showgrid=True,
        gridcolor="rgba(15, 23, 42, 0.10)",
        zeroline=False,
        rangemode="tozero",
    ),
    yaxis2=dict(
        title=dict(text="Stress (TSS)", font=dict(color="#991b1b")),
        tickfont=dict(color="#991b1b"),
        overlaying="y",
        side="left",
        anchor="free",
        position=0.0,
        showgrid=False,
        rangemode="tozero",
    ),
    yaxis3=dict(
        title=dict(text="Form", font=dict(color="#eab308")),
        tickfont=dict(color="#eab308"),
        overlaying="y",
        side="right",
        showgrid=False,
        zeroline=True,
        zerolinecolor="rgba(234, 179, 8, 0.35)",
    ),
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
)

st.plotly_chart(fig, width='stretch')

st.subheader("Latest Activities")
latest_activities = df.sort_values("date", ascending=False).head(12).copy()
latest_activities["Date"] = latest_activities["date"].dt.strftime("%Y-%m-%d")
latest_activities["Activity"] = latest_activities["type"].astype(str).str.replace("root='", "", regex=False).str.replace("'", "", regex=False)
latest_activities["Ride Length"] = latest_activities["distance_km"].map(lambda value: "" if pd.isna(value) else f"{value:.1f} km")
latest_activities["Time"] = latest_activities["moving_time"].map(format_duration)
latest_activities["Avg Speed"] = latest_activities["speed_kmh"].map(lambda value: "" if pd.isna(value) else f"{value:.1f} km/h")
latest_activities["Avg Watts"] = latest_activities["average_watts"].map(lambda value: "" if pd.isna(value) else f"{value:.0f} W")
latest_activities["Normalized Power"] = latest_activities["weighted_average_watts"].map(lambda value: "" if pd.isna(value) else f"{value:.0f} W")
latest_activities["TSS"] = latest_activities["TSS"].map(lambda value: "" if pd.isna(value) else f"{value:.0f}")

st.dataframe(
    latest_activities[
        ["Date", "Activity", "Ride Length", "Time", "Avg Speed", "Avg Watts", "Normalized Power", "TSS"]
    ],
    width="stretch",
    hide_index=True,
)

st.subheader("Power Curve")

DURATIONS = [
    5, 15, 30, 60, 120, 300, 600, 1200, 1800, 3600
]
duration_labels = [
    "5s", "15s", "30s", "1m", "2m", "5m", "10m", "20m", "30m", "1h"
]
POWER_STREAMS_PATH = "power_streams.parquet"

def max_avg_power(watts, duration):
    window = int(duration)
    watts = np.asarray(watts, dtype=float)
    watts = watts[~np.isnan(watts)]
    if len(watts) < window:
        return np.nan, None

    cumsum = np.concatenate(([0.0], np.cumsum(watts)))
    rolling = (cumsum[window:] - cumsum[:-window]) / window
    max_idx = int(np.argmax(rolling))
    return rolling[max_idx], max_idx + window - 1


@st.cache_data(show_spinner="Building power curve cache...")
def build_power_curve_cache(path, modified_time, durations):
    power_df = pd.read_parquet(path, columns=["activity_id", "watts"])
    rows = []

    for activity_id, activity in power_df.groupby("activity_id", sort=False):
        watts = pd.to_numeric(activity["watts"], errors="coerce").to_numpy()
        for duration in durations:
            max_power, _ = max_avg_power(watts, duration)
            if not np.isnan(max_power):
                rows.append(
                    {
                        "activity_id": activity_id,
                        "duration": duration,
                        "max_power": max_power,
                    }
                )

    return pd.DataFrame(rows, columns=["activity_id", "duration", "max_power"])


def best_power_curve(power_cache, durations):
    if power_cache.empty:
        return [np.nan] * len(durations), [None] * len(durations)

    best = (
        power_cache.sort_values(["duration", "max_power"], ascending=[True, False])
        .drop_duplicates("duration")
        .set_index("duration")
    )

    powers = []
    activity_ids = []
    for duration in durations:
        if duration in best.index:
            powers.append(best.loc[duration, "max_power"])
            activity_ids.append(best.loc[duration, "activity_id"])
        else:
            powers.append(np.nan)
            activity_ids.append(None)

    return powers, activity_ids


if os.path.exists(POWER_STREAMS_PATH):
    power_cache = build_power_curve_cache(
        POWER_STREAMS_PATH,
        os.path.getmtime(POWER_STREAMS_PATH),
        tuple(DURATIONS),
    )

    # Get filtered activity IDs (from date range)
    filtered_activity_ids = df[
        (df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))
    ]["id"].unique()

    power_cache_filtered = power_cache[power_cache["activity_id"].isin(filtered_activity_ids)]

    if len(power_cache_filtered) == 0:
        st.warning("No power stream data in selected date range.")
    else:
        power_curve, power_curve_acts = best_power_curve(power_cache_filtered, DURATIONS)
        power_curve_all, _ = best_power_curve(power_cache, DURATIONS)

        # Plot both curves (log scale, x in seconds)
        fig2 = go.Figure()
        fig2.add_trace(
            go.Scatter(
                x=DURATIONS,
                y=power_curve,
                mode="lines+markers",
                name="Power Curve (Date Range)",
                marker=dict(size=10),
            )
        )
        fig2.add_trace(
            go.Scatter(
                x=DURATIONS,
                y=power_curve_all,
                mode="lines+markers",
                name="All-Time Power Curve",
                marker=dict(size=10, symbol="circle-open"),
            )
        )
        fig2.update_layout(
            xaxis=dict(
                title="Duration",
                type="log",
                tickvals=DURATIONS,
                ticktext=duration_labels
            ),
            yaxis_title="Watts",
            title="Best Power Curve",
            legend=dict(orientation="h"),
        )

        chart_state = st.plotly_chart(
            fig2,
            width="stretch",
            key="power_curve",
            on_select="rerun",
            selection_mode="points",
            config={"displayModeBar": True},
        )

        # Handle click events
        if chart_state.selection.points:
            point = chart_state.selection.points[0]
            x_clicked = point["x"]
            # Find index in DURATIONS
            try:
                idx = DURATIONS.index(int(x_clicked))
            except (ValueError, TypeError):
                idx = None
            if idx is not None:
                activity_id = power_curve_acts[idx]
                if activity_id is not None:
                    st.markdown("#### Activity with Highest Power for Selected Duration")
                    activity_row = df[df["id"] == activity_id]
                    if not activity_row.empty:
                        activity = activity_row.iloc[0]
                        st.write({
                            "date": activity["date"],
                            "activity_id": activity["id"],
                            "name": activity.get("name", ""),
                            "moving_time (min)": round(activity["moving_time"]/60, 1),
                            "weighted_average_watts": activity.get("weighted_average_watts", None),
                            "TSS": round(activity["TSS"],1) if "TSS" in activity else None,
                        })
                    else:
                        st.info("Activity not found in dataframe.")
                else:
                    st.info("No activity found for that duration.")
else:
    st.info("No power stream data file found.")
