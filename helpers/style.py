import streamlit as st


def red_button():
    st.markdown(
        """
        <style>
        div[data-testid="stSidebar"] div.stButton > button {
            background-color: #d9534f;
            color: white;
            font-weight: bold;
            border-radius: 8px;
            border: none;
            height: 3em;
        }

        div[data-testid="stSidebar"] div.stButton > button:hover {
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

        .dashboard-title {
            font-size: 2.2rem;
            font-weight: 800;
            color: #1e1b4b;
            margin-bottom: 20px;
        }

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


def calendar_style():

    st.markdown(
        """
        <style>

        /* -----------------------------
           Calendar container
        ------------------------------*/

        .fc {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #e5e7eb;
            background: white;
        }


        /* -----------------------------
           Past dates
        ------------------------------*/

        .fc-day-past {
            opacity: 0.35;
            background-color: #f8fafc !important;
        }


        /* -----------------------------
           Today highlight
        ------------------------------*/

        .fc-day-today {
            background-color: #e0f2fe !important;
            opacity: 1 !important;
            border: 2px solid #2563eb !important;
        }


        /* -----------------------------
           Hover on selectable days
        ------------------------------*/

        .fc-daygrid-day:hover {
            background-color: rgba(250, 204, 21, 0.15) !important;
            cursor: pointer;
        }


        /* -----------------------------
           Event bars
        ------------------------------*/

        .fc-event {
            border-radius: 6px !important;
            padding: 2px 4px !important;
            font-size: 13px !important;
            font-weight: 600 !important;
        }


        /* -----------------------------
           Calendar title
        ------------------------------*/

        .fc-toolbar-title {
            font-size: 1.4rem !important;
            font-weight: 700 !important;
            color: #111827 !important;
        }


        /* -----------------------------
           Calendar buttons
        ------------------------------*/

        .fc-button {
            background-color: white !important;
            color: #374151 !important;
            border: 1px solid #d1d5db !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 6px 12px !important;
        }


        .fc-button:hover {
            background-color: #f3f4f6 !important;
        }


        .fc-button-active {
            background-color: #2563eb !important;
            color: white !important;
            border-color: #2563eb !important;
        }


        /* -----------------------------
           Calendar day numbers
        ------------------------------*/

        .fc-daygrid-day-number {
            color: #374151 !important;
            font-weight: 600 !important;
            padding: 8px !important;
        }


        /* Clicked date */
        .fc-highlight {
            background-color: #fde047 !important;
            opacity: 0.5 !important;
        }

        </style>
        """,
        unsafe_allow_html=True
    )