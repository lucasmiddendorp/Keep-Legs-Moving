
import streamlit as st

from helpers.topbar import render_topbar
from Strava.strava_user import get_training_goal, get_user_settings, get_user_strava
from Strava.strava_oauth import handle_strava_callback
from helpers.database import init_database
from helpers.availability import load_availability


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Keep Legs Moving",
    page_icon="🚴",
    layout="wide",
)


# =========================================================
# DATABASE
# =========================================================

init_database()


# =========================================================
# HANDLE STRAVA OAUTH CALLBACK
# =========================================================

callback_status = handle_strava_callback()

if callback_status == "success":
    st.rerun()

if callback_status == "error":
    st.stop()


# =========================================================
# PAGE DEFINITIONS
# =========================================================

login = st.Page(
    "pages/login.py",
    title="Login",
)

connect_strava = st.Page(
    "pages/connect_strava.py",
    title="Connect Strava",
)


# ---------------------------------------------------------
# Main application pages
# ---------------------------------------------------------

dashboard = st.Page(
    "pages/dashboard.py",
    title="Dashboard",
)

pacing = st.Page(
    "pages/course_pacing.py",
    title="Pacing",
)

training_plan = st.Page(
    "pages/training_plan.py",
    title="Training Plan",
)

workouts = st.Page(
    "pages/workout_library.py",
    title="Workouts",
)


# ---------------------------------------------------------
# Secondary / profile pages
# ---------------------------------------------------------

profile = st.Page(
    "pages/profile.py",
    title="Profile",
)

settings_exceptions = st.Page(
    "pages/settings_exceptions.py",
    title="Availability Exceptions",
)


def profile_has_changes(username):
    goal = get_training_goal(username)
    if goal.get("name"):
        return True

    settings = get_user_settings(username)
    defaults = {
        "ftp": 300,
        "max_hr": 190,
        "threshold_hr": None,
        "threshold_pace": 5.0,
        "weight": 70,
        "athlete_level": "Amateur",
        "training_progression": 8,
        "atl_tc": 7,
        "sessions_per_week": None,
    }
    for key, default in defaults.items():
        if settings.get(key) != default:
            return True

    weekly = load_availability(username).get("weekly", {})
    return any(
        data.get("available") or data.get("hours", 0) or data.get("start") or data.get("end")
        for data in weekly.values()
        if isinstance(data, dict)
    )


@st.dialog("Complete your athlete profile")
def show_athlete_profile_prompt():
    st.write(
        "Before you can access your performance dashboard, training plan "
        "and workout library, please fill in your athlete profile."
    )
    if st.button("Fill in athlete profile", type="primary", use_container_width=True):
        st.session_state["show_athlete_profile_prompt"] = False
        st.session_state["athlete_profile_prompt_seen"] = True
        goal = get_training_goal(st.session_state["username"])
        st.session_state["profile_section"] = "Training Goal" if not goal.get("name") else "Thresholds"
        st.session_state.pop("profile_athlete_subsection", None)
        st.switch_page("pages/profile.py")


# =========================================================
# AUTHENTICATION
# =========================================================

authenticated = (
    st.session_state.get("authentication_status") is True
)


# =========================================================
# NOT LOGGED IN
# =========================================================

if not authenticated:

    pg = st.navigation(
        [login],
        position="hidden",
    )


# =========================================================
# LOGGED IN
# =========================================================

else:

    username = st.session_state.get("username")

    # -----------------------------------------------------
    # Missing username
    # -----------------------------------------------------

    if not username:

        st.session_state["authentication_status"] = None

        pg = st.navigation(
            [login],
            position="hidden",
        )

    else:

        # -------------------------------------------------
        # Check Strava connection
        # -------------------------------------------------

        strava = get_user_strava(username)

        strava_connected = (
            isinstance(strava, dict)
            and strava.get("connected", False)
            and strava.get("access_token")
        )

        # -------------------------------------------------
        # Strava not connected
        # -------------------------------------------------

        if not strava_connected:

            pg = st.navigation(
                [connect_strava, profile],
                position="hidden",
            )

        # -------------------------------------------------
        # Main application
        # -------------------------------------------------

        else:


            # Custom navigation
           

            pg = st.navigation(
                [
                    dashboard,
                    pacing,
                    training_plan,
                    workouts,
                    profile,
                    settings_exceptions,
                ]
            )
            render_topbar()

        if st.session_state.get("show_athlete_profile_prompt"):
            if profile_has_changes(username):
                st.session_state["show_athlete_profile_prompt"] = False
                st.session_state["athlete_profile_prompt_seen"] = True
            else:
                st.session_state["show_athlete_profile_prompt"] = False
                st.session_state["athlete_profile_prompt_seen"] = True
                show_athlete_profile_prompt()


# =========================================================
# RUN SELECTED PAGE
# =========================================================

pg.run()
