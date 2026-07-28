from stravalib.client import Client
import pandas as pd
import os
from helpers.user_cache import get_user_cache_paths


def get_user_client(access_token):
    client = Client()
    client.access_token = access_token
    return client


def activity_to_dict(a):
    return {
        "id": a.id,
        "date": a.start_date.date(),
        "type": str(a.type.name) if hasattr(a.type, "name") else str(a.type),
        "distance": float(a.distance) if a.distance else None,
        "moving_time": int(a.moving_time) if a.moving_time else None,
        "total_elevation_gain": float(a.total_elevation_gain) if a.total_elevation_gain else None,
        "average_speed": float(a.average_speed) if a.average_speed else None,
        "average_heartrate": float(a.average_heartrate) if getattr(a, "average_heartrate", None) else None,
        "max_heartrate": float(a.max_heartrate) if getattr(a, "max_heartrate", None) else None,
        "average_watts": float(a.average_watts) if getattr(a, "average_watts", None) else None,
        "weighted_average_watts": float(a.weighted_average_watts) if getattr(a, "weighted_average_watts", None) else None,
        "trainer": a.trainer,
        "gear_id": a.gear_id
    }


def fetch_new_activities(access_token, after_date=None):
    client = get_user_client(access_token)
    activities = []

    for activity in client.get_activities(after=after_date):
        activities.append(activity_to_dict(activity))

    return pd.DataFrame(activities)


def fetch_power_stream(access_token, activity_id):
    client = get_user_client(access_token)

    try:
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

        if df.empty:
            return None

        df["activity_id"] = activity_id
        df["timepoint"] = df.index

        return df[["activity_id", "timepoint", "time", "moving", "watts"]]

    except Exception as e:
        print(f"Stream error {activity_id}: {e}")
        return None


def update_activity_cache(username, access_token):
    activity_file, _ = get_user_cache_paths(username)

    if os.path.exists(activity_file):
        df = pd.read_csv(activity_file)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

        latest_date = df["date"].max()

        new_df = fetch_new_activities(
            access_token,
            latest_date
        )

        if not new_df.empty:
            df = pd.concat([df, new_df], ignore_index=True)
            df = df.drop_duplicates("id")

    else:
        df = fetch_new_activities(access_token)

    df["distance_km"] = df["distance"] / 1000
    df["speed_kmh"] = df["average_speed"] * 3.6

    df.to_csv(
        activity_file,
        index=False
    )

    return df


def update_power_stream_cache(username, access_token, df):
    _, power_file = get_user_cache_paths(username)

    if os.path.exists(power_file):
        power_df = pd.read_parquet(power_file)
        cached_ids = set(power_df["activity_id"])
    else:
        power_df = pd.DataFrame()
        cached_ids = set()

    new_streams = []

    for _, ride in df.iterrows():
        activity_id = ride["id"]

        if activity_id in cached_ids:
            continue

        stream = fetch_power_stream(
            access_token,
            activity_id
        )

        if stream is not None:
            new_streams.append(stream)

    if new_streams:
        power_df = pd.concat(
            [power_df, *new_streams],
            ignore_index=True
        )

        power_df.to_parquet(
            power_file
        )

    return power_df


def update_strava_data(username, access_token):
    df = update_activity_cache(
        username,
        access_token
    )

    update_power_stream_cache(
        username,
        access_token,
        df
    )

    return df