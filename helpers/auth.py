import streamlit_authenticator as stauth
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


def get_authenticator():

    config = load_config()

    authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
    )

    return authenticator, config