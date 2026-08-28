import streamlit as st
import bcrypt
from helpers.database import get_user, create_user


def get_authenticator():
    """
    Kept for compatibility with existing code.
    Authentication is now handled through PostgreSQL.
    """
    return None, None


def authenticate_user(username, password):
    user = get_user(username)

    if not user:
        return False

    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            user["password_hash"].encode("utf-8"),
        )
    except Exception:
        return False


def register_user(email, username, name, password):
    if get_user(username):
        raise ValueError("Username already exists.")

    hashed_password = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

    return create_user(
        username=username,
        email=email,
        name=name,
        password_hash=hashed_password,
    )


def login_user(username):
    user = get_user(username)

    if not user:
        return False

    st.session_state["authentication_status"] = True
    st.session_state["username"] = username
    st.session_state["name"] = user.get("name") or username
    st.session_state["email"] = user.get("email")

    return True


def logout_user():
    st.session_state["authentication_status"] = None
    st.session_state.pop("username", None)
    st.session_state.pop("name", None)
    st.session_state.pop("email", None)