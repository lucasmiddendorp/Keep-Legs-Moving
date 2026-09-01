import streamlit as st
from helpers.style import apply_global_style
from helpers.dashboard_css import inject_card_css
from helpers.profile_page_functions import render_account_section, render_athlete_profile_section, inject_profile_css

apply_global_style()
inject_card_css()
inject_profile_css()

st.markdown('<div class="dashboard-title">Profile</div>', unsafe_allow_html=True)

username = st.session_state.get("username", "")

account_col, athlete_col = st.columns(2, gap="large")

with account_col:
    render_account_section(username)

with athlete_col:
    render_athlete_profile_section(username)