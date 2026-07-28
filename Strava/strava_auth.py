import time
from stravalib.client import Client
import Strava.strava_config as strava_config


def get_authorization_url():

    client = Client()

    url = client.authorization_url(
        client_id=strava_config.CLIENT_ID,
        redirect_uri=strava_config.REDIRECT_URI,
        scope=[
            "read",
            "activity:read_all"
        ]
    )

    return url



def exchange_code(code):

    client = Client()

    token_response = client.exchange_code_for_token(
        client_id=strava_config.CLIENT_ID,
        client_secret=strava_config.CLIENT_SECRET,
        code=code
    )

    return token_response



from Strava.strava_user import get_user_strava
from Strava.strava_user import save_user_strava
from stravalib.client import Client
import time
import Strava.strava_config as strava_config


def get_client(username):

    strava = get_user_strava(username)

    client = Client()


    if time.time() > strava["expires_at"]:

        refresh = client.refresh_access_token(
            client_id=strava_config.CLIENT_ID,
            client_secret=strava_config.CLIENT_SECRET,
            refresh_token=strava["refresh_token"]
        )

        token = {
            "access_token": refresh["access_token"],
            "refresh_token": refresh["refresh_token"],
            "expires_at": refresh["expires_at"],
        }

        save_user_strava(
            username,
            token
        )

        strava = token


    client.access_token = strava["access_token"]

    return client