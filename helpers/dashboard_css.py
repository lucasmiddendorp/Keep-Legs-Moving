import streamlit as st


def inject_card_css():

    st.markdown(
        """
        <style>

        /* --------------------
           General cards
        -------------------- */

        .modern-card {

            background:white;
            border-radius:18px;
            padding:20px;
            height:100%;

            border:1px solid #ede9fe;

            box-shadow:
            0px 4px 20px rgba(124,58,237,0.06);

        }


        .card-title {

            font-size:14px;
            font-weight:700;

            color:#64748b;

            text-transform:uppercase;

            letter-spacing:0.06em;

        }


        .card-main {

            margin-top:12px;

            font-size:28px;

            font-weight:800;

        }


        .card-note {

            margin-top:8px;

            color:#64748b;

            font-size:14px;

        }


        /* --------------------
           Ramp card
        -------------------- */

        .ramp-container {

            display:flex;

            gap:5px;

            margin-top:25px;

        }


        .ramp-segment {

            height:8px;

            flex:1;

            border-radius:20px;

        }


        .ramp-segment:nth-child(1){
            background:#ddd6fe;
        }

        .ramp-segment:nth-child(2){
            background:#c4b5fd;
        }

        .ramp-segment:nth-child(3){
            background:#a78bfa;
        }

        .ramp-segment:nth-child(4){
            background:#7c3aed;
        }


        .ramp-labels {

            display:flex;

            justify-content:space-between;

            margin-top:8px;

            color:#64748b;

            font-size:12px;

        }


        </style>
        """,
        unsafe_allow_html=True
    )