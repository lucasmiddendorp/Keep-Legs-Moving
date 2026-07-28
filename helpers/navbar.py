import streamlit as st


import streamlit as st


def render_logo():

    st.markdown(
        """
        <style>

        .brand-header {
            display: flex;
            align-items: center;
            gap: 14px;
            margin-bottom: 12px;
        }

        .brand-title {
            font-size: 32px;
            font-weight: 800;
            color: #1f2937;
            letter-spacing: -1px;
        }

        .brand-subtitle {
            font-size: 14px;
            color: #6b7280;
            margin-top: -5px;
        }

        </style>
        """,
        unsafe_allow_html=True
    )

    col1, col2 = st.columns([0.08, 0.92])

    with col1:
        st.markdown("<div style='padding-top:10px'>", unsafe_allow_html=True)
        st.image("logo.png", width=55)
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown(
            """
            <div class="brand-title">
                Keep Legs Moving
            </div>
            <div class="brand-subtitle">
                Cycling Performance Analytics
            </div>
            """,
            unsafe_allow_html=True
        )

def render_navbar():

    render_logo()

    st.markdown(
        """
        <style>

        .nav-bar {
            background-color: #e5e7eb;
            padding: 8px 10px;
            border-radius: 12px;
            margin-bottom: 20px;
        }

        div[data-testid="stHorizontalBlock"] {
            gap: 0.25rem;
        }

        div[data-testid="stHorizontalBlock"] div.stButton > button {
            width: 100%;
            background-color: white;
            color: #374151;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            height: 2.8em;
        }

        div[data-testid="stHorizontalBlock"] div.stButton > button:hover {
            background-color: #f9fafb;
            color: #fc4c02;
            border-color: #fc4c02;
        }

        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="nav-bar">', unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns([1,1,1,1,1])

    with col1:
        if st.button("Dashboard"):
            st.session_state.page = "Dashboard"

    with col2:
        if st.button("Course Pacing"):
            st.session_state.page = "Course Pacing"

    with col3:
        if st.button("Pacing Comparison"):
            st.session_state.page = "Pacing Comparison"

    with col4:
        if st.button("Training Plan"):
            st.session_state.page = "Training Plan"

    with col5:
        if st.button("Settings ⚙️"):
            st.session_state.page = "Settings"

    st.markdown("</div>", unsafe_allow_html=True)