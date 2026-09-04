import streamlit as st
import traceback

from Strava.strava_data import update_strava_data
from Strava.strava_user import get_valid_access_token
from helpers.debug import debug_error

def update_strava():

    username = st.session_state["username"]

    progress_bar = st.progress(0)
    status = st.empty()

    try:

        status.write("🔑 Checking Strava authentication...")
        progress_bar.progress(10)

        access_token = get_valid_access_token(username)

        status.write("🚴 Fetching Strava activities...")
        progress_bar.progress(30)

        activities, new_activities = update_strava_data(
            username,
            access_token
        )

        status.write("✅ Finished updating Strava data")
        progress_bar.progress(100)

        st.session_state["strava_update_status"] = "success"

        if "date" in activities.columns:
            st.session_state["last_activity_date"] = activities["date"].max()

        # DO NOT RERUN WHILE DEBUGGING

    except Exception as exc:

        st.session_state["strava_update_status"] = "error"

        debug_error(exc)

        st.error("❌ Strava sync failed")

        # IMPORTANT:
        # Don't rerun here while debugging.