import streamlit as st


def red_button():

    st.markdown(
        """
        <style>
        div.stButton > button:first-child {
            background-color: #d9534f;
            color: white;
            font-weight: bold;
            border-radius: 8px;
            border: none;
            height: 3em;
        }

        div.stButton > button:first-child:hover {
            background-color: #c9302c;
            color: white;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def apply_global_style():

    st.markdown(
        """
        <style>

        /* Remove default Streamlit padding */
        .block-container {
            padding-top: 2rem;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            padding-top: 1rem;
        }

        /* Metric cards */
        div[data-testid="metric-container"] {
            border-radius: 10px;
            padding: 10px;
        }

        </style>
        """,
        unsafe_allow_html=True
    )