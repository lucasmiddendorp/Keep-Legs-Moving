import streamlit as st
import pandas as pd

from Strava.strava_user import get_user_settings, save_user_settings
from Strava.strava_user import get_training_goal, save_training_goal
from helpers.availability_ui import render_weekly_availability
from helpers.style import apply_global_style

# =========================================================
# Page setup
# =========================================================

apply_global_style()

st.title("Settings")

username = st.session_state["username"]

settings = get_user_settings(username)

# =========================================================
# Settings navigation
# =========================================================

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

# =========================================================
# Weekly availability
# =========================================================

if st.session_state.settings_section == "Weekly Availability":
    render_weekly_availability(username)
    st.stop()

# =========================================================
# Exceptions
# =========================================================

if st.session_state.settings_section == "Exceptions":
    st.switch_page("pages/settings_exceptions.py")

# =========================================================
# Athlete profile
# =========================================================

if st.session_state.settings_section == "Athlete Profile":

    st.subheader("Training progression")

    progression = st.select_slider(
        "Weekly progression",
        options=[4, 6, 8, 10, 12],
        value=settings.get("training_progression", 8),
        format_func=lambda x: f"{x}%"
    )

    st.caption(
        "How quickly your training load increases during build weeks. "
        "8% is recommended."
    )

    settings["training_progression"] = progression

    st.divider()

    # =====================================================
    # Threshold settings
    # =====================================================

    st.subheader("Threshold settings")

    ftp = st.number_input(
        "Cycling FTP (W)",
        min_value=50,
        max_value=700,
        value=int(settings.get("ftp", 150)),
        step=5,
    )

<<<<<<< Updated upstream
    st.write("**Running Threshold Pace (min/km)**")
=======
    st.write(
        "**Running Threshold Pace (min/km)** - Pace you can run at for "
        "1 hour (or approximately 95% of the pace you can run at for 20 min)"
    )
>>>>>>> Stashed changes

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



# =========================================================
# Training goal
# =========================================================

if st.session_state.settings_section == "Training Goal":

    st.subheader("Training Goal")

    st.caption(
        "Choose the sport and event you are training towards. "
        "Your training plan will use this goal to select and distribute "
        "appropriate workouts."
    )

    # =====================================================
    # Load existing training goal
    # =====================================================

    current_goal = get_training_goal(username)

    if not isinstance(current_goal, dict):
        current_goal = {
            "sport": "Cycling",
            "name": "general_fitness",
            "goal_date": None,
        }

    current_sport = current_goal.get("sport", "Cycling")

    if current_sport not in ["Cycling", "Running"]:
        current_sport = "Cycling"

    # =====================================================
    # Select training sport
    # =====================================================

    sport = st.segmented_control(
        "Sport",
        ["Cycling", "Running"],
        default=current_sport,
        selection_mode="single",
        key="training_goal_sport",
    )

    if not sport:
        sport = current_sport

    # =====================================================
    # Goal options for each sport
    # =====================================================

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

    if sport == "Running":
        goal_options = running_goal_options
    else:
        goal_options = cycling_goal_options

    # =====================================================
    # Make sure the previously saved goal exists
    # =====================================================

    current_goal_name = current_goal.get("name", "general_fitness")

    if current_goal_name not in goal_options:
        current_goal_name = "general_fitness"

    # =====================================================
    # Goal selection
    # =====================================================

    goal = st.selectbox(
        "Training goal",
        options=list(goal_options.keys()),
        index=list(goal_options.keys()).index(current_goal_name),
        format_func=lambda x: goal_options[x],
        key="training_goal_selection",
    )

    # =====================================================
    # Goal date
    # =====================================================

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
        key="training_goal_date",
    )

    # =====================================================
    # Running-specific information
    # =====================================================

    if sport == "Running":

        # Suggested distance based on the selected race
        default_distances = {
            "general_fitness": 0,
            "5k": 5,
            "10k": 10,
            "half_marathon": 21.1,
            "marathon": 42.2,
        }

        default_distance = default_distances.get(goal, 0)
        event_distance_km = default_distance
        event_climb_m = 0
        event_type = "race"

    # =====================================================
    # Cycling-specific information
    # =====================================================

    else:

        event_distance_km = st.number_input(
            "Event distance (km)",
            min_value=0.0,
            value=float(
                current_goal.get("event_distance_km") or 0
            ),
            step=5.0,
            key="cycling_event_distance",
        )

        event_climb_m = st.number_input(
            "Event climbing (m)",
            min_value=0.0,
            value=float(
                current_goal.get("event_climb_m") or 0
            ),
            step=100.0,
            key="cycling_event_climb",
        )

        event_type_options = [
            "endurance",
            "race",
            "time_trial",
        ]

        current_event_type = current_goal.get(
            "event_type",
            "endurance"
        )

        if current_event_type not in event_type_options:
            current_event_type = "endurance"

        event_type = st.selectbox(
            "Event type",
            event_type_options,
            index=event_type_options.index(current_event_type),
            key="cycling_event_type",
        )

    # =====================================================
    # Goal explanation
    # =====================================================

    if sport == "Running":

        goal_descriptions = {
            "general_fitness": (
                "Build general running fitness with a balanced mix of "
                "easy running, aerobic work, tempo and faster sessions."
            ),
            "5k": (
                "Prioritizes VO₂max, speed, running economy and shorter "
                "high-intensity intervals while maintaining aerobic fitness."
            ),
            "10k": (
                "Balances threshold development, VO₂max and aerobic "
                "endurance with progressively longer race-specific work."
            ),
            "half_marathon": (
                "Emphasizes aerobic endurance, threshold work and long "
                "runs with increasing amounts of race-specific intensity."
            ),
            "marathon": (
                "Prioritizes long-run development, aerobic endurance, "
                "fatigue resistance and controlled marathon-specific work."
            ),
        }

        st.info(goal_descriptions.get(goal, ""))

    else:

        goal_descriptions = {
            "general_fitness": (
                "Build general cycling fitness with a balanced mix of "
                "endurance, tempo and high-intensity workouts."
            ),
            "gran_fondo": (
                "Prioritizes endurance, long rides, climbing and the "
                "ability to sustain power for extended periods."
            ),
            "criterium": (
                "Places more emphasis on repeated high-intensity efforts, "
                "acceleration, VO₂max and anaerobic capacity."
            ),
        }

        st.info(goal_descriptions.get(goal, ""))

    # =====================================================
    # Save training goal
    # =====================================================

    if st.button(
        "Save Training Goal",
        use_container_width=True,
    ):

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