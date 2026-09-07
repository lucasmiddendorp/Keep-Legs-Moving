import streamlit as st
from datetime import datetime

from Strava.strava_data import update_strava_data
from Strava.strava_user import get_valid_access_token
from helpers.debug import debug_error


def show_sync_limit_message(result):
    limit_type = result.get("limit_type")
    synced_through = result.get("synced_through")
    reset_at = result.get("reset_at")
    if limit_type == "daily":
        st.warning("Strava's daily read API limit has been reached.")
        st.write("Your sync progress has been saved. Please try again tomorrow.")
    else:
        st.warning("Strava's 15-minute read API limit has been reached.")
        if reset_at:
            reset_text = reset_at.astimezone().strftime("%H:%M")
            st.write(f"Try again after **{reset_text}** and press Sync again.")
        else:
            st.write("Try again after the current 15-minute window and press Sync again.")
    if synced_through:
        if isinstance(synced_through, datetime):
            synced_text = synced_through.astimezone().strftime("%Y-%m-%d")
        else:
            synced_text = str(synced_through)[:10]
        st.write(f"Activities were synced through **{synced_text}**.")
    st.write("Activities and zone data processed so far have been saved.")


@st.dialog("Strava sync", width="small")
def show_sync_dialog(username):
    progress_bar = st.progress(0)
    status = st.empty()

    def update_progress(message, value):
        status.write(message)
        progress_bar.progress(min(max(value, 0.0), 1.0))

    try:
        status.write("Checking Strava authentication...")
        progress_bar.progress(0.05)
        access_token = get_valid_access_token(username)
        status.write("Fetching Strava activities...")
        progress_bar.progress(0.1)
        result = update_strava_data(
            username,
            access_token,
            progress_callback=update_progress,
        )
        activities = result.get("activities")
        if activities is not None and "date" in activities.columns:
            st.session_state["last_activity_date"] = activities["date"].max()
        if result.get("rate_limited"):
            st.session_state["strava_update_status"] = "rate_limited"
            show_sync_limit_message(result)
            return
        status.write("Sync complete.")
        progress_bar.progress(1.0)
        st.session_state["strava_update_status"] = "success"
    except Exception as exc:
        st.session_state["strava_update_status"] = "error"
        debug_error(exc)
        st.error("Strava sync failed")


def update_strava():

    username = st.session_state["username"]
    show_sync_dialog(username)