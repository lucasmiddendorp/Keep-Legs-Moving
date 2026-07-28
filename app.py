import streamlit as st

from pages.dashboard import render as render_dashboard
from pages.course_pacing import render as render_course_pacing
from pages.pacing_comparison import render as render_pacing_strategy
from pages.training_plan import render as render_training_plan
from pages.settings import render as render_settings

from helpers.navbar import render_navbar


st.set_page_config(
    page_title="Performance Dashboard",
    page_icon="🚴",
    layout="wide"
)


if "username" not in st.session_state:
    st.switch_page("pages/login.py")
    st.stop()


render_navbar()


page = st.session_state.get("page", "Dashboard")


if page == "Dashboard":
    render_dashboard()

elif page == "Course Pacing":
    render_course_pacing()

elif page == "Pacing Comparison":
    render_pacing_strategy()

elif page == "Training Plan":
    render_training_plan()

elif page == "Settings":
    render_settings()