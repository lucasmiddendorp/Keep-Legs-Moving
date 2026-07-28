import streamlit as st

st.set_page_config(
    page_title="Strava Callback"
)

from Strava.strava_auth import exchange_code
from Strava.strava_user import save_user_strava


st.title("Connecting Strava...")


if "code" not in st.query_params:
    st.error("No Strava code received.")
    st.stop()


code = st.query_params["code"]


# Recover user
from Strava.strava_user import (
    get_pending_user,
    clear_pending_user
)


username = get_pending_user()

if username is None:
    st.error(
        "No pending user found."
    )
    st.stop()


token = exchange_code(code)


save_user_strava(
    username,
    token
)

clear_pending_user()

st.success(
    "Strava connected successfully!"
)


st.switch_page(
    "app.py"
)