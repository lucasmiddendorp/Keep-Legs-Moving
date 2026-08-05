import os
import pandas as pd
from stravalib.client import Client
from helpers.user_cache import get_user_cache_paths
from Strava.strava_user import get_user_settings
import numpy as np

ACTIVITY_COLUMNS = [
    "id",
    "date",
    "type",
    "distance",
    "moving_time",
    "total_elevation_gain",
    "average_speed",
    "average_heartrate",
    "max_heartrate",
    "average_watts",
    "weighted_average_watts",
    "trainer",
    "gear_id",
    'stress',
]

def get_user_client(access_token):
    client = Client()
    client.access_token = access_token
    return client

def activity_to_dict(activity):
    start_date = pd.to_datetime(activity.start_date, utc=True, errors="coerce") if activity.start_date else pd.NaT
    activity_type = activity.type.name if hasattr(activity.type, "name") else str(activity.type)

    return {
        "id": activity.id,
        "date": start_date.tz_localize(None) if pd.notna(start_date) else None,
        "type": activity_type,
        "distance": float(activity.distance) if activity.distance else None,
        "moving_time": int(activity.moving_time) if activity.moving_time else None,
        "total_elevation_gain": float(activity.total_elevation_gain) if activity.total_elevation_gain else None,
        "average_speed": float(activity.average_speed) if activity.average_speed else None,
        "average_heartrate": float(activity.average_heartrate) if getattr(activity, "average_heartrate", None) else None,
        "max_heartrate": float(activity.max_heartrate) if getattr(activity, "max_heartrate", None) else None,
        "average_watts": float(activity.average_watts) if getattr(activity, "average_watts", None) else None,
        "weighted_average_watts": float(activity.weighted_average_watts) if getattr(activity, "weighted_average_watts", None) else None,
        "trainer": activity.trainer,
        "gear_id": activity.gear_id
    }

def fetch_activities(access_token, after_date=None):
    client = get_user_client(access_token)
    activities = []
    for activity in client.get_activities(after=after_date):
        try:
            activity_dict = activity_to_dict(activity)
            if activity_dict["date"] is not None:
                activities.append(activity_dict)
            else:
                print("Skipping activity without date:", activity.id)
        except Exception as e:
            print("Skipping activity:", activity.id, e)
    df = pd.DataFrame(activities, columns=ACTIVITY_COLUMNS)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
    else:
        df = pd.DataFrame(columns=ACTIVITY_COLUMNS)
    return df

def update_activity_cache(username, access_token):
    activity_file, _ = get_user_cache_paths(username)
    if not os.path.exists(activity_file):
        print("Downloading all activities...")
        df = fetch_activities(access_token)
        new_df = df.copy()
    else:
        print("Loading existing activity cache...")
        try:
            df = pd.read_csv(activity_file)
        except pd.errors.EmptyDataError:
            df = pd.DataFrame(columns=ACTIVITY_COLUMNS)

        if "date" not in df.columns:
            df["date"] = pd.Series(dtype="datetime64[ns]")

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df[df["date"].notna()]

        if df.empty:
            after_timestamp = None
        else:
            latest_date = df["date"].max()
            after_timestamp = int(latest_date.timestamp())
            print("Fetching activities after:", latest_date)

        new_df = fetch_activities(access_token, after_date=after_timestamp)
        if "date" in new_df.columns:
            new_df["date"] = pd.to_datetime(new_df["date"], errors="coerce")
            new_df = new_df[new_df["date"].notna()]
        if not new_df.empty:
            df = pd.concat([df, new_df], ignore_index=True)
            df = df.drop_duplicates(subset="id")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["distance_km"] = df["distance"] / 1000
    df["speed_kmh"] = df["average_speed"] * 3.6

    settings = get_user_settings(username)
    df = calculate_activity_stress(df,ftp=settings.get("ftp", 200),threshold_hr=settings.get("threshold_hr", 170),threshold_pace=settings.get("threshold_pace", 5.0))

    df.to_csv(activity_file, index=False)

    return df, new_df

