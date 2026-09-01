
import streamlit as st

from helpers.topbar import render_topbar
from Strava.strava_user import get_user_strava
from Strava.strava_oauth import handle_strava_callback
from helpers.database import init_database


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

settings = st.Page(
    "pages/settings.py",
    title="Settings",
)

settings_availability = st.Page(
    "pages/settings_availability.py",
    title="Weekly Availability",
)


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
                [connect_strava],
                position="hidden",
            )

        # -------------------------------------------------
        # Main application
        # -------------------------------------------------

        else:

            # Custom navigation
<<<<<<< Updated upstream
            render_navbar()
            render_topbar()
=======
            # Custom navigation
>>>>>>> Stashed changes

            pg = st.navigation(
                [
                    dashboard,
                    pacing,
                    training_plan,
                    workouts,
                    profile,
                    settings,
                    settings_availability,
                    workout_builder,
                    workout_library,
                ]
            )


# =========================================================
# RUN SELECTED PAGE
# =========================================================

pg.run()
