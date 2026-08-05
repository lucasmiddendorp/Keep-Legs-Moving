import streamlit as st

from helpers.navbar import render_navbar
from helpers.topbar import render_topbar


st.set_page_config(
    page_title="Performance Dashboard",
    page_icon="🚴",
    layout="wide"
)


# -----------------------------
# Define all pages
# -----------------------------

login = st.Page(
    "pages/login.py",
    title="Login",
    icon="🔑"
)

dashboard = st.Page(
    "pages/dashboard.py",
    title="Dashboard",
    icon="🏠"
)

course_pacing = st.Page(
    "pages/course_pacing.py",
    title="Course Pacing",
    icon="📊"
)

pacing_comparison = st.Page(
    "pages/pacing_comparison.py",
    title="Pacing Comparison",
    icon="🗺️"
)

training = st.Page(
    "pages/training_plan.py",
    title="Training Plan",
    icon="📅"
)

settings = st.Page(
    "pages/settings.py",
    title="Settings",
    icon="⚙️"
)

profile = st.Page(
    "pages/profile.py",
    title="Profile",
    icon="👤"
)

settings_availability = st.Page(
    "pages/settings_availability.py",
    title="Weekly Availability")


# -----------------------------
# Authentication routing
# -----------------------------

if not st.session_state.get("authentication_status"):

    pg = st.navigation(
        [login]
    )

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
            settings_availability
        ]
    )


pg.run()