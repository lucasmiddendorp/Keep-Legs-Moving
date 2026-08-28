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


        /* Make sidebar narrow */

        section[data-testid="stSidebar"] {

            width:90px !important;

            min-width:90px !important;

            background:#ffffff;
                        width:210px !important;
                        min-width:210px !important;
                        background:#202a33;
                        border-right:1px solid #34424d;


        section[data-testid="stSidebar"] > div {

            padding:20px 10px;

        }
                        width:180px;


                        background:transparent;
                        color:#d9e1e7;
                        font-size:13px;
                        text-align:left;
        section[data-testid="stSidebar"] button {

            height:45px;

            width:55px;

            border-radius:14px;

                        background:#34424d;
                        color:#ffffff;
            background:white;

            font-size:0;

            position:relative;

        }


        /* Icons */

        section[data-testid="stSidebar"] button::first-letter {

            font-size:22px;

        }



        /* Hover */

        section[data-testid="stSidebar"] button:hover {

            background:#eff6ff;

            transform:translateX(3px);

        }



        /* Tooltip */
                        if st.button(f"{icon}  {page}", key=f"nav_{page}"):
        section[data-testid="stSidebar"] button:hover::after {


            content:attr(data-testid);

            position:absolute;

            left:65px;

            top:50%;

            transform:translateY(-50%);


            background:#0f172a;

            color:white;


            padding:8px 12px;

            border-radius:8px;


            font-size:14px;

            white-space:nowrap;


            z-index:9999;

        }


        </style>

        """,
        unsafe_allow_html=True
    )


    with st.sidebar:


        # render_logo()


        pages = [

            ("🏠", "Dashboard"),

            ("📊", "Course Pacing"),

            ("🗺️", "Pacing Comparison"),

            ("📅", "Training Plan"),

            ("🏋️", "Workout Builder"),

            # ("🎯", "Goals"),

            ("⚙️", "Settings"),

        ]


        for icon, page in pages:
            if st.button(icon, key=f"nav_{page}"):
                st.switch_page(f"pages/{page.lower().replace(' ', '_')}.py")


