import secrets
import streamlit as st

from Strava.strava_auth import get_authorization_url
from Strava.strava_user import save_pending_user
username = st.session_state.get("username")

if not username:
    st.error("You must be logged in.")
    st.stop()

_, profile_col = st.columns([5, 1])
with profile_col:
    st.page_link("pages/profile.py", label="Profile")

st.title("Connect Strava")

st.write(
    "Connect your Strava account to import your "
    "activities and power data."
)

expected_state = secrets.token_urlsafe(32)

save_pending_user(
    username,
    expected_state
)

auth_url = get_authorization_url(
    state=expected_state
)

st.link_button(
    "Connect with Strava",
    auth_url,
    type="primary",
    use_container_width=True,
)