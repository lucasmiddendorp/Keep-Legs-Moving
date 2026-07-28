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


def render():
    st.title("🏁 Pacing Comparison Tool")

    with st.expander("⚙️ Pacing Settings", expanded=False):
        settings = PacingSettings.from_ui()
    pc = PacingComparison(settings)

    # =========================================================
    # FILE UPLOAD
    # =========================================================
    uploaded_file = st.file_uploader("Upload FIT file", type=["fit"])

    if uploaded_file is None:
        st.info("Upload a FIT file to generate pacing analysis.")
        return

    # =========================================================
    # RUN PIPELINE
    # =========================================================
    with st.spinner("Processing route and running pacing model..."):
        result = pc.run_all(uploaded_file)

    summary = result["summary"]
    modeled = result["modeled"]

    # =========================================================
    # SUMMARY METRICS
    # =========================================================
    st.subheader("📊 Summary")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Distance (km)", summary["distance_km"])
    col2.metric("Time (min)", summary["time_min"])
    col3.metric("Avg Power (W)", summary["avg_power_w"])
    col4.metric("NP (W)", round(summary["np_w"], 1))


    # =========================================================
    # PLOTS
    # =========================================================
    st.subheader("📈 Analysis")

    tab1, tab2, tab3, tab4 = st.tabs([
        "Power", "Speed", "Elevation", "Route"
    ])

    with tab1:
        pc.plot_power(modeled)

    with tab2:
        pc.plot_speed(modeled)

    with tab3:
        pc.plot_elevation(modeled)

    with tab4:
        pc.plot_route(result["points"])

    # =========================================================
    # CHEAT SHEET (optional but very useful)
    # =========================================================
    st.subheader("🧠 Pacing Cheat Sheet")

    cheat = pc.pacing.pacing_cheat_sheet(modeled, settings)
    st.dataframe(cheat, use_container_width=True)

    # =========================================================
    # SECTION BREAKDOWN
    # =========================================================
    st.subheader("🗺 Course Sections")

    sections = pc.pacing.course_section_summary(modeled)
    st.dataframe(sections, use_container_width=True)

