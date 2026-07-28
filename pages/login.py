import streamlit as st
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

from Strava.strava_user import get_user_strava


# -----------------------------------------------------
# CONFIG
# -----------------------------------------------------

CONFIG_PATH = "auth_config.yaml"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.load(f, Loader=SafeLoader)


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(
            config,
            f,
            default_flow_style=False
        )


# -----------------------------------------------------
# PAGE SETTINGS
# -----------------------------------------------------

st.set_page_config(
    page_title="Login",
    page_icon="🚴",
    layout="centered"
)


# -----------------------------------------------------
# LOAD AUTH CONFIG
# -----------------------------------------------------

config = load_config()


authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)


# -----------------------------------------------------
# LOGIN
# -----------------------------------------------------

st.title("🚴 Performance Dashboard")

authenticator.login()

if st.session_state.get("authentication_status"):
    authenticator.logout(
        "Logout",
        "sidebar"
    )

auth_status = st.session_state.get("authentication_status")


# -----------------------------------------------------
# LOGIN FAILED
# -----------------------------------------------------

if auth_status is False:

    st.error(
        "Incorrect username or password."
    )

    st.stop()



# -----------------------------------------------------
# NOT LOGGED IN
# -----------------------------------------------------

if auth_status is None:

    st.info(
        "Please log in or create an account."
    )


    with st.expander(
        "Create an account"
    ):

        try:

            email, username, name = (
                authenticator.register_user()
            )


            if email:

                save_config(config)

                st.success(
                    "Account created successfully! "
                    "You can now log in."
                )


        except Exception as e:

            st.error(e)


    st.stop()



# -----------------------------------------------------
# SUCCESSFUL LOGIN
# -----------------------------------------------------
if auth_status:

    username = st.session_state["username"]

    strava = get_user_strava(username)

    if not strava.get("connected", False):

        st.switch_page(
            "pages/connect_strava.py"
        )
        st.stop()

    else:

        st.switch_page(
            "app.py"
        )
        st.stop()
        