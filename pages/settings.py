import streamlit as st

from Strava.strava_user import (
    get_user_settings,
    save_user_settings
)


def render():

    st.title("⚙️ Settings")


    username = st.session_state["username"]


    settings = get_user_settings(
        username
    )


    if "edit_settings" not in st.session_state:
        st.session_state.edit_settings = False



    # Display mode
    if not st.session_state.edit_settings:

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "FTP",
                f"{settings['ftp']} W"
            )

        with col2:
            st.metric(
                "Weight",
                f"{settings['weight']} kg"
            )


        if st.button("✏️ Edit settings"):

            st.session_state.edit_settings = True

            st.rerun()



    # Edit mode
    else:

        ftp = st.number_input(
            "FTP",
            value=settings["ftp"]
        )

        weight = st.number_input(
            "Weight (kg)",
            value=settings["weight"]
        )


        col1, col2 = st.columns(2)


        with col1:

            if st.button("💾 Save"):

                save_user_settings(
                    username,
                    ftp,
                    weight
                )

                st.session_state.edit_settings = False

                st.success(
                    "Settings saved"
                )

                st.rerun()



        with col2:

            if st.button("Cancel"):

                st.session_state.edit_settings = False

                st.rerun()