def fetch_power_stream(access_token, activity_id):
    client = get_user_client(access_token)
    try:
        streams = client.get_activity_streams(activity_id, types=["time", "moving", "watts"], resolution="high", series_type="time")
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
        print(f"Power stream error {activity_id}: {e}")
        return None

def update_power_stream_cache(username, access_token, activities):
    _, power_file = get_user_cache_paths(username)
    if os.path.exists(power_file):
        power_df = pd.read_parquet(power_file)
        cached_ids = set(power_df["activity_id"])
    else:
        power_df = pd.DataFrame()
        cached_ids = set()
    new_streams = []
    for _, activity in activities.iterrows():
        activity_id = int(activity["id"])
        if activity_id in cached_ids:
            continue
        stream = fetch_power_stream(access_token, activity_id)
        if stream is not None:
            new_streams.append(stream)
    if new_streams:
        power_df = pd.concat([power_df, *new_streams], ignore_index=True)
        power_df.to_parquet(power_file, index=False)
    return power_df

def update_strava_data(username, access_token):
    print("Updating Strava data for", username)
    activities, new_activities = update_activity_cache(username, access_token)
    if not new_activities.empty:
        print("Updating power streams for", len(new_activities), "new activities")
        update_power_stream_cache(username, access_token, new_activities)
    else:
        print("No new activities found")
    print("Total activities:", len(activities))
    return activities, new_activities


def calculate_activity_stress(df, ftp, threshold_hr, threshold_pace):
    """
    Calculate an estimated stress score for every activity.

    Priority:
    1. Cycling -> Power
    2. Heart rate
    3. Running pace
    4. Default IF = 0.35
    """

    df = df.copy()

    df["moving_time"] = pd.to_numeric(df["moving_time"], errors="coerce")
    df["average_speed"] = pd.to_numeric(df["average_speed"], errors="coerce")
    df["average_heartrate"] = pd.to_numeric(df["average_heartrate"], errors="coerce")
    df["weighted_average_watts"] = pd.to_numeric(df["weighted_average_watts"], errors="coerce")

    hours = df["moving_time"] / 3600

    df["stress"] = 0.0
    df["IF"] = 0.35

    # Pace (min/km)
    df["average_pace"] = np.where(
        df["average_speed"] > 0,
        1000 / (df["average_speed"] * 60),
        np.nan,
    )

    activity_type = df["type"].fillna("").astype(str)

    cycling_mask = (activity_type.str.contains("Ride|VirtualRide|GravelRide|MountainBikeRide|Handcycle|Velomobile",
        case=False,
        regex=True) & ~activity_type.str.contains("EBikeRide", case=False, na=False))


    running_mask = activity_type.str.contains(
        "Run|TrailRun|Treadmill",
        case=False,
        regex=True,
    )

    # -------------------------------------------------
    # 1. Cycling -> Power
    # -------------------------------------------------
    power_mask = cycling_mask & df["weighted_average_watts"].notna()

    df.loc[power_mask, "IF"] = (
        df.loc[power_mask, "weighted_average_watts"] / ftp
    )

    # -------------------------------------------------
    # 2. Heart rate (everything else)
    # -------------------------------------------------
    hr_mask = (~power_mask) & df["average_heartrate"].notna()

    df.loc[hr_mask, "IF"] = (
        df.loc[hr_mask, "average_heartrate"] / threshold_hr
    )

    # -------------------------------------------------
    # 3. Running pace
    # -------------------------------------------------
    pace_mask = (
        (~power_mask)
        & (~hr_mask)
        & running_mask
        & df["average_pace"].notna()
    )

    df.loc[pace_mask, "IF"] = (
        threshold_pace / df.loc[pace_mask, "average_pace"]
    )

    # -------------------------------------------------
    # Clamp IF to realistic values
    # -------------------------------------------------
    df["IF"] = df["IF"].clip(lower=0.20, upper=1.50)

    # -------------------------------------------------
    # Stress
    # -------------------------------------------------
    df["stress"] = (
        hours
        * (df["IF"] ** 2)
        * 100
    )

    return df