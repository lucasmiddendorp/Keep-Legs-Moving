import streamlit as st
import pandas as pd

# import pages.settings_availability as availability_page
# import pages.settings_exceptions as exceptions_page
from Strava.strava_user import get_user_settings, save_user_settings, load_config
from training_planner.goals import (TRAINING_GOALS, get_goal_description)

from Strava.strava_user import (get_training_goal,save_training_goal)


st.title("⚙️ Settings")


username = st.session_state["username"]


settings = get_user_settings(
    username
)


if "edit_settings" not in st.session_state:
    st.session_state.edit_settings = False




tabs = st.tabs([
    "Athlete Profile",
    "Weekly Availability",
    "Exceptions",
    "Training Goal"
])

with tabs[0]:

    st.subheader("Athlete settings")


    athlete_levels = {
        "Beginner": 10,
        "Amateur": 8,
        "Advanced": 6,
        "Professional": 5,
    }

    current_level = settings.get("athlete_level", "Amateur")

    athlete_level = st.select_slider(
        "Athlete Level",
        options=list(athlete_levels.keys()),
        value=current_level,
    )

    st.caption(
        f"Fatigue recovery time constant: {athlete_levels[athlete_level]} days"
    )

    if st.button("Save Athlete Level"):

        save_user_settings(
            username,
            athlete_level=athlete_level,
            atl_tc=athlete_levels[athlete_level])

        st.success("Athlete level saved")
        st.rerun()

    st.divider()

    st.subheader("Threshold settings")

    ftp = st.number_input(
        "Cycling FTP (W)",
        min_value=50,
        max_value=700,
        value=int(settings.get("ftp", 200)),
        step=5,
    )

    st.write("**Running Threshold Pace (min/km)**")

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


with tabs[1]:

    st.subheader(
        "Training Goal"
    )

    current_goal = get_training_goal(
        username
    )


    goal_names = list(
        TRAINING_GOALS.keys()
    )


    selected_goal = st.selectbox(

        "Goal",

        goal_names,

        index=(
            goal_names.index(
                current_goal["name"]
            )
            if current_goal["name"] in goal_names
            else 0
        )

    )


    st.info(
        get_goal_description(
            selected_goal
        )
    )


    goal_date = st.date_input(
        "Goal date"
    )


    if st.button(
        "Save Training Goal"
    ):

        save_training_goal(
            username,
            selected_goal,
            goal_date
        )


        st.success(
            "Training goal saved"
        )

        st.rerun()