import streamlit as st

from stravalib.client import Client


def get_authorization_url(state=None):

    client = Client()

    return client.authorization_url(
        client_id=st.secrets["strava"]["CLIENT_ID"],
        redirect_uri=st.secrets["strava"]["REDIRECT_URI"],
        approval_prompt="force",
        scope=[
            "read",
            "activity:read_all",
        ],
        state=state,
    )


def exchange_code(code):

    client = Client()

    token_response, athlete = client.exchange_code_for_token(
        client_id=st.secrets["strava"]["CLIENT_ID"],
        client_secret=st.secrets["strava"]["CLIENT_SECRET"],
        code=code,
        return_athlete=True,
    )

    token_response["athlete"] = (
        athlete.model_dump() if hasattr(athlete, "model_dump") else athlete
    )

    return token_response