import streamlit as st

from pages.dashboard import render as render_dashboard
from pages.course_pacing import render as render_course_pacing
from pages.pacing_comparison import render as render_pacing_comparison
from helpers.navbar import render_navbar
from pages.training_plan import render as render_training_plan
from pages.settings import render as render_settings




st.set_page_config(
    page_title="Performance Dashboard",
    page_icon="🚴",
    layout="wide",
)

st.markdown(
    """
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
    """,
    unsafe_allow_html=True
)

if "username" not in st.session_state:
    st.switch_page("pages/login.py")
    st.stop()
    
# ------------------------------
# Logged in app
# ------------------------------
render_navbar()

st.title("🚴 Performance Dashboard")

username = st.session_state["username"]
name = st.session_state["name"]

st.sidebar.success(f"Logged in as {name}")



# -------------------------------
# TOP NAVIGATION
# -------------------------------

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"


st.markdown(
    """
    <style>

    div.stButton > button {
        border: none;
        background: transparent;
        font-size: 16px;
        padding: 10px 20px;
    }

    div.stButton > button:hover {
        color: #fc4c02;
        background-color: transparent;
    }

    </style>
    """,
    unsafe_allow_html=True
)


col1, col2, col3, col4, col5 = st.columns(
    [1, 1.2, 1.4, 1.2, 0.8]
)


with col1:
    if st.button("Dashboard"):
        st.session_state.page = "Dashboard"


with col2:
    if st.button("Course Pacing"):
        st.session_state.page = "Course Pacing"


with col3:
    if st.button("Pacing Strategy"):
        st.session_state.page = "Pacing Strategy"


with col4:
    if st.button("Training Plan"):
        st.session_state.page = "Training Plan"


with col5:
    if st.button("Settings ⚙️"):
        st.session_state.page = "Settings"



st.divider()


page = st.session_state.page


if page == "Dashboard":
    render_dashboard()

elif page == "Course Pacing":
    render_course_pacing()

elif page == "Pacing Strategy":
    render_pacing_comparison()

elif page == "Training Plan":
    render_training_plan()

elif page == "Settings":
    render_settings()