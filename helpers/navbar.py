import streamlit as st


def render_logo():

    st.markdown(
        """
        <style>

        .sidebar-logo {
            text-align:center;
            margin-bottom:35px;
        }

        .sidebar-logo img {
            border-radius:14px;
        }

        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="sidebar-logo">
            <img src="data:image/png;base64,{}" width="55">
        </div>
        """.format(
            get_logo_base64()
        ),
        unsafe_allow_html=True
    )


def get_logo_base64():

    import base64

    with open("logo.png", "rb") as f:
        return base64.b64encode(f.read()).decode()

def render_navbar():

    st.markdown(
        """
        <style>

        /* Thin sidebar */
        section[data-testid="stSidebar"] {
            width: 72px !important;
            min-width: 72px !important;
            max-width: 72px !important;
            background: #202a33 !important;
            border-right: 1px solid #34424d;
        }

        /* Remove Streamlit's default sidebar padding */
        section[data-testid="stSidebar"] > div {
            padding: 15px 8px !important;
        }

        /* Remove extra width from the sidebar content */
        section[data-testid="stSidebar"] .stVerticalBlock {
            gap: 8px !important;
        }

        /* Navigation buttons */
        section[data-testid="stSidebar"] button {
            width: 54px !important;
            min-width: 54px !important;
            max-width: 54px !important;
            height: 50px !important;

            padding: 0 !important;
            margin: 0 auto !important;

            border-radius: 12px !important;
            border: none !important;

            background: transparent !important;
            color: #d9e1e7 !important;

            font-size: 22px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;

            transition: all 0.15s ease;
        }

        /* Hover */
        section[data-testid="stSidebar"] button:hover {
            background: #34424d !important;
            transform: translateX(2px);
        }

        /* Hide button text styling */
        section[data-testid="stSidebar"] button p {
            font-size: 0 !important;
            margin: 0 !important;
        }

        section[data-testid="stSidebar"] button p::first-letter {
            font-size: 22px !important;
        }

        </style>
        """,
        unsafe_allow_html=True
    )

    with st.sidebar:

        pages = [
            ("🏠", "Dashboard"),
            ("📊", "Course Pacing"),
            ("🗺️", "Pacing Comparison"),
            ("📅", "Training Plan"),
            ("🏋️", "Workout Builder"),
            ("📚", "Workout Library"),
            ("⚙️", "Settings"),
        ]

        for icon, page in pages:
            if st.button(icon, key=f"nav_{page}"):
                st.switch_page(
                    f"pages/{page.lower().replace(' ', '_')}.py"
                )
