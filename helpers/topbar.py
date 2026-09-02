import base64
import streamlit as st
from helpers.strava_sync import update_strava
from Strava.strava_user import get_user_strava

def get_logo_base64():
    with open("logo.png","rb") as f:
        return base64.b64encode(f.read()).decode()

def render_topbar():
    st.markdown("""
        <style>
        /* =====================================================
           TOP BAR
        ===================================================== */

        .klm-topbar-wrapper {
            width:100%;
            padding: 4px 0 18px 0;
            margin-bottom:20px;
            border-bottom:1px solid #e8ebee;
        }

        /* =====================================================
           BRAND
        ===================================================== */

        .klm-brand {
            display:flex;
            align-items:center;
            gap:10px;
            height:42px;
        }

        .klm-logo {
            width:40px;
            height:40px;
            border-radius:11px;
            object-fit:cover;
        }

        .klm-brand-text {
            display:flex;
            flex-direction:column;
            justify-content:center;
            line-height:1.1;
        }

        .klm-title {
            font-size:16px;
            font-weight:700;
            color:#17212b;
        }

        .klm-subtitle {
            margin-top:4px;
            font-size:11px;
            color:#7a8694;
        }

        /* =====================================================
           NAVIGATION
        ===================================================== */

        div[data-testid="column"] {
            gap:0;
        }

        div[data-testid="stHorizontalBlock"] > div:nth-child(2) {
            background:transparent !important;
            padding:0 !important;
            border-radius:0 !important;
            display:flex;
            justify-content:center;
            align-items:center;
        }

        [data-testid="stPageLink"] {
            width:auto !important;
        }

        [data-testid="stPageLink"] a {
            display:flex !important;
            align-items:center !important;
            justify-content:center !important;
            min-height:34px !important;
            padding:0 10px !important;
            margin:0 !important;
            border:none !important;
            border-radius:0 !important;
            background:transparent !important;
            color:#66727e !important;
            text-decoration:none !important;
            font-size:13px !important;
            font-weight:500 !important;
            box-shadow:none !important;
            transition:color 0.15s ease,font-weight 0.15s ease;
        }

        [data-testid="stPageLink"] a:hover {
            background:transparent !important;
            color:#17212b !important;
        }

        [data-testid="stPageLink"] img,
        [data-testid="stPageLink"] svg {
            display:none !important;
        }

        /* =====================================================
           SYNC BUTTON
        ===================================================== */

        .klm-sync-button button {
            min-height:36px !important;
            padding:0 14px !important;
            border-radius:10px !important;
            border:1px solid #c9e1ed !important;
            background:#eef8fc !important;
            color:#3d7187 !important;
            font-size:12px !important;
            font-weight:600 !important;
            box-shadow:none !important;
            transition:background 0.15s ease,border-color 0.15s ease;
        }

        .klm-sync-button button:hover {
            background:#e2f3f9 !important;
            border-color:#b8d8e5 !important;
            color:#315f72 !important;
        }

        .klm-sync-button button:disabled {
            background:#f4f7f8 !important;
            border-color:#e4e8ea !important;
            color:#a1abb3 !important;
        }

        /* =====================================================
           SPACING
        ===================================================== */

        div[data-testid="stHorizontalBlock"] {
            align-items:center;
            width:100%;
        }

        </style>
    """,unsafe_allow_html=True)

    brand_col,nav_col,actions_col=st.columns(
        [1.7,5.0,1.3],
        vertical_alignment="center"
    )

    # =========================================================
    # BRAND
    # =========================================================

    with brand_col:
        logo=get_logo_base64()
        st.image(f"data:image/png;base64,{logo}",width=150)

    
    # =========================================================
    # NAVIGATION
    # =========================================================

    with nav_col:
        nav1,nav2,nav3,nav4,nav5=st.columns(
            [1,1,1.3,1,1],
            gap="small"
        )

        with nav1:
            st.page_link(
                "pages/dashboard.py",
                label="Dashboard"
            )

        with nav2:
            st.page_link(
                "pages/course_pacing.py",
                label="Pacing"
            )

        with nav3:
            st.page_link(
                "pages/training_plan.py",
                label="Training Plan"
            )

        with nav4:
            st.page_link(
                "pages/workout_library.py",
                label="Workouts"
            )

        with nav5:
            st.page_link(
                "pages/profile.py",
                label="Profile"
            )

    # =========================================================
    # ACTIONS
    # =========================================================

    with actions_col:
        username=st.session_state.get("username")

        strava=(
            get_user_strava(username)
            if username
            else {}
        )

        strava_connected=(
            isinstance(strava,dict)
            and strava.get("connected",False)
            and strava.get("access_token")
        )

        st.markdown(
            '<div class="klm-sync-button">',
            unsafe_allow_html=True
        )

        if st.button(
            "Sync",
            key="topbar_sync",
            disabled=not strava_connected,
            use_container_width=True
        ):
            update_strava()

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        ) 