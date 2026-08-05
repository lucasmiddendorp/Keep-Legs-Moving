import yaml
from yaml.loader import SafeLoader
import time
from stravalib.client import Client
import Strava.strava_config as strava_config
import pandas as pd

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



def get_user_strava(username):

    config = load_config()

    user = config["credentials"]["usernames"][username]

    return user.get(
        "strava",
        {
            "connected": False
        }
    )


def save_user_strava(
        username,
        token
):

    config = load_config()

    print("Saving Strava for user:", username)

    print(
        "Available users:",
        config["credentials"]["usernames"].keys()
    )


    user = config["credentials"]["usernames"][username]


    user["strava"] = {

        "connected": True,

        "access_token":
            token["access_token"],

        "refresh_token":
            token["refresh_token"],

        "expires_at":
            token["expires_at"],
    }


    save_config(config)

    print("Saved successfully")


def save_pending_user(username):

    config = load_config()

    config["strava_oauth"]["pending_user"] = username

    save_config(config)



def get_pending_user():

    config = load_config()

    return config["strava_oauth"].get(
        "pending_user"
    )



def clear_pending_user():

    config = load_config()

    config["strava_oauth"]["pending_user"] = None

    save_config(config)

def get_user_settings(username):

    config = load_config()

    user = config["credentials"]["usernames"][username]

    return user.get(
        "settings",
        {
            "ftp": 300,
            "threshold_pace": 5.0,
            "threshold_hr": 170,
            "weight": 70,
        }
    )



def save_user_settings(
        username,
        ftp=None,
        threshold_hr=None,
        threshold_pace=None,
        weight=None,
        athlete_level=None,
        atl_tc=None,
):

    config = load_config()

    user = config["credentials"]["usernames"][username]


    if "settings" not in user:
        user["settings"] = {
            "ftp": 300,
            "threshold_hr": 170,
            "threshold_pace": 5.0,
            "weight": 70,
        }


    settings = user["settings"]

    if ftp is not None:
        settings["ftp"] = ftp
    if threshold_hr is not None:
        settings["threshold_hr"] = threshold_hr
    if threshold_pace is not None:
        settings["threshold_pace"] = threshold_pace
    if weight is not None:
        settings["weight"] = weight

    save_config(config)


def get_training_goal(username):

    settings = get_user_settings(username)

    return settings.get(
        "training_goal",
        {
            "name": None,
            "goal_date": None
        }
    )



def save_training_goal(
        username,
        goal_name,
        goal_date
):

    config = load_config()

    user = config["credentials"]["usernames"][username]


    if "settings" not in user:
        user["settings"] = {}


    user["settings"]["training_goal"] = {

        "name": goal_name,

        "goal_date": str(goal_date)

    }


    save_config(config)



def get_valid_access_token(username):

    config = load_config()

    user = config["credentials"]["usernames"][username]

    strava = user.get("strava")


    if not strava or not strava.get("connected", False):

        raise Exception("Strava account not connected")


    # Existing token still valid
    if pd.Timestamp.now() < pd.Timestamp(strava["expires_at"]) - pd.Timedelta(minutes=1):

        return strava["access_token"]


    # Token expired -> refresh
    client = Client()


    token = client.refresh_access_token(

        client_id=strava_config.CLIENT_ID,

        client_secret=strava_config.CLIENT_SECRET,

        refresh_token=strava["refresh_token"]

    )


    # Save new tokens back to auth_config.yaml

    user["strava"] = {

        "connected": True,

        "access_token": token["access_token"],

        "refresh_token": token["refresh_token"],

        "expires_at": token["expires_at"]

    }


    save_config(config)


    return token["access_token"]