import secrets
import streamlit as st

from Strava.strava_auth import (
    get_authorization_url,
)
from Strava.strava_user import (
    clear_pending_user,
    save_pending_user,
)


# --------------------------------------------------
# Require logged-in user
# --------------------------------------------------

username = st.session_state.get("username")

if not username:
    st.error("You must be logged in.")
    st.stop()


# --------------------------------------------------
# Connect screen
# --------------------------------------------------

st.title("Connect Strava")

st.write(
    "Connect your Strava account to import your "
    "activities and power data."
)


# --------------------------------------------------
# Persist the user initiating the OAuth flow
# --------------------------------------------------

if "strava_oauth_state" not in st.session_state:

    st.session_state["strava_oauth_state"] = (secrets.token_urlsafe(32))

expected_state = st.session_state["strava_oauth_state"]
clear_pending_user()
save_pending_user(username,state=expected_state)

auth_url = get_authorization_url(state=expected_state)
st.link_button(
    "Connect with Strava",
    auth_url,
    type="primary",
    use_container_width=True,
)