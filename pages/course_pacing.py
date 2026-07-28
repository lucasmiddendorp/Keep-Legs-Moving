
import streamlit as st
import pandas as pd
import numpy as np
import Strava.strava_config as strava_config
import os
import math
import subprocess
import sys
import xml.etree.ElementTree as ET
import plotly.graph_objects as go
from datetime import date


from helpers.pacing import Pacing
from helpers.get_pacing_settings import PacingSettings
from helpers.compare_pacing import PacingComparison

from helpers.metrics import rolling_km


def render():
    progress = st.progress(0)
    status = st.empty()
    st.title("Course Pacing Model")

    uploaded_file = st.file_uploader("Import GPX file", type=["gpx"])

    st.sidebar.header("Smoothing")
    smooth_km = st.sidebar.slider(
        "Rolling average window (km)",
        min_value=0.1,
        max_value=10.0,
        value=2.0,
        step=0.1,
    )


    settings = PacingSettings.from_sidebar()
    pacing = Pacing(settings)
    if uploaded_file is None:
        st.info("Upload a GPX route with elevation data to estimate pacing and course time.")
        return

    try:    
        status.text("Parsing GPX...")
        points = pacing.parse_gpx(uploaded_file)
        progress.progress(0.10)
    except ET.ParseError:
        st.error("This GPX file could not be parsed.")
        return

    if len(points) < 2:
        st.warning("The GPX file does not contain enough route points.")
        return

    if points["ele"].isna().any():
        st.warning("Some GPX points are missing elevation. The model needs elevation for reliable climbing and descending estimates.")
        points["ele"] = points["ele"].interpolate().bfill().ffill()

    status.text("Modeling course pacing...")
    segments = pacing.build_route_segments(points)
    progress.progress(0.30)
    if segments.empty:
        st.warning("The GPX route does not contain enough distance between points to model.")
        return
    
    status.text("Estimating pacing...")
    modeled = pacing.estimate_course_pacing(segments, settings)
    progress.progress(0.80)

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

    modeled["power_smooth"] = rolling_km(modeled, "target_power_w", smooth_km)
    modeled["speed_smooth"] = rolling_km(modeled, "speed_kmh", smooth_km)
    modeled["elev_smooth"] = rolling_km(modeled, "end_elevation_m", smooth_km)
        
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=modeled["distance_km"],
            y=modeled["power_smooth"],
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
            y=modeled["speed_smooth"],
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
            y=modeled["elev_smooth"],
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
            range=[0, modeled["target_power_w"].max() * 1.1],
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
    st.dataframe(settings.assumptions_dataframe(), width="stretch", hide_index=True)

    st.subheader("Course Power Cheat Sheet")
    st.dataframe(
        pacing.pacing_cheat_sheet(modeled, settings),
        width="stretch",
        hide_index=True,
    )

    st.subheader("Course Sections")
    section_summary = pacing.course_section_summary(modeled, min_distance_km=PacingSettings.MIN_SECTION_DISTANCE_KM)
    if section_summary.empty:
        st.info(f"No climb, descent, or flat/rolling sections longer than {PacingSettings.MIN_SECTION_DISTANCE_KM:.1f} km.")
    else:
        st.dataframe(section_summary, width="stretch", hide_index=True)

    print("Mean speed:", modeled["speed_kmh"].mean())
    print("Time weighted speed:",
      modeled["distance_m"].sum() /
      modeled["segment_time_s"].sum() * 3.6)
    
