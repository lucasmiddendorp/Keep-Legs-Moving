import streamlit as st


def apply_global_style():
    st.markdown(
        """
        <style>

        /* =========================================
           Global layout
        ========================================= */

        .block-container {
            max-width: 1440px;
            padding: 3rem 3rem 4rem;
        }

        .stApp {
            background: #ffffff;
        }


        /* =========================================
           Typography
        ========================================= */

        .dashboard-title {
            font-size: 2rem;
            line-height: 1.15;
            font-weight: 700;
            color: #18181b;
            margin: 0 0 0.45rem;
            letter-spacing: -0.02em;
        }

        .page-kicker {
            color: #71717a;
            font-size: 0.9rem;
            margin-bottom: 1.8rem;
        }

        h1,
        h2,
        h3 {
            color: #18181b;
            letter-spacing: -0.01em;
        }

        h2 {
            font-size: 1.2rem;
            margin-top: 2rem;
        }

        h3 {
            font-size: 1rem;
        }

        p,
        label,
        [data-testid="stCaptionContainer"] {
            color: #71717a;
        }


        /* =========================================
           Dividers
        ========================================= */

        hr {
            border-color: #e4e4e7;
        }


        /* =========================================
           Metrics
        ========================================= */

        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e4e4e7;
            border-radius: 10px;
            padding: 1rem 1.1rem;
            box-shadow: 0 2px 8px rgba(24, 24, 27, 0.04);
        }

        div[data-testid="stMetricLabel"] {
            color: #71717a;
            font-size: 0.74rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }

        div[data-testid="stMetricValue"] {
            color: #18181b;
            font-size: 1.8rem;
            font-weight: 700;
        }


        /* =========================================
        Buttons
        ========================================= */

        .stButton > button,
        .stDownloadButton > button {
            border-radius: 8px;
            min-height: 2.25rem;
            font-weight: 600;
        }

        .stButton > button[kind="primary"] {
            color: white;
        }
        div[data-testid="stButton"] {
            margin-top: 1.5rem !important;
        }

        div[data-testid="stButton"] button[kind="secondary"] {
            height: 2.25rem !important;
            padding: 0 12px !important;
            margin: 0 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
   

        /* =========================================
           Inputs
        ========================================= */

        input,
        textarea,
        [data-baseweb="select"] > div {
            border-radius: 8px !important;
        }


        /* =========================================
           Containers
        ========================================= */

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 10px;
        }



        /* =========================================
           Links
        ========================================= */

        a {
            color: #7c3aed;
        }

        a:hover {
            color: #6d28d9;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


def calendar_style():
    st.markdown(
        """
        <style>

        /* =========================================
           Calendar container
        ========================================= */

        .fc {
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid #e4e4e7;
            background: #ffffff;
            font-family: "DM Sans", sans-serif;
        }


        /* =========================================
           Past dates
        ========================================= */

        .fc-day-past {
            opacity: 0.4;
            background-color: #fafafa !important;
        }


        /* =========================================
           Today
        ========================================= */

        .fc-day-today {
            background-color: #f5f3ff !important;
            opacity: 1 !important;
            border: 2px solid #8b5cf6 !important;
        }


        /* =========================================
           Hover on selectable days
        ========================================= */

        .fc-daygrid-day:hover {
            background-color: #fafafa !important;
            cursor: pointer;
        }


        /* =========================================
           Event bars
        ========================================= */

        .fc-event {
            border-radius: 6px !important;
            padding: 2px 4px !important;
            font-size: 13px !important;
            font-weight: 600 !important;
        }


        /* =========================================
           Calendar title
        ========================================= */

        .fc-toolbar-title {
            font-size: 1.4rem !important;
            font-weight: 700 !important;
            color: #18181b !important;
        }


        /* =========================================
           Calendar buttons
        ========================================= */

        .fc-button {
            background-color: #ffffff !important;
            color: #3f3f46 !important;
            border: 1px solid #e4e4e7 !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 6px 12px !important;
            box-shadow: none !important;
        }

        .fc-button:hover {
            background-color: #fafafa !important;
            border-color: #d4d4d8 !important;
        }

        .fc-button-active {
            background-color: #8b5cf6 !important;
            color: #ffffff !important;
            border-color: #8b5cf6 !important;
        }


        /* =========================================
           Calendar day numbers
        ========================================= */

        .fc-daygrid-day-number {
            color: #3f3f46 !important;
            font-weight: 600 !important;
            padding: 8px !important;
        }


        /* =========================================
           Selected date
        ========================================= */

        .fc-highlight {
            background-color: #ede9fe !important;
            opacity: 0.7 !important;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


  
