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

from helpers.style import red_button, apply_global_style
from helpers.metrics import calculate_training_load, rolling_km, format_duration
from Strava.strava_data import update_strava_data
from Strava.strava_user import get_user_strava, get_user_settings

from helpers.user_cache import get_user_cache_paths
from pages import settings


def render():

    apply_global_style()

    st.title("Cycling Training Dashboard")


    # -----------------------------------------------------
    # DATA SYNC
    # -----------------------------------------------------

    st.sidebar.header("Data Sync")

    red_button()
    if st.sidebar.button("Update Strava Data", type="primary",):
        username = st.session_state["username"]
        strava = get_user_strava(username)

        st.write("USERNAME:", username)
        st.write("STRAVA:", strava)
        with st.spinner("Fetching latest Strava activities..."):

            try:
                username = st.session_state["username"]
                strava = get_user_strava(username)

                activities = update_strava_data(username, strava["access_token"])

                st.cache_data.clear()
                
                st.session_state["last_activity_date"] = activities["date"].max().date()

                st.session_state["strava_update_status"] = "success"
                st.session_state["strava_update_output"] = "Strava data updated successfully."

            except Exception as exc:
                st.session_state["strava_update_status"] = "error"
                st.session_state["strava_update_output"] = str(exc)

        st.rerun()


    # -----------------------------------------------------
    # UPDATE STATUS
    # -----------------------------------------------------

    if "strava_update_status" in st.session_state:

        if st.session_state["strava_update_status"] == "success":

            st.sidebar.success("Strava data updated.")

            if "last_activity_date" in st.session_state:
                st.sidebar.info(
                    f"Latest activity: {st.session_state['last_activity_date']}"
                )

        else:
            st.sidebar.error("Strava update failed.")



    CTL_TC = strava_config.CTL_TIME_CONSTANT
    ATL_TC = strava_config.ATL_TIME_CONSTANT

    username = st.session_state["username"]
    settings = get_user_settings(username)

    daily = calculate_training_load(username, settings["ftp"], strava_config.CTL_TIME_CONSTANT, strava_config.ATL_TIME_CONSTANT)
    activity_file, power_file = get_user_cache_paths(username)

    if not os.path.exists(activity_file):
        st.info("No Strava data found. Click **Update Strava Data** to download your activities.")
        st.stop()

    df = pd.read_csv(activity_file)

    df["date"] = pd.to_datetime(df["date"],errors="coerce")

    df = df.dropna(subset=["date"])

    ftp = settings["ftp"]

    df = df[df["weighted_average_watts"].notna()]

    df["IF"] = df["weighted_average_watts"] / ftp

    df["TSS"] = (df["moving_time"]* df["weighted_average_watts"]* df["IF"]/ (ftp * 3600)* 100)

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
        smoothed["CTL"] = filtered["CTL"].rolling(rolling_days, min_periods=1, center=False).mean()
        smoothed["ATL"] = filtered["ATL"].rolling(rolling_days, min_periods=1, center=False).mean()
        smoothed["TSB"] = filtered["TSB"].rolling(rolling_days, min_periods=1, center=False).mean()
        
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

    latest_activities = df.sort_values("date",ascending=False).head(12).copy()
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


    if os.path.exists(power_file):
        power_cache = build_power_curve_cache(
            power_file,
            os.path.getmtime(power_file),
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


