import streamlit as st

from helpers.auth import get_authenticator, save_config
from Strava.strava_user import get_user_strava, reset_user_strava

authenticator, config = get_authenticator()


# -----------------------------------------------------
# PAGE
# -----------------------------------------------------

st.title("🚴 Performance Dashboard")

authenticator.login()

auth_status = st.session_state.get("authentication_status")


# -----------------------------------------------------
# LOGIN FAILED
# -----------------------------------------------------

if auth_status is False:

    st.error("Incorrect username or password.")

    st.stop()


# -----------------------------------------------------
# NOT LOGGED IN
# -----------------------------------------------------

if auth_status is None:

    st.info("Please log in or create an account.")

    with st.expander("Create an account"):

        try:

            email, username, name = authenticator.register_user()

            if email:
                save_config(config)

                reset_user_strava(username)

                st.success(
                    "Account created successfully! "
                    "You can now log in."
                )
        

        except Exception as e:

            st.error(e)

    st.stop()


# -----------------------------------------------------
# SUCCESSFUL LOGIN
# -----------------------------------------------------

if auth_status:
    st.rerun()