import os
import numpy as np
import pandas as pd
from helpers.user_cache import get_user_cache_paths

TRAINING_ZONES = {
    "Recovery": {"min": 0.00, "max": 0.55},
    "Endurance": {"min": 0.55, "max": 0.76},
    "Tempo": {"min": 0.76, "max": 0.91},
    "Threshold": {"min": 0.91, "max": 1.06},
    "VO2max": {"min": 1.06, "max": 1.21},
    "Anaerobic": {"min": 1.21, "max": float("inf")},
}

ZONE_KEYS = tuple(TRAINING_ZONES.keys())

HR_ZONES = {
    "Recovery": {"min": 0.50, "max": 0.65},
    "Endurance": {"min": 0.65, "max": 0.75},
    "Tempo": {"min": 0.75, "max": 0.85},
    "Threshold": {"min": 0.85, "max": 0.92},
    "VO2max": {"min": 0.92, "max": 1.00},
    "Anaerobic": {"min": 1.00, "max": float("inf")}
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

def get_training_zone(intensity):
    for zone, limits in TRAINING_ZONES.items():
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
    activity_file, _ = get_user_cache_paths(username)
    if not os.path.exists(activity_file):
        return pd.DataFrame(columns=["stress", "CTL", "ATL", "TSB"])
    df = pd.read_csv(activity_file)
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