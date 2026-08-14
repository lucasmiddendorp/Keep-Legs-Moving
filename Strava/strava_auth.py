from stravalib.client import Client

import Strava.strava_config as strava_config


def get_authorization_url(state=None):

    client = Client()

    return client.authorization_url(
        client_id=strava_config.CLIENT_ID,
        redirect_uri=strava_config.REDIRECT_URI,
        approval_prompt="force",
        scope=[
            "read",
            "activity:read_all",
        ],
        state=state,
    )


def exchange_code(code):

    client = Client()

    token_response = client.exchange_code_for_token(
        client_id=strava_config.CLIENT_ID,
        client_secret=strava_config.CLIENT_SECRET,
        code=code,
    )

    return token_response