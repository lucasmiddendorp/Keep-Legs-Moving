import streamlit as st


def render_navbar():

    st.markdown(
        """
        <style>
        .topbar {
            background-color: #e5e7eb;
            padding: 10px 20px;
            border-radius: 0px;
            width: 100%;
            display: flex;
            gap: 12px;
            margin-bottom: 25px;
        }

        div.stButton > button {
            background-color: white;
            color: #374151;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            padding: 8px 20px;
            font-weight: 600;
            width: 100%;
        }

        div.stButton > button:hover {
            background-color: #f3f4f6;
            border-color: #9ca3af;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


    pages = [
        ("Dashboard", "app.py"),
        ("Course Pacing", "pages/course_pacing.py"),
        ("Pacing Strategy", "pages/pacing_strategy.py"),
        ("Training Plan", "pages/training_plan.py"),
        ("Settings", "pages/settings.py"),
    ]


    cols = st.columns(len(pages))

    for col, (name, page) in zip(cols, pages):

        with col:

            if st.button(name, key=name):

                st.switch_page(page)