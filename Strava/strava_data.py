import os
import pandas as pd

from stravalib.client import Client

from helpers.user_cache import get_user_cache_paths
from Strava.strava_client import update_power_stream_cache

# -----------------------------------------------------
# STRAVA CLIENT
# -----------------------------------------------------

def get_user_client(access_token):
 
    client = Client()
    client.access_token = access_token

    return client


# -----------------------------------------------------
# ACTIVITY PROCESSING
# -----------------------------------------------------

def activity_to_dict(activity):

    return {
        "id": activity.id,
        "date": activity.start_date.date(),

        "type": activity.type.name if hasattr(activity.type, "name") else str(activity.type),

        "distance": float(activity.distance) if activity.distance else None,

        "moving_time": int(activity.moving_time) if activity.moving_time else None,

        "total_elevation_gain": float(activity.total_elevation_gain) if activity.total_elevation_gain else None,

        "average_speed": float(activity.average_speed) if activity.average_speed else None,

        "average_heartrate": float(activity.average_heartrate)
        if getattr(activity, "average_heartrate", None)
        else None,

        "max_heartrate": float(activity.max_heartrate)
        if getattr(activity, "max_heartrate", None)
        else None,

        "average_watts": float(activity.average_watts)
        if getattr(activity, "average_watts", None)
        else None,

        "weighted_average_watts": float(activity.weighted_average_watts)
        if getattr(activity, "weighted_average_watts", None)
        else None,

        "trainer": activity.trainer,

        "gear_id": activity.gear_id,
    }


# -----------------------------------------------------
# FETCH ACTIVITIES
# -----------------------------------------------------

def fetch_activities(access_token, after_date=None):

    client = get_user_client(access_token)

    activities = []

    for activity in client.get_activities(after=after_date):
        activities.append(activity_to_dict(activity))

    return pd.DataFrame(activities)


# -----------------------------------------------------
# UPDATE ACTIVITY CACHE
# -----------------------------------------------------

def update_activity_cache(username, access_token):

    activity_file, _ = get_user_cache_paths(username)

    if not os.path.exists(activity_file):

        print("Downloading all activities...")

        df = fetch_activities(access_token)

    else:

        print("Loading existing activities...")

        df = pd.read_csv(activity_file)

        df["date"] = pd.to_datetime(df["date"], errors="coerce")

        latest_date = df["date"].max()

        print("Fetching activities after", latest_date)

        new_df = fetch_activities(
            access_token,
            after_date=latest_date
        )

        if not new_df.empty:

            df = pd.concat(
                [df, new_df],
                ignore_index=True
            )

            df = df.drop_duplicates(
                subset="id"
            )


    df["distance_km"] = df["distance"] / 1000

    df["speed_kmh"] = df["average_speed"] * 3.6


    df.to_csv(
        activity_file,
        index=False
    )

    return df


# -----------------------------------------------------
# POWER STREAMS
# -----------------------------------------------------

def fetch_power_stream(access_token, activity_id):

    client = get_user_client(access_token)

    streams = client.get_activity_streams(
        activity_id,
        types=["time", "moving", "watts"],
        resolution="high",
        series_type="time"
    )

    data = {}

    for stream_type in ["time", "moving", "watts"]:

        stream = streams.get(stream_type)

        data[stream_type] = stream.data if stream else []


    df = pd.DataFrame(data)

    df["activity_id"] = activity_id

    df["timepoint"] = df.index

    return df


# -----------------------------------------------------
# FULL UPDATE
# -----------------------------------------------------

def update_strava_data(username, access_token):

    print(
        "Updating Strava activities for",
        username
    )

    activities = update_activity_cache(
        username,
        access_token
    )
    
    update_power_stream_cache(username, access_token, activities)


    print(
        "Activities:",
        len(activities)
    )

    return activities