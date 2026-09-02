import streamlit as st
import bcrypt
from helpers.database import get_user, create_user

st.title("🚴 Keep Legs Moving")
st.subheader("Performance Analytics")

auth_status = st.session_state.get("authentication_status", None)

if auth_status is True:
    st.rerun()

tab1, tab2 = st.tabs(["Login", "Create account"])

with tab1:
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", type="primary", use_container_width=True)

    if submitted:
        if not username or not password:
            st.error("Enter your username and password.")
        else:
            user = get_user(username)

            if user and bcrypt.checkpw(
                password.encode("utf-8"),
                user["password_hash"].encode("utf-8")
            ):
                st.session_state["authentication_status"] = True
                st.session_state["username"] = username
                st.session_state["user_id"] = user["id"]
                if not st.session_state.get("athlete_profile_prompt_seen"):
                    st.session_state["show_athlete_profile_prompt"] = True
                st.rerun()
            else:
                st.error("Incorrect username or password.")

with tab2:
    with st.form("register_form"):
        email = st.text_input("Email")
        new_username = st.text_input("Username")
        name = st.text_input("Name")
        new_password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm password", type="password")
        registered = st.form_submit_button("Create account", type="primary", use_container_width=True)

    if registered:
        if not email or not new_username or not name or not new_password:
            st.error("Please fill in all fields.")
        elif new_password != confirm_password:
            st.error("Passwords do not match.")
        elif len(new_password) < 8:
            st.error("Password must be at least 8 characters.")
        elif get_user(new_username):
            st.error("Username already exists.")
        else:
            try:
                password_hash = bcrypt.hashpw(
                    new_password.encode("utf-8"),
                    bcrypt.gensalt()
                ).decode("utf-8")

                user_id = create_user(
                    username=new_username,
                    email=email,
                    name=name,
                    password_hash=password_hash
                )

                st.success("Account created successfully. You can now log in.")

            except Exception as e:
                if "unique" in str(e).lower():
                    st.error("Username or email already exists.")
                else:
                    st.error("Could not create account.")
                    st.exception(e)