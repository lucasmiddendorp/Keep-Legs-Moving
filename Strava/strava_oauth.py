import streamlit as st

from Strava.strava_auth import exchange_code
from Strava.strava_user import (
    clear_pending_user,
    get_pending_user,
    get_user_by_strava_athlete_id,
    save_user_strava,
)
from helpers.database import get_user


def handle_strava_callback():

    error = st.query_params.get("error")

    if error:

        state = st.query_params.get("state")

        if state:
            clear_pending_user(state)

        st.error(
            f"Strava authorization failed: {error}"
        )

        st.query_params.clear()

        return "error"


    code = st.query_params.get("code")

    if not code:
        return None


    returned_state = st.query_params.get("state")

    if not returned_state:

        st.error(
            "Missing Strava OAuth state."
        )

        st.query_params.clear()

        return "error"


    # --------------------------------------------------
    # Find the user using the OAuth state
    # --------------------------------------------------

    username = get_pending_user(
        returned_state
    )

    if username is None:

        st.error(
            "No pending Strava authorization found. "
            "Please start the Strava connection again."
        )

        st.query_params.clear()

        return "error"


    # --------------------------------------------------
    # Exchange authorization code
    # --------------------------------------------------

    try:

        token = exchange_code(code)

    except Exception as e:

        clear_pending_user(returned_state)

        st.error(
            f"Failed to connect Strava: {e}"
        )

        st.query_params.clear()

        return "error"


    # --------------------------------------------------
    # Get Strava athlete
    # --------------------------------------------------

    athlete = (
        token.get("athlete")
        if isinstance(token, dict)
        else None
    )

    athlete_id = (
        athlete.get("id")
        if isinstance(athlete, dict)
        else None
    )


    if athlete_id is None:

        clear_pending_user(returned_state)

        st.error(
            "Strava did not return an athlete ID."
        )

        st.query_params.clear()

        return "error"


    # --------------------------------------------------
    # Check whether athlete is already linked
    # --------------------------------------------------

    linked_user = get_user_by_strava_athlete_id(
        athlete_id
    )

    if linked_user and linked_user != username:

        clear_pending_user(returned_state)

        st.error(
            "That Strava account is already connected "
            "to another dashboard user."
        )

        st.query_params.clear()

        return "error"


    # --------------------------------------------------
    # Save Strava connection
    # --------------------------------------------------

    save_user_strava(
        username,
        token
    )

    user = get_user(username)
    if user:
        st.session_state["authentication_status"] = True
        st.session_state["username"] = username
        st.session_state["user_id"] = user["id"]
        st.session_state["name"] = user.get("name") or username
        st.session_state["email"] = user.get("email")


    # --------------------------------------------------
    # OAuth complete
    # --------------------------------------------------

    clear_pending_user(
        returned_state
    )

    st.query_params.clear()

    st.success(
        "Strava connected successfully!"
    )

    return "success"