import streamlit as st

from helpers.navbar import render_navbar
from helpers.topbar import render_topbar
from Strava.strava_user import get_user_strava
from Strava.strava_oauth import handle_strava_callback

from helpers.database import init_database


st.set_page_config(
    page_title="Performance Dashboard",
    page_icon="🚴",
    layout="wide",
)

init_database()


# --------------------------------------------------
# Handle Strava OAuth callback
# --------------------------------------------------

callback_status = handle_strava_callback()

if callback_status == "success":
    st.rerun()

if callback_status == "error":
    st.stop()


# --------------------------------------------------
# Pages
# --------------------------------------------------

login = st.Page(
    "pages/login.py",
    title="Login",
    icon="🔑",
)

connect_strava = st.Page(
    "pages/connect_strava.py",
    title="Connect Strava",
    icon="🔗",
)

dashboard = st.Page(
    "pages/dashboard.py",
    title="Dashboard",
    icon="🏠",
)

course_pacing = st.Page(
    "pages/course_pacing.py",
    title="Course Pacing",
    icon="📊",
)

pacing_comparison = st.Page(
    "pages/pacing_comparison.py",
    title="Pacing Comparison",
    icon="🗺️",
)

training = st.Page(
    "pages/training_plan.py",
    title="Training Plan",
    icon="📅",
)

settings = st.Page(
    "pages/settings.py",
    title="Settings",
    icon="⚙️",
)

profile = st.Page(
    "pages/profile.py",
    title="Profile",
    icon="👤",
)

settings_availability = st.Page(
    "pages/settings_availability.py",
    title="Weekly Availability",
)

workout_builder = st.Page(
    "pages/workout_builder.py",
    title="Workout Builder",
    icon="🏋️",
)


# --------------------------------------------------
# Authentication
# --------------------------------------------------

authenticated = (
    st.session_state.get("authentication_status") is True
)


# --------------------------------------------------
# Not logged in
# --------------------------------------------------

if not authenticated:

    pg = st.navigation(
        [login]
    )


# --------------------------------------------------
# Logged in
# --------------------------------------------------

else:

    username = st.session_state.get("username")

    if not username:

        st.session_state["authentication_status"] = None

        pg = st.navigation(
            [login]
        )

    else:

        # ------------------------------------------
        # Check Strava connection
        # ------------------------------------------

        strava = get_user_strava(username)

        strava_connected = (
            isinstance(strava, dict)
            and strava.get("connected", False)
            and strava.get("access_token")
        )

        # ------------------------------------------
        # Strava not connected
        # ------------------------------------------

        if not strava_connected:

            pg = st.navigation(
                [connect_strava]
            )

        # ------------------------------------------
        # Strava connected
        # ------------------------------------------

        else:

            render_navbar()
            render_topbar()

            pg = st.navigation(
                [
                    dashboard,
                    course_pacing,
                    pacing_comparison,
                    training,
                    settings,
                    profile,
                    settings_availability,
                    workout_builder,
                ]
            )


# --------------------------------------------------
# Run selected page
# --------------------------------------------------

pg.run()