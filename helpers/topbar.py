<<<<<<< Updated upstream
=======

import base64
>>>>>>> Stashed changes
import streamlit as st
from helpers.strava_sync import update_strava
from Strava.strava_user import get_user_strava

<<<<<<< Updated upstream
def render_topbar():
    
    st.markdown(
        """
        <style>

        .topbar {

            display:flex;
            justify-content:space-between;
            align-items:center;

            padding:10px 0 18px;

            background:transparent;

            margin-bottom:25px;

        }


        .topbar-title {

            font-size:18px;
            font-weight:700;
            color:#17212b;

        }


        .topbar-subtitle {

            font-size:12px;
            color:#6b7785;

        }


=======
def get_logo_base64():
    with open("logo.png", "rb") as f:
        return base64.b64encode(f.read()).decode()

def render_topbar():
    st.markdown(
        """
        <style>
        .klm-topbar {
            width: 100%;
            margin-bottom: 20px;
            padding-bottom: 16px;
            border-bottom: 1px solid #e8ebee;
        }
        .klm-brand {
            display: flex;
            align-items: center;
            gap: 10px;
            height: 42px;
        }
        .klm-logo {
            width: 40px;
            height: 40px;
            border-radius: 11px;
            object-fit: cover;
        }
        .klm-brand-title {
            font-size: 16px;
            font-weight: 700;
            color: #17212b;
            line-height: 1.1;
        }
        .klm-brand-subtitle {
            margin-top: 4px;
            font-size: 11px;
            color: #7a8694;
        }
        .klm-nav-wrapper {
            display: flex;
            align-items: center;
            justify-content: center;
            background: #f1f3f5;
            padding: 4px;
            border-radius: 14px;
        }
        [data-testid="stPageLink"] {
            margin: 0 !important;
            padding: 0 !important;
        }
        [data-testid="stPageLink"] a {
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            min-height: 34px !important;
            padding: 0 15px !important;
            border-radius: 10px !important;
            border: 1px solid transparent !important;
            background: transparent !important;
            color: #66727e !important;
            text-decoration: none !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            box-shadow: none !important;
            transition: background 0.15s ease, border 0.15s ease, box-shadow 0.15s ease;
        }
        [data-testid="stPageLink"] a:hover {
            background: transparent !important;
            color: #17212b !important;
            box-shadow: none !important;
        }
        [data-testid="stPageLink"] a[aria-current="page"] {
            background: #ffffff !important;
            color: #17212b !important;
            font-weight: 1000 !important;
            border: 1px solid #e1e5e8 !important;
            box-shadow: 0 1px 3px rgba(23, 33, 43, 0.08) !important;
        }
        [data-testid="stPageLink"] img,
        [data-testid="stPageLink"] svg {
            display: none !important;
        }
        .klm-action button {
            min-height: 36px !important;
            padding: 0 14px !important;
            border-radius: 10px !important;
            border: 1px solid #e1e5e8 !important;
            background: #ffffff !important;
            color: #34414d !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            box-shadow: none !important;
        }
        .klm-action button:hover {
            background: #f6f7f8 !important;
            border-color: #d5dbe0 !important;
        }
        .klm-topbar [data-testid="column"] {
            padding: 0 !important;
        }
>>>>>>> Stashed changes
        </style>
        """,
        unsafe_allow_html=True
    )
<<<<<<< Updated upstream


    left, right = st.columns(
        [3,1],
        vertical_alignment="center"
    )


    # LEFT SIDE
    with left:

        st.markdown(
            """
            <div class="topbar-title">
                Keep Legs Moving
            </div>

            <div class="topbar-subtitle">
                Cycling Performance Analytics
            </div>
            """,
            unsafe_allow_html=True
        )


    # RIGHT SIDE
    with right:

        col1, col2 = st.columns(
            [1.5, 1],
            vertical_alignment="center"
        )

        with col1:

            username = st.session_state.get("username")

            strava = get_user_strava(username) if username else {}

            strava_connected = (
                isinstance(strava, dict)
                and strava.get("connected", False)
                and strava.get("access_token")
            )

            if st.button(
                "Sync Strava",
                use_container_width=True,
                disabled=not strava_connected,
            ):

                update_strava()

        with col2:

            if st.button(
                "Profile",
                use_container_width=True
            ):
=======
    brand_col, nav_col, actions_col = st.columns([1.7, 4.8, 1.5], vertical_alignment="center")
    with brand_col:
        logo = get_logo_base64()
        st.markdown(
            f"""
            <div class="klm-brand">
                <img class="klm-logo" src="data:image/png;base64,{logo}">
                <div>
                    <div class="klm-brand-title">Keep Legs Moving</div>
                    <div class="klm-brand-subtitle">Cycling Performance Analytics</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with nav_col:
        nav1, nav2, nav3, nav4 = st.columns([1, 0.8, 1.2, 0.9], gap="small")
        with nav1:
            st.page_link("pages/dashboard.py", label="Dashboard", icon=None)
        with nav2:
            st.page_link("pages/course_pacing.py", label="Pacing", icon=None)
        with nav3:
            st.page_link("pages/training_plan.py", label="Training Plan", icon=None)
        with nav4:
            st.page_link("pages/workout_library.py", label="Workouts", icon=None)
    with actions_col:
        sync_col, profile_col = st.columns([1, 1], gap="small")
        with sync_col:
            username = st.session_state.get("username")
            strava = get_user_strava(username) if username else {}
            strava_connected = isinstance(strava, dict) and strava.get("connected", False) and strava.get("access_token")
            if st.button("Sync", key="topbar_sync", disabled=not strava_connected, use_container_width=True):
                update_strava()
        with profile_col:
            if st.button("Profile", key="topbar_profile", use_container_width=True):
>>>>>>> Stashed changes
                st.switch_page("pages/profile.py")