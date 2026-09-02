import os
import numpy as np
import pandas as pd
from helpers.database import load_activity_cache

TRAINING_ZONES = {
    "Recovery": {"min": 0.00, "max": 0.55},
    "Endurance": {"min": 0.55, "max": 0.76},
    "Tempo": {"min": 0.76, "max": 0.91},
    "Threshold": {"min": 0.91, "max": 1.06},
    "VO2max": {"min": 1.06, "max": 1.21},
    "Anaerobic": {"min": 1.21, "max": float("inf")},
}

RUNNING_ZONES = {
    "Recovery": {"min": 0.00, "max": 0.70},
    "Endurance": {"min": 0.70, "max": 0.80},
    "Tempo": {"min": 0.80, "max": 0.95},
    "Threshold": {"min": 0.95, "max": 1.06},
    "VO2max": {"min": 1.06, "max": 1.21},
    "Anaerobic": {"min": 1.21, "max": float("inf")},
}


ZONE_KEYS = tuple(TRAINING_ZONES.keys())

HR_ZONES = {
    "Recovery": {"min": 0.50, "max": 0.60},
    "Endurance": {"min": 0.60, "max": 0.72},
    "Tempo": {"min": 0.72, "max": 0.80},
    "Threshold": {"min": 0.80, "max": 0.90},
    "VO2max": {"min": 0.90, "max": 0.97},
    "Anaerobic": {"min": 0.97, "max": float("inf")}
}

ZONE_TO_DISPLAY = {
    "Recovery": "Zone 1",
    "Endurance": "Zone 2",
    "Tempo": "Zone 3",
    "Threshold": "Zone 4",
    "VO2max": "Zone 5+",
    "Anaerobic": "Zone 5+",
}

CATEGORY_ZONE_FOCUS = {
    "Endurance": ("Endurance",),
    "Tempo": ("Tempo",),
    "Threshold": ("Threshold",),
    "VO2max": ("VO2max",),
    "Anaerobic": ("Anaerobic",),
}

def get_zone_definitions(sport="Cycling"):
    return RUNNING_ZONES if str(sport or "Cycling").strip().casefold() == "running" else TRAINING_ZONES


def get_training_zone(intensity, sport="Cycling"):
    for zone, limits in get_zone_definitions(sport).items():
        if limits["min"] <= intensity < limits["max"]:
            return zone
    return "Anaerobic"

def get_hr_zone(hr, max_hr):
    if max_hr <= 0:
        return "Recovery"
    hr_percent = hr / max_hr
    for zone, limits in HR_ZONES.items():
        if limits["min"] <= hr_percent < limits["max"]:
            return zone
    return "Threshold"

def calculate_training_load(username, ctl_tc, atl_tc, activity_type="All"):
    stored_activities = load_activity_cache(username)
    if not stored_activities:
        return pd.DataFrame(columns=["stress", "CTL", "ATL", "TSB"])
    df = pd.DataFrame(stored_activities)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["type"] = df["type"].astype(str).str.replace("root='", "", regex=False).str.replace("'", "", regex=False)
    if activity_type != "All":
        df = df[df["type"] == activity_type]
    if df.empty or "stress" not in df.columns:
        return pd.DataFrame(columns=["stress", "CTL", "ATL", "TSB"])
    daily = df.groupby(pd.Grouper(key="date", freq="D"))["stress"].sum().to_frame().asfreq("D", fill_value=0)
    daily["CTL"] = daily["stress"].ewm(span=ctl_tc, adjust=False).mean()
    daily["ATL"] = daily["stress"].ewm(span=atl_tc, adjust=False).mean()
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

def calculate_workout_metrics(workout):
    steps = workout["steps"]
    total_duration = sum(step["duration"] for step in steps)
    if total_duration == 0:
        return {"duration": 0, "if": 0, "tss": 0}
    weighted_intensity = sum(step["duration"] * (step["ftp"] / 100) ** 4 for step in steps)
    intensity_factor = (weighted_intensity / total_duration) ** 0.25
    hours = total_duration / 60
    tss = hours * intensity_factor ** 2 * 100
    return {"duration": round(total_duration), "if": round(intensity_factor, 2), "tss": round(tss), "steps": steps}