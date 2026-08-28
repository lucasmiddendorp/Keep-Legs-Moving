import streamlit as st
import traceback

from Strava.strava_data import update_strava_data
from Strava.strava_user import get_valid_access_token
from helpers.database import load_training_plan, save_training_plan
from training_planner.periodization import reforecast_plan


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

        activities, new_activities = update_strava_data(username,access_token)

        saved_plan = load_training_plan(username)
        if saved_plan:
            save_training_plan(username, reforecast_plan(saved_plan, activities))

        status.write("⚡ Updating power data...")
        progress_bar.progress(80)

        # Clear cached data
        st.cache_data.clear()

        status.write("✅ Finished updating Strava data")
        progress_bar.progress(100)

        st.session_state["strava_update_status"] = "success"

        if "date" in activities.columns:
            st.session_state["last_activity_date"] = (activities["date"].max())

    except Exception as exc:
        st.session_state["strava_update_status"] = "error"
        st.session_state["strava_update_output"] = str(exc)
        st.error(str(exc))
        st.code(traceback.format_exc())

    st.rerun()