import time
from stravalib.client import Client
import config

# client = Client()
# url = client.authorization_url(
#     client_id=208407,
#     redirect_uri="http://localhost/exchange_token",
#     scope=["read", "activity:read_all"])
# print(url)

# client = Client()
# token_response = client.exchange_code_for_token(
#     client_id=CLIENT_ID,
#     client_secret=CLIENT_SECRET,
#     code=CODE)
# print(token_response)

def get_client():

    client = Client()

    # refresh if token expired
    if time.time() > config.EXPIRES_AT:

        refresh = client.refresh_access_token(
            client_id=config.CLIENT_ID,
            client_secret=config.CLIENT_SECRET,
            refresh_token=config.REFRESH_TOKEN
        )

        config.ACCESS_TOKEN = refresh["access_token"]
        config.REFRESH_TOKEN = refresh["refresh_token"]
        config.EXPIRES_AT = refresh["expires_at"]

    client.access_token = config.ACCESS_TOKEN

    return client
