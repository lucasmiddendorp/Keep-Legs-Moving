import pandas as pd
import numpy as np

import Strava.strava_config as strava_config
from helpers.user_cache import get_user_cache_paths

import os
from datetime import date

from helpers.user_cache import get_user_cache_paths


def calculate_training_load(username, ftp, ctl_tc, atl_tc):

    activity_file, _ = get_user_cache_paths(username)

    if not os.path.exists(activity_file):
        return None

    df = pd.read_csv(activity_file)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    df = df[df["weighted_average_watts"].notna()]

    df["IF"] = df["weighted_average_watts"] / ftp
    df["TSS"] = (df["moving_time"] * df["weighted_average_watts"] * df["IF"]) / (ftp * 3600) * 100

    daily = df.groupby(pd.Grouper(key="date", freq="D"))["TSS"].sum().to_frame()
    daily = daily.asfreq("D", fill_value=0)

    today = pd.Timestamp(date.today())

    if daily.index[-1] < today:
        daily = daily.reindex(pd.date_range(daily.index[0], today, freq="D"), fill_value=0)

    daily["CTL"] = daily["TSS"].ewm(span=ctl_tc, adjust=False).mean()
    daily["ATL"] = daily["TSS"].ewm(span=atl_tc, adjust=False).mean()
    daily["TSB"] = daily["CTL"].shift(1) - daily["ATL"].shift(1)

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
    