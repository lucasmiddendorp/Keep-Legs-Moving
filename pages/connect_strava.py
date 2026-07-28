import streamlit as st

st.set_page_config(
    page_title="Connect Strava",
    page_icon="🚴"
)

from Strava.strava_auth import get_authorization_url, exchange_code
from Strava.strava_user import save_user_strava, get_user_strava, save_pending_user



username = st.session_state.get("username")


# Check existing Strava connection
strava = get_user_strava(username)

if strava.get("connected", False):

    st.success("Strava already connected")

    st.switch_page("app.py")

    st.stop()



st.title("🚴 Connect Strava")

st.write(
    """
    Connect your Strava account to import your cycling activities.
    """
)


# OAuth button
username = st.session_state["username"]

save_pending_user(username)

auth_url = get_authorization_url()

st.link_button(
    "Connect with Strava",
    auth_url
)


# OAuth callback
if "code" in st.query_params:

    st.write("OAuth callback received")

    code = st.query_params["code"]

    st.write("Code:", code)


    with st.spinner("Connecting Strava..."):

        token = exchange_code(code)

        st.write("Token received:")
        st.write(token)


        username = st.query_params.get("pending_user")

        st.write("Username:", username)

        save_user_strava(
            username,
            token
        )


    st.success("Strava connected!")

    st.switch_page("app.py")
    st.stop()