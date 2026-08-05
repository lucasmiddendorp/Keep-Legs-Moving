import streamlit as st

from helpers.strava_sync import update_strava

def render_topbar():
    
    st.markdown(
        """
        <style>

        .topbar {

            display:flex;
            justify-content:space-between;
            align-items:center;

            padding:12px 20px;

            background:white;

            border-bottom:1px solid #e5e7eb;

            margin-bottom:25px;

        }


        .topbar-title {

            font-size:24px;
            font-weight:800;
            color:#0f172a;

        }


        .topbar-subtitle {

            font-size:13px;
            color:#64748b;

        }


        </style>
        """,
        unsafe_allow_html=True
    )


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
            [1.5,1],
            vertical_alignment="center"
        )


        with col1:

            if st.button(
                "🔄 Sync Strava",
                use_container_width=True
            ):
                update_strava()

        with col2:
            if st.button("👤 Profile"):
                st.switch_page("pages/profile.py")
