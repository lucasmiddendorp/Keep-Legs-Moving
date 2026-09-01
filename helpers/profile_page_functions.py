import streamlit as st
import pandas as pd

from helpers.auth import logout_user
from helpers.availability_ui import render_weekly_availability
from Strava.strava_user import (
    get_user_strava,
    reset_user_strava,
    get_user_settings,
    save_user_settings,
    get_training_goal,
    save_training_goal,
)

ATHLETE_PROFILE_SUBSECTIONS = ["Thresholds", "Training Goal", "Weekly Availability"]


def inject_profile_css():
    st.markdown(
        """
        <style>
        .profile-card-title{font-size:16px;font-weight:700;color:#17212b;margin:0 0 14px;}
        .profile-section-title{font-size:11px;font-weight:750;color:#7a8792;text-transform:uppercase;letter-spacing:.05em;margin:0 0 8px;}
        [data-testid="stVerticalBlockBorderWrapper"] hr{margin:14px 0;}
        div[data-testid="stHorizontalBlock"]{align-items:flex-start !important;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_account_section(username):
    with st.container(border=True):
        st.markdown('<div class="profile-card-title">Account</div>', unsafe_allow_html=True)

        st.text_input("Username", value=username, disabled=True, key="profile_username_display")
        st.text_input("Email", value=st.session_state.get("email", ""), disabled=True, key="profile_email_display")

        st.divider()

        st.markdown('<div class="profile-section-title">Security</div>', unsafe_allow_html=True)

        st.text_input("Current password", type="password", key="profile_current_password")
        st.text_input("New password", type="password", key="profile_new_password")
        st.text_input("Confirm new password", type="password", key="profile_confirm_password")

        if st.button("Update password", type="primary", key="profile_update_password"):
            st.info("Password update functionality coming soon.")

        st.divider()

        st.markdown('<div class="profile-section-title">Strava connection</div>', unsafe_allow_html=True)

        strava = get_user_strava(username)
        strava_connected = isinstance(strava, dict) and strava.get("connected", False) and strava.get("access_token")

        if strava_connected:
            st.success("Connected to Strava")
            if st.button("Disconnect Strava", key="profile_disconnect_strava"):
                reset_user_strava(username)
                st.rerun()
        else:
            st.warning("Not connected to Strava")
            if st.button("Connect Strava", key="profile_connect_strava"):
                st.switch_page("pages/connect_strava.py")

        st.divider()

        if st.button("🚪 Log out", key="profile_logout", use_container_width=True):
            logout_user()
            st.rerun()


def render_thresholds_section(username, settings):
    st.markdown('<div class="profile-section-title">Training progression</div>', unsafe_allow_html=True)

    progression = st.select_slider(
        "Weekly progression",
        options=[4, 6, 8, 10, 12],
        value=settings.get("training_progression", 8),
        format_func=lambda x: f"{x}%",
        key="profile_training_progression",
        label_visibility="collapsed",
    )

    st.caption("How quickly your training load increases during build weeks. 8% is recommended.")

    st.divider()

    st.markdown('<div class="profile-section-title">Threshold settings</div>', unsafe_allow_html=True)

    ftp = st.number_input(
        "Cycling FTP (W)",
        min_value=50,
        max_value=700,
        value=int(settings.get("ftp", 150)),
        step=5,
        key="profile_ftp",
    )

    weight = st.number_input(
        "Weight (kg)",
        min_value=30.0,
        max_value=200.0,
        value=float(settings.get("weight", 70) or 70),
        step=0.5,
        key="profile_weight",
    )

    st.caption("Running threshold pace (min/km) - pace you can run at for 1 hour (or 95% of the pace you can run at for 20 min)")

    pace = float(settings.get("threshold_pace", 5.0))
    pace_minutes = int(pace)
    pace_seconds = int(round((pace - pace_minutes) * 60))

    if pace_seconds == 60:
        pace_minutes += 1
        pace_seconds = 0

    col1, col2 = st.columns(2)

    with col1:
        pace_min = st.number_input("Minutes", min_value=2, max_value=10, value=pace_minutes, step=1, key="profile_pace_min")

    with col2:
        pace_sec = st.number_input("Seconds", min_value=0, max_value=59, value=pace_seconds, step=1, key="profile_pace_sec")

    threshold_pace = pace_min + pace_sec / 60

    max_hr = st.number_input(
        "Maximum Heart Rate (bpm)",
        min_value=120,
        max_value=220,
        value=int(settings.get("max_hr", 180)),
        step=1,
        key="profile_max_hr",
    )
    if st.button("Save Threshold Settings", type="primary", key="profile_save_thresholds"):
        save_user_settings(
            username,
            ftp=ftp,
            max_hr=max_hr,
            threshold_pace=threshold_pace,
            weight=weight,
            training_progression=progression)

        st.session_state["profile_thresholds_saved"] = True
        st.rerun()

    if st.session_state.pop("profile_thresholds_saved", False):
        st.success("✅ Threshold settings saved!")


def render_training_goal_section(username):
    st.markdown('<div class="profile-section-title">Training Goal</div>', unsafe_allow_html=True)

    st.caption(
        "Choose the sport and event you are training towards. "
        "Your training plan will use this goal to select and distribute "
        "appropriate workouts."
    )

    current_goal = get_training_goal(username)

    if not isinstance(current_goal, dict):
        current_goal = {"sport": "Cycling", "name": "general_fitness", "goal_date": None}

    current_sport = current_goal.get("sport", "Cycling")

    if current_sport not in ["Cycling", "Running"]:
        current_sport = "Cycling"

    sport = st.segmented_control(
        "Sport",
        ["Cycling", "Running"],
        default=current_sport,
        selection_mode="single",
        key="profile_training_goal_sport",
    )

    if not sport:
        sport = current_sport

    cycling_goal_options = {
        "general_fitness": "General Fitness",
        "gran_fondo": "Gran Fondo",
        "criterium": "Criterium",
    }

    running_goal_options = {
        "general_fitness": "General Fitness",
        "5k": "5K",
        "10k": "10K",
        "half_marathon": "Half Marathon",
        "marathon": "Marathon",
    }

    goal_options = running_goal_options if sport == "Running" else cycling_goal_options

    current_goal_name = current_goal.get("name", "general_fitness")

    if current_goal_name not in goal_options:
        current_goal_name = "general_fitness"

    goal = st.selectbox(
        "Training goal",
        options=list(goal_options.keys()),
        index=list(goal_options.keys()).index(current_goal_name),
        format_func=lambda x: goal_options[x],
        key="profile_training_goal_selection",
    )

    current_goal_date = current_goal.get("goal_date")

    if current_goal_date:
        try:
            current_goal_date = pd.to_datetime(current_goal_date).date()
        except Exception:
            current_goal_date = None

    goal_date = st.date_input(
        "Goal date",
        value=current_goal_date,
        min_value=pd.Timestamp.today().date(),
        key="profile_training_goal_date",
    )

    if sport == "Running":
        default_distances = {"general_fitness": 0, "5k": 5, "10k": 10, "half_marathon": 21.1, "marathon": 42.2}
        event_distance_km = default_distances.get(goal, 0)
        event_climb_m = 0
        event_type = "race"
    else:
        event_distance_km = st.number_input(
            "Event distance (km)",
            min_value=0.0,
            value=float(current_goal.get("event_distance_km") or 0),
            step=5.0,
            key="profile_cycling_event_distance",
        )

        event_climb_m = st.number_input(
            "Event climbing (m)",
            min_value=0.0,
            value=float(current_goal.get("event_climb_m") or 0),
            step=100.0,
            key="profile_cycling_event_climb",
        )

        event_type_options = ["endurance", "race", "time_trial"]
        current_event_type = current_goal.get("event_type", "endurance")

        if current_event_type not in event_type_options:
            current_event_type = "endurance"

        event_type = st.selectbox(
            "Event type",
            event_type_options,
            index=event_type_options.index(current_event_type),
            key="profile_cycling_event_type",
        )

    if sport == "Running":
        goal_descriptions = {
            "general_fitness": "Build general running fitness with a balanced mix of easy running, aerobic work, tempo and faster sessions.",
            "5k": "Prioritizes VO₂max, speed, running economy and shorter high-intensity intervals while maintaining aerobic fitness.",
            "10k": "Balances threshold development, VO₂max and aerobic endurance with progressively longer race-specific work.",
            "half_marathon": "Emphasizes aerobic endurance, threshold work and long runs with increasing amounts of race-specific intensity.",
            "marathon": "Prioritizes long-run development, aerobic endurance, fatigue resistance and controlled marathon-specific work.",
        }
    else:
        goal_descriptions = {
            "general_fitness": "Build general cycling fitness with a balanced mix of endurance, tempo and high-intensity workouts.",
            "gran_fondo": "Prioritizes endurance, long rides, climbing and the ability to sustain power for extended periods.",
            "criterium": "Places more emphasis on repeated high-intensity efforts, acceleration, VO₂max and anaerobic capacity.",
        }

    st.info(goal_descriptions.get(goal, ""))

    if st.button("Save Training Goal", use_container_width=True, key="profile_save_training_goal"):
        save_training_goal(
            username,
            goal,
            goal_date,
            event_distance_km=event_distance_km or None,
            event_climb_m=event_climb_m or None,
            event_type=event_type,
            sport=sport,
        )

        st.success("Training goal saved.")
        st.rerun()


def render_athlete_profile_section(username):
    with st.container(border=True):
        st.markdown('<div class="profile-card-title">Athlete Profile</div>', unsafe_allow_html=True)

        requested_section = st.session_state.pop("profile_section", None)
        default_section = requested_section if requested_section in ATHLETE_PROFILE_SUBSECTIONS else "Thresholds"

        selected_sub = st.segmented_control(
            "Athlete profile section",
            ATHLETE_PROFILE_SUBSECTIONS,
            default=default_section,
            selection_mode="single",
            key="profile_athlete_subsection",
            label_visibility="collapsed",
        )

        selected_sub = selected_sub or default_section

        st.divider()

        if selected_sub == "Thresholds":
            render_thresholds_section(username, get_user_settings(username))
        elif selected_sub == "Training Goal":
            render_training_goal_section(username)
        else:
            render_weekly_availability(username)
            if st.button("Manage availability exceptions", key="profile_manage_exceptions"):
                st.switch_page("pages/settings_exceptions.py")
