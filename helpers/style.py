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
        :root {
            --ink: #17212b;
            --muted: #6b7785;
            --line: #dfe5ea;
            --surface: #ffffff;
            --canvas: #f5f7f8;
            --accent: #2f6f8f;
        }

        html, body, [class*="css"] { font-family: "DM Sans", "Segoe UI", sans-serif; }
        .stApp { background: var(--canvas); color: var(--ink); }
        .block-container { max-width: 1440px; padding: 2.25rem 3.5rem 4rem; }
        .dashboard-title { font-size: 2rem; line-height: 1.15; font-weight: 700; color: var(--ink); margin: 0 0 .45rem; letter-spacing: 0; }
        .page-kicker { color: var(--muted); font-size: .9rem; margin-bottom: 1.8rem; }
        h1, h2, h3 { color: var(--ink); letter-spacing: 0; }
        h2 { font-size: 1.2rem; margin-top: 2rem; }
        h3 { font-size: 1rem; }
        p, label, [data-testid="stCaptionContainer"] { color: var(--muted); }
        hr { border-color: var(--line); }
        div[data-testid="stMetric"] { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 1rem 1.1rem; box-shadow: 0 2px 8px rgba(23,33,43,.04); }
        div[data-testid="stMetricLabel"] { color: var(--muted); font-size: .74rem; text-transform: uppercase; letter-spacing: .06em; }
        div[data-testid="stMetricValue"] { color: var(--ink); font-size: 1.8rem; font-weight: 700; }
        .stButton > button, .stDownloadButton > button { border-radius: 6px; border: 1px solid var(--line); min-height: 2.5rem; font-weight: 600; }
        .stButton > button[kind="primary"] { background: var(--accent); border-color: var(--accent); color: white; }
        .stButton > button:hover { border-color: var(--accent); color: var(--accent); }
        [data-testid="stSidebar"] { background: #202a33; }
        [data-testid="stSidebar"] * { color: #d9e1e7; }
        [data-testid="stSidebar"] button { color: #d9e1e7 !important; }
        input, textarea, [data-baseweb="select"] > div { border-color: var(--line) !important; border-radius: 6px !important; }

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