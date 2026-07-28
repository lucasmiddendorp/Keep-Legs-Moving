import yaml
from yaml.loader import SafeLoader


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
            "weight": 70
        }
    )


def save_user_settings(username, ftp, weight):

    config = load_config()

    user = config["credentials"]["usernames"][username]

    user["settings"] = {
        "ftp": ftp,
        "weight": weight
    }

    save_config(config)