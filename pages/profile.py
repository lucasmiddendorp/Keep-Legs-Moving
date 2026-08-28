import streamlit as st
from helpers.style import apply_global_style
from helpers.auth import logout_user

apply_global_style()

st.markdown(
    """
    <div class="dashboard-title">
        My Profile
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("Account")

username = st.session_state.get("username", "")

st.text_input(
    "Username",
    value=username,
    disabled=True,
)

st.text_input(
    "Email",
    value=st.session_state.get("email", ""),
    disabled=True,
)

st.divider()

st.subheader("Security")

current_password = st.text_input(
    "Current password",
    type="password",
)

new_password = st.text_input(
    "New password",
    type="password",
)

confirm_password = st.text_input(
    "Confirm new password",
    type="password",
)

if st.button("Update password", type="primary"):
    st.info("Password update functionality coming soon.")

st.divider()

st.subheader("Session")

if st.button("🚪 Log out", type="secondary", use_container_width=True):
    logout_user()
    st.rerun()