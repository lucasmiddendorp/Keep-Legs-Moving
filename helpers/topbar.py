import base64
import streamlit as st
from helpers.strava_sync import update_strava
from Strava.strava_user import get_user_strava


def get_logo_base64():
    with open("logo.png", "rb") as f:
        return base64.b64encode(f.read()).decode()


<<<<<<< Updated upstream
def render_topbar():

    st.markdown(
        """
        <style>

        /* =====================================================
           TOP BAR
        ===================================================== */

        .klm-topbar-wrapper {
            width: 100%;
            padding: 4px 0 18px 0;
            margin-bottom: 20px;
            border-bottom: 1px solid #e8ebee;
        }


        /* =====================================================
           BRAND
        ===================================================== */

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

        .klm-brand-text {
            display: flex;
            flex-direction: column;
            justify-content: center;
            line-height: 1.1;
        }

        .klm-title {
            font-size: 16px;
            font-weight: 700;
            color: #17212b;
        }

        .klm-subtitle {
            margin-top: 4px;
            font-size: 11px;
            color: #7a8694;
        }


        /* =====================================================
           NAVIGATION - Style the middle column directly
        ===================================================== */

        div[data-testid="column"] {
            gap: 0;
        }

        /* Target middle column (nav column) */
        div[data-testid="stHorizontalBlock"] > div:nth-child(2) {
            background: #f1f3f5;
            padding: 4px;
            border-radius: 14px;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        /* Style page links */
        [data-testid="stPageLink"] {
            width: auto !important;
        }

        [data-testid="stPageLink"] a {
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            min-height: 34px !important;
            padding: 0 15px !important;
            border: none !important;
            border-radius: 10px !important;
            background: transparent !important;
            color: #66727e !important;
            text-decoration: none !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            box-shadow: none !important;
            transition: background 0.15s ease, color 0.15s ease;
        }

        [data-testid="stPageLink"] a:hover {
            background: rgba(255, 255, 255, 0.75) !important;
            color: #17212b !important;
        }

        [data-testid="stPageLink"] img,
        [data-testid="stPageLink"] svg {
            display: none !important;
        }


        /* =====================================================
           BUTTONS - Style all buttons in topbar
        ===================================================== */

        div[data-testid="stHorizontalBlock"] > div:nth-child(3) button {
            min-height: 36px !important;
            padding: 0 14px !important;
            border-radius: 10px !important;
            border: 1px solid #e1e5e8 !important;
            background: white !important;
            color: #34414d !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            box-shadow: none !important;
            transition: background 0.15s ease, border-color 0.15s ease;
        }

        div[data-testid="stHorizontalBlock"] > div:nth-child(3) button:hover {
            background: #f6f7f8 !important;
            border-color: #d5dbe0 !important;
        }


        /* =====================================================
           SPACING
        ===================================================== */

        div[data-testid="stHorizontalBlock"] {
            align-items: center;
            width: 100%;
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
        unsafe_allow_html=True,
    )
<<<<<<< Updated upstream


    # =========================================================
    # TOP BAR
    # =========================================================

    brand_col, nav_col, actions_col = st.columns(
        [1.7, 4.8, 1.5],
        vertical_alignment="center",
    )


    # =========================================================
    # BRAND
    # =========================================================

    with brand_col:
        logo_col, text_col = st.columns([0.35, 0.65], gap="small", vertical_alignment="center")
        
        with logo_col:
            logo = get_logo_base64()
            st.image(f"data:image/png;base64,{logo}", width=40)
        
        with text_col:
            st.markdown("**Keep Legs Moving**", help=None)


    # =========================================================
    # NAVIGATION
    # =========================================================

    with nav_col:

        nav1, nav2, nav3, nav4 = st.columns(
            [1, 1, 1.25, 1],
            gap="small",
        )

        with nav1:
            st.page_link(
                "pages/dashboard.py",
                label="Dashboard",
            )

        with nav2:
            st.page_link(
                "pages/course_pacing.py",
                label="Pacing",
            )

        with nav3:
            st.page_link(
                "pages/training_plan.py",
                label="Training Plan",
            )

        with nav4:
            st.page_link(
                "pages/workout_library.py",
                label="Workouts",
            )


    # =========================================================
    # ACTIONS
    # =========================================================

    with actions_col:

        sync_col, profile_col = st.columns(
            [1, 1],
            gap="small",
        )


        # STRAVA SYNC
        with sync_col:

            username = st.session_state.get("username")

            strava = (
                get_user_strava(username)
                if username
                else {}
            )

            strava_connected = (
                isinstance(strava, dict)
                and strava.get("connected", False)
                and strava.get("access_token")
            )

            if st.button(
                "Sync",
                key="topbar_sync",
                disabled=not strava_connected,
                use_container_width=True,
            ):
                update_strava()


        # PROFILE
        with profile_col:

            if st.button(
                "Profile",
                key="topbar_profile",
                use_container_width=True,
            ):
                st.switch_page(
                    "pages/profile.py"
                )