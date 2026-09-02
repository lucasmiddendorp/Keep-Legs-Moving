import streamlit as st


def inject_card_css():
    st.markdown(
        """
        <style>

        /* --------------------
           General cards
        -------------------- */

        .modern-card {
            background: #ffffff;
            border-radius: 10px;
            padding: 18px;
            height: 100%;
            border: 1px solid #e4e4e7;
            box-shadow: 0 2px 8px rgba(24, 24, 27, 0.04);
        }

        .card-title {
            font-size: 14px;
            font-weight: 700;
            color: #71717a;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }

        .card-main {
            margin-top: 12px;
            font-size: 26px;
            font-weight: 800;
            color: #18181b;
        }

        .card-note {
            margin-top: 8px;
            color: #71717a;
            font-size: 14px;
        }


        /* --------------------
           Ramp card
        -------------------- */

        .ramp-container {
            display: flex;
            gap: 5px;
            margin-top: 25px;
        }

        .ramp-segment {
            height: 8px;
            flex: 1;
            border-radius: 20px;
        }

        .ramp-segment:nth-child(1) {
            background: #ede9fe;
        }

        .ramp-segment:nth-child(2) {
            background: #ddd6fe;
        }

        .ramp-segment:nth-child(3) {
            background: #a78bfa;
        }

        .ramp-segment:nth-child(4) {
            background: #8b5cf6;
        }

        .ramp-labels {
            display: flex;
            justify-content: space-between;
            margin-top: 8px;
            color: #71717a;
            font-size: 12px;
        }


        /* --------------------
           Streamlit containers
        -------------------- */

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 10px;
        }


        /* --------------------
           Buttons
        -------------------- */

        .stButton > button {
            border-radius: 8px;
            font-weight: 600;
        }


        /* --------------------
           Inputs
        -------------------- */

        .stTextInput input,
        .stNumberInput input,
        .stDateInput input,
        .stSelectbox > div,
        .stMultiSelect > div {
            border-radius: 8px;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )
