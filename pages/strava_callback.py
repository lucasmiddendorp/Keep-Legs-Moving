import streamlit as st

st.set_page_config(page_title="Strava Callback")

from Strava.strava_oauth import handle_strava_callback


st.title("Connecting Strava...")

callback_status = handle_strava_callback()

if callback_status == "success":

    st.rerun()

if callback_status is None:
    st.info("Waiting for the Strava authorization response.")