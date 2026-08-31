import streamlit as st
import pandas as pd
import numpy as np
import Strava.strava_config as strava_config
import os
import plotly.graph_objects as go
from datetime import date

from helpers.style import red_button, apply_global_style
from helpers.metrics import calculate_training_load, rolling_km, format_duration
from Strava.strava_data import update_strava_data
from Strava.strava_user import get_user_strava, get_user_settings
from Strava.strava_user import get_valid_access_token
from helpers.user_cache import get_user_cache_paths
from helpers.dashboard_cards import (
    render_metric_circle,
    render_readiness_card,
    render_fatigue_card,
    render_ramp_card
)

from helpers.dashboard_css import inject_card_css


apply_global_style()
inject_card_css()

st.markdown("""<div class="dashboard-title">Dashboard</div>""",unsafe_allow_html=True)

username = st.session_state["username"]
settings = get_user_settings(username)

activity_file, power_file = get_user_cache_paths(username)

if not os.path.exists(activity_file):
    st.info("No Strava data found. Click **Sync Strava** to download your activities.")
    st.stop()

df = pd.read_csv(activity_file)

df["date"] = pd.to_datetime(df["date"],errors="coerce")

df = df.dropna(subset=["date"])

df["type"] = (df["type"].astype(str).str.replace("root='", "", regex=False).str.replace("'", "", regex=False))
activity_types = ["All"] + sorted(df["type"].dropna().unique().tolist())
activity_type = st.segmented_control("Activity type",activity_types,default="All",key="activity_type_filter")

if activity_type != "All":
    df = df[df["type"] == activity_type]

daily = calculate_training_load(username,strava_config.CTL_TIME_CONSTANT, settings.get("atl_tc", 7), activity_type=activity_type)

if daily is None or daily.empty:
    st.info("No training-load data yet. Sync Strava activities first.")
    st.stop()

with st.expander("Filters"):

    col1, col2, col3 = st.columns(3)

    with col1:
        start_date = st.date_input("Start date",date.today() - pd.Timedelta(days=90))

    with col2:
        end_date = st.date_input("End date",date.today())

    with col3:
        rolling_days = st.slider("Rolling Average",1,28,5)
filtered = daily.loc[pd.to_datetime(start_date):pd.to_datetime(end_date)]

smoothed = filtered.copy()
if rolling_days > 1:
    smoothed["CTL"] = filtered["CTL"].rolling(rolling_days, min_periods=1, center=False).mean()
    smoothed["ATL"] = filtered["ATL"].rolling(rolling_days, min_periods=1, center=False).mean()
    smoothed["TSB"] = filtered["TSB"].rolling(rolling_days, min_periods=1, center=False).mean()
    
# DASHBOARD
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

col1,col2,col3 = st.columns(3)

with col1:
        render_ramp_card(ramp_label, ramp_position, fitness_ramp_rate)

with col2:
    render_fatigue_card(
                fatigue_label,
                atl,
                fatigue_delta
            )


with col3:
    render_readiness_card(
        readiness_label,
        readiness_note,
        readiness_color
    )   

st.subheader("Performance Management Chart")

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=filtered.index,
        y=filtered["stress"],
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
        position=0.02,
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

latest_activities = df[
    (pd.to_datetime(df["date"]) >= pd.to_datetime(start_date)) &
    (pd.to_datetime(df["date"]) <= pd.to_datetime(end_date) + pd.Timedelta(days=1))
].sort_values("date", ascending=False).copy()
latest_activities["Date"] = latest_activities["date"].dt.strftime("%Y-%m-%d")
latest_activities["Activity"] = latest_activities["type"].astype(str).str.replace("root='", "", regex=False).str.replace("'", "", regex=False)
latest_activities["Ride Length"] = latest_activities["distance_km"].map(lambda value: "" if pd.isna(value) else f"{value:.1f} km")
latest_activities["Time"] = latest_activities["moving_time"].map(format_duration)
latest_activities["Stress"] = latest_activities["stress"].map(lambda value: "" if pd.isna(value) else f"{value:.0f}")
latest_activities["Normalized Power"] = latest_activities["weighted_average_watts"].map(lambda value: "" if pd.isna(value) else f"{value:.0f} W")
latest_activities['Avg Heart Rate'] = latest_activities['average_heartrate'].map(lambda value: "" if pd.isna(value) else f"{value:.0f} bpm")
latest_activities['Time Z1 (min)'] = latest_activities['time_z1_hr'].map(lambda value: "" if pd.isna(value) else f"{value/60:.0f} min")
latest_activities['Time Z2 (min)'] = latest_activities['time_z2_hr'].map(lambda value: "" if pd.isna(value) else f"{value/60:.0f} min")
latest_activities['Time Z3 (min)'] = latest_activities['time_z3_hr'].map(lambda value: "" if pd.isna(value) else f"{value/60:.0f} min")
latest_activities['Time Z4+ (min)'] = latest_activities['time_z4_hr'].map(lambda value: "" if pd.isna(value) else f"{value/60:.0f} min")

st.dataframe(
    latest_activities[
        ["Date", "Activity", "Ride Length", "Time", "Stress", "Normalized Power", "Avg Heart Rate", "Time Z1 (min)", "Time Z2 (min)", "Time Z3 (min)", "Time Z4+ (min)"]
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
        (pd.to_datetime(df["date"]) >= pd.to_datetime(start_date)) & (pd.to_datetime(df["date"]) <= pd.to_datetime(end_date))
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

                        activity_display = pd.DataFrame([{
                            "Date": pd.to_datetime(activity["date"]).strftime("%d %b %Y"),
                            "Activity": activity.get("name", ""),
                            "Duration": f"{activity['moving_time'] / 60:.1f} min",
                            "Avg Power": (
                                f"{activity['weighted_average_watts']:.0f} W"
                                if pd.notna(activity.get("weighted_average_watts"))
                                else "—"
                            ),
                            "IF": (
                                f"{activity['IF']:.2f}"
                                if pd.notna(activity.get("IF"))
                                else "—"
                            ),
                            "Stress": (
                                f"{activity['stress']:.0f}"
                                if pd.notna(activity.get("stress"))
                                else "—"
                            ),
                        }])

                        st.dataframe(
                            activity_display,
                            hide_index=True,
                            use_container_width=True,
                        )
                    else:
                        st.info("Activity not found in dataframe.")
                else:
                    st.info("No activity found for that duration.")
else:
    st.info("No power stream data file found.")


