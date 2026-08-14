import streamlit as st

from Strava.strava_auth import exchange_code
from Strava.strava_user import (
    clear_pending_user,
    get_pending_state,
    get_pending_user,
    get_user_by_strava_athlete_id,
    save_user_strava,
)


def handle_strava_callback():

    error = st.query_params.get("error")

    if error:

        clear_pending_user()

        st.error(
            f"Strava authorization failed: {error}"
        )

        st.query_params.clear()

        return "error"


    code = st.query_params.get("code")

    if not code:
        return None


    returned_state = st.query_params.get("state")
    username = get_pending_user()

    if username is None:

        st.error(
            "No pending user found."
        )

        st.query_params.clear()

        return "error"


    expected_state = get_pending_state()

    if not expected_state or returned_state != expected_state:

        clear_pending_user()

        st.error(
            "Invalid or expired Strava authorization request."
        )

        st.query_params.clear()

        return "error"


    token = exchange_code(code)

    athlete = token.get("athlete") if isinstance(token, dict) else None
    athlete_id = athlete.get("id") if isinstance(athlete, dict) else None

    linked_user = get_user_by_strava_athlete_id(athlete_id)

    if linked_user and linked_user != username:

        clear_pending_user()

        st.error(
            "That Strava account is already connected to another dashboard user. "
            "Log out of Strava in this browser or use the correct Strava account."
        )

        return "error"

    save_user_strava(
        username,
        token,
    )

    clear_pending_user()

    st.query_params.clear()

    st.success(
        "Strava connected successfully!"
    )

    return "success"