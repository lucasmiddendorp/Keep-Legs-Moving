import streamlit as st
import pandas as pd

# import pages.settings_availability as availability_page
# import pages.settings_exceptions as exceptions_page
from Strava.strava_user import get_user_settings, save_user_settings

from Strava.strava_user import (get_training_goal,save_training_goal)
from helpers.availability_ui import render_weekly_availability
from helpers.style import apply_global_style

apply_global_style()

st.title("Settings")


username = st.session_state["username"]


settings = get_user_settings(
    username
)


if "edit_settings" not in st.session_state:
    st.session_state.edit_settings = False

sections = [
    "Athlete Profile",
    "Weekly Availability",
    "Exceptions",
    "Training Goal",
]

if "settings_section" not in st.session_state:
    st.session_state.settings_section = "Athlete Profile"

selected_section = st.segmented_control(
    "Settings",
    sections,
    selection_mode="single",
    default=st.session_state.settings_section,
    key="settings_section_control",
)

if selected_section:
    st.session_state.settings_section = selected_section

if st.session_state.settings_section == "Weekly Availability":
    render_weekly_availability(username)
    st.stop()

if st.session_state.settings_section == "Exceptions":
    st.switch_page("pages/settings_exceptions.py")

if st.session_state.settings_section == "Athlete Profile":

    st.subheader("Training progression")
    progression = st.select_slider(
        "Weekly progression",
        options=[4, 6, 8, 10, 12],
        value=settings.get("training_progression", 8),
        format_func=lambda x: f"{x}%"
    )
    st.caption("How quickly your training load increases during build weeks. 8% is recommended.")
    settings["training_progression"] = progression

    st.divider()

    st.subheader("Threshold settings")

    ftp = st.number_input(
        "Cycling FTP (W)",
        min_value=50,
        max_value=700,
        value=int(settings.get("ftp", 150)),
        step=5,
    )

    st.write("**Running Threshold Pace (min/km)** - Pace you can run at for 1 hour (or 95% of the pace you can run at for 20 min)")

    pace = float(settings.get("threshold_pace", 5.0))

    pace_minutes = int(pace)
    pace_seconds = int(round((pace - pace_minutes) * 60))

    if pace_seconds == 60:
        pace_minutes += 1
        pace_seconds = 0

    col1, col2 = st.columns(2)

    with col1:
        pace_min = st.number_input(
            "Minutes",
            min_value=2,
            max_value=10,
            value=pace_minutes,
            step=1,
        )

    with col2:
        pace_sec = st.number_input(
            "Seconds",
            min_value=0,
            max_value=59,
            value=pace_seconds,
            step=1,
        )

    threshold_pace = pace_min + pace_sec / 60

    max_hr = st.number_input(
        "Maximum Heart Rate (bpm)",
        min_value=120,
        max_value=220,
        value=int(settings.get("max_hr", 180)),
        step=1,
    )

    if st.button("Save Threshold Settings", type="primary"):

        save_user_settings(
            username,
            ftp=ftp,
            max_hr=max_hr,
            threshold_pace=threshold_pace,
        )



        st.session_state["thresholds_saved"] = True
        st.rerun()

    if st.session_state.pop("thresholds_saved", False):
        st.success("✅ Threshold settings saved!")

    st.subheader("Mass settings")


    weight = st.number_input(
        "Body mass (kg)",
        min_value=30.0,
        max_value=150.0,
        value=float(settings.get("weight", 70)),
        step=0.5
    )


    if st.button(
        "Save mass settings",
        type="primary"
    ):

        save_user_settings(
            username,
            weight=weight
        )

        st.success(
            "Mass settings saved"
        )

        st.rerun()


if selected_section == "Training Goal":
    st.subheader("Training Goal")

    goal_options = {
        "general_fitness": "General Fitness",
        "gran_fondo": "Gran Fondo",
        "criterium": "Criterium",
    }

    current_goal = get_training_goal(username)

    if not isinstance(current_goal, dict):
        current_goal = {
            "name": "general_fitness",
            "goal_date": None,
        }

    current_goal_name = current_goal.get("name", "general_fitness")

    if current_goal_name not in goal_options:
        current_goal_name = "general_fitness"

    current_goal_date = current_goal.get("goal_date")

    if current_goal_date:
        try:
            current_goal_date = pd.to_datetime(current_goal_date).date()
        except Exception:
            current_goal_date = None

    goal = st.selectbox(
        "Training goal",
        options=list(goal_options.keys()),
        index=list(goal_options.keys()).index(current_goal_name),
        format_func=lambda x: goal_options[x],
    )

    goal_date = st.date_input(
        "Goal date",
        value=current_goal_date,
        min_value=pd.Timestamp.today().date(),
    )

    event_distance_km = st.number_input(
        "Event distance (km)",
        min_value=0.0,
        value=float(current_goal.get("event_distance_km") or 0),
        step=5.0,
    )
    event_climb_m = st.number_input(
        "Event climbing (m)",
        min_value=0.0,
        value=float(current_goal.get("event_climb_m") or 0),
        step=100.0,
    )
    event_type = st.selectbox(
        "Event type",
        ["endurance", "race", "time_trial"],
        index=["endurance", "race", "time_trial"].index(
            current_goal.get("event_type") or "endurance"
        ),
    )

    st.caption(
        "Your goal influences how your weekly training load is distributed. "
        "For example, Gran Fondo prioritizes endurance, while Criterium places "
        "more emphasis on high-intensity work."
    )

    if st.button("Save Training Goal", type="primary"):
        save_training_goal(
            username,
            goal,
            goal_date,
            event_distance_km=event_distance_km or None,
            event_climb_m=event_climb_m or None,
            event_type=event_type,
        )

        st.success("Training goal saved.")
        st.rerun()