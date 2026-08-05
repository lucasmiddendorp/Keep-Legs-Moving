import pandas as pd
import numpy as np

import Strava.strava_config as strava_config
from helpers.user_cache import get_user_cache_paths

import os
from datetime import date

from helpers.user_cache import get_user_cache_paths


from datetime import date
import os
import pandas as pd
from helpers.user_cache import get_user_cache_paths

def calculate_training_load(username,ctl_tc,atl_tc, activity_type = "All"):

    activity_file, _ = get_user_cache_paths(username)

    if not os.path.exists(activity_file):
        return pd.DataFrame(columns=["stress", "CTL", "ATL", "TSB"])

    df = pd.read_csv(activity_file)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    df["type"] = (df["type"].astype(str).str.replace("root='", "", regex=False).str.replace("'", "", regex=False))

    if activity_type != "All":
        df = df[df["type"] == activity_type]

    if df.empty or "stress" not in df.columns:
        return pd.DataFrame(columns=["stress", "CTL", "ATL", "TSB"])
        
    daily = (df.groupby(pd.Grouper(key="date", freq="D"))["stress"].sum().to_frame())
    daily = daily.asfreq("D", fill_value=0)

    daily["CTL"] = (daily["stress"].ewm(span=ctl_tc, adjust=False).mean())
    daily["ATL"] = (daily["stress"].ewm(span=atl_tc, adjust=False).mean())

    daily["TSB"] = (daily["CTL"].shift(1)-daily["ATL"].shift(1))

    return daily


def format_duration(seconds):
    if pd.isna(seconds):
        return ""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"

def rolling_km(series_df, value_col, km_window):
    df = series_df.copy()

    x = df["distance_km"].to_numpy()
    y = df[value_col].to_numpy()

    out = np.empty(len(df))

    for i in range(len(df)):
        start = x[i] - km_window
        mask = (x >= start) & (x <= x[i])

        out[i] = np.mean(y[mask]) if mask.any() else np.nan

    return out

    

def calculate_workout_metrics(workout):

    steps = workout["steps"]

    total_duration = sum(
        step["duration"]
        for step in steps
    )


    if total_duration == 0:

        return {
            "duration": 0,
            "if": 0,
            "tss": 0
        }


    weighted_intensity = sum(

        step["duration"] *
        (step["ftp"] / 100) ** 4

        for step in steps

    )


    intensity_factor = (
        weighted_intensity /
        total_duration
    ) ** 0.25


    hours = total_duration / 60


    tss = (
        hours *
        intensity_factor ** 2 *
        100
    )


    return {

        "duration": round(total_duration),

        "if": round(
            intensity_factor,
            2
        ),

        "tss": round(tss),
        "steps": steps

    }