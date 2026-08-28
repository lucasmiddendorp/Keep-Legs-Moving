import streamlit as st

from helpers.availability_ui import render_weekly_availability


render_weekly_availability(st.session_state["username"])