from stravalib.client import Client
import pandas as pd
import os
from strava_auth import get_client
os.environ["SILENCE_TOKEN_WARNINGS"] = "true"

CACHE_FILE = "activities_cache.csv"
POWER_CACHE_FILE = "power_streams.parquet"

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


def fetch_new_activities(after_date=None):

    client = get_client()
    activities = []

    for activity in client.get_activities(after=after_date):
        activities.append(activity_to_dict(activity))

    return pd.DataFrame(activities)

def fetch_power_stream(activity_id):
    """
    Fetch time, moving, and watts streams for an activity.
    Returns a DataFrame with columns: activity_id, timepoint, time, moving, watts
    """
    client = get_client()
    try:
        streams = client.get_activity_streams(
            activity_id,
            types=['time', 'moving', 'watts'],
            resolution='high',
            series_type='time'
        )

        # Build dict of lists, pad as needed
        data = {}
        max_length = 0
        for stream_type in ['time', 'moving', 'watts']:
            stream_obj = streams.get(stream_type)
            values = getattr(stream_obj, 'data', []) if stream_obj else []
            data[stream_type] = values
            if len(values) > max_length:
                max_length = len(values)
        # Pad all lists to max_length
        for key in data:
            if len(data[key]) < max_length:
                data[key] += [None] * (max_length - len(data[key]))

        if max_length == 0:
            return None

        df = pd.DataFrame(data)
        df['activity_id'] = activity_id
        df['timepoint'] = df.index
        # Reorder columns
        df = df[['activity_id', 'timepoint', 'time', 'moving', 'watts']]
        return df

    except Exception as e:
        print(f"Stream error for {activity_id}: {e}")
    return None

def update_cache():

    if not os.path.exists(CACHE_FILE):

        print("Downloading all activities...")
        df = fetch_new_activities()

    else:

        print("Loading cached activities...")
        df = pd.read_csv(CACHE_FILE)
        df["date"] = pd.to_datetime(df["date"], format="mixed", errors="coerce")
        df = df.dropna(subset=["date"])

        latest_date = df["date"].max()

        print("Fetching new activities since", latest_date.date())

        new_df = fetch_new_activities(after_date=latest_date)

        if len(new_df) > 0:

            df = pd.concat([df, new_df], ignore_index=True)
            df = df.drop_duplicates(subset="id")

            print("Added", len(new_df), "new activities")

        else:
            print("No new activities found")

    df["distance_km"] = df["distance"] / 1000
    df["speed_kmh"] = df["average_speed"] * 3.6

    df.to_csv(CACHE_FILE, index=False)

    return df

def update_power_stream_cache(df):
    """
    For each Ride activity, fetch power streams (time, moving, watts),
    append to the power parquet cache.
    """
    rides = df

    if os.path.exists(POWER_CACHE_FILE):
        power_df = pd.read_parquet(POWER_CACHE_FILE)
        cached_ids = set(power_df["activity_id"].unique())
    else:
        power_df = pd.DataFrame()
        cached_ids = set()

    new_dfs = []

    for i, ride in rides.iterrows():
        activity_id = ride["id"]
        if activity_id in cached_ids:
            continue

        print(f"Downloading power stream for activity {activity_id}")
        # df_stream = fetch_power_stream(activity_id)
        df_stream = None  # Placeholder for actual stream fetching logic
        if df_stream is not None and not df_stream.empty:
            new_dfs.append(df_stream)

    if new_dfs:
        new_data = pd.concat(new_dfs, ignore_index=True)
        power_df = pd.concat([power_df, new_data], ignore_index=True)
        power_df.to_parquet(POWER_CACHE_FILE)
        print("Added", len(new_data), "power stream points")
    else:
        print("No new power streams")

    return power_df


if __name__ == "__main__":
    df = update_cache()
    power_df = update_power_stream_cache(df)
    print(df.tail())
    print("Total activities:", len(df))
    print("Total power datapoints:", len(power_df))
