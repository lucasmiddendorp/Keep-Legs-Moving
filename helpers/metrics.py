import numpy as np
import pandas as pd
from datetime import date
from helpers.database import load_activity_cache

# training zones based on strava power zones
TRAINING_ZONES = {
    "Recovery": {"min": 0.00, "max": 0.55},
    "Endurance": {"min": 0.55, "max": 0.75},
    "Tempo": {"min": 0.75, "max": 0.90},
    "Threshold": {"min": 0.90, "max": 1.05},
    "VO2max": {"min": 1.05, "max": 1.20},
    "Anaerobic": {"min": 1.20, "max": float("inf")},
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

ZONE_TO_DISPLAY = { 
    "Recovery": "Zone 1",
    "Endurance": "Zone 2",
    "Tempo": "Zone 3",
    "Threshold": "Zone 4",
    "VO2max": "Zone 5+",
    "Anaerobic": "Zone 5+",
}

_ACTIVE_ZONE_DEFINITIONS = {
    "Cycling": TRAINING_ZONES,
    "Running": RUNNING_ZONES,
}


def set_strava_zone_definitions(power_zones=None, heart_rate_zones=None):
    definitions = {}
    if power_zones:
        definitions["Cycling"] = power_zones
    if heart_rate_zones:
        definitions["Running"] = heart_rate_zones
    for sport, zone_definitions in definitions.items():
        _ACTIVE_ZONE_DEFINITIONS[sport] = zone_definitions

def get_zone_definitions(sport="Cycling"):
    if str(sport or "Cycling").strip().casefold() == "running":
        return _ACTIVE_ZONE_DEFINITIONS["Running"]
    return _ACTIVE_ZONE_DEFINITIONS["Cycling"]


def get_training_zone(intensity, sport="Cycling"):
    for zone, limits in get_zone_definitions(sport).items():
        if limits["min"] <= intensity < limits["max"]:
            return zone
    return "Anaerobic"


def calculate_training_load(username,ctl_tc,atl_tc,activity_type="All"):
    stored_activities = load_activity_cache(username)
    if stored_activities is None or len(stored_activities) == 0:
        return pd.DataFrame(columns=["stress","CTL","ATL","TSB"])
    df = pd.DataFrame(stored_activities)
    if df.empty:
        return pd.DataFrame(columns=["stress","CTL","ATL","TSB"])
    df["date"] = pd.to_datetime(df["date"],errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")
    if "type" not in df.columns:
        df["type"] = ""
    df["type"] = df["type"].astype(str).str.replace("root='","",regex=False).str.replace("'","",regex=False)
    if activity_type != "All":
        df = df[df["type"] == activity_type]
    if df.empty or "stress" not in df.columns:
        return pd.DataFrame(columns=["stress","CTL","ATL","TSB"])
    df["stress"] = pd.to_numeric(df["stress"],errors="coerce").fillna(0)
    daily = df.groupby(pd.Grouper(key="date",freq="D"))["stress"].sum().to_frame()
    today = pd.Timestamp(date.today())
    daily = daily.reindex(
        pd.date_range(daily.index.min(), max(daily.index.max(), today), freq="D"),
        fill_value=0,
    )
    daily["CTL"] = daily["stress"].ewm(span=ctl_tc,adjust=False).mean()
    daily["ATL"] = daily["stress"].ewm(span=atl_tc,adjust=False).mean()
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

def rolling_km(series_df,value_col,km_window):
    df = series_df.copy()
    x = pd.to_numeric(df["distance_km"],errors="coerce").to_numpy()
    y = pd.to_numeric(df[value_col],errors="coerce").to_numpy()
    out = np.full(len(df),np.nan)
    for i in range(len(df)):
        if np.isnan(x[i]):
            continue
        start = x[i] - km_window
        mask = (x >= start) & (x <= x[i]) & ~np.isnan(y)
        if mask.any():
            out[i] = np.mean(y[mask])
    return out

def calculate_workout_metrics(workout):
    steps = workout["steps"]
    total_duration = sum(step["duration"] for step in steps)
    if total_duration == 0:
        return {"duration":0,"if":0,"tss":0,"steps":steps}
    weighted_intensity = sum(
        step["duration"] * (step["ftp"] / 100) ** 4
        for step in steps
    )
    intensity_factor = (weighted_intensity / total_duration) ** 0.25
    hours = total_duration / 3600
    tss = hours * intensity_factor ** 2 * 100
    return {
        "duration":round(total_duration),
        "if":round(intensity_factor,2),
        "tss":round(tss),
        "steps":steps
    }

def get_activity_zone_minutes(activity, ftp):
    display_zones = list(dict.fromkeys([ZONE_TO_DISPLAY[z] for z in ZONE_KEYS]))
    zones = {z: 0.0 for z in display_zones}
    if not ftp or pd.isna(ftp):
        return zones
    power_buckets = [
        ("power_0_50", 0, 50),
        ("power_50_100", 50, 100),
        ("power_100_150", 100, 150),
        ("power_150_200", 150, 200),
        ("power_200_250", 200, 250),
        ("power_250_300", 250, 300),
        ("power_300_350", 300, 350),
        ("power_350_400", 350, 400),
        ("power_400_450", 400, 450),
    ]
    for column, bucket_low, bucket_high in power_buckets:
        seconds = pd.to_numeric(activity.get(column, 0), errors="coerce")
        if pd.isna(seconds) or seconds <= 0:
            continue
        bucket_width = bucket_high - bucket_low
        bucket_minutes = float(seconds) / 60.0
        for zone_name in ZONE_KEYS:
            zone = TRAINING_ZONES[zone_name]
            zone_low = zone["min"] * float(ftp)
            zone_high = zone["max"] * float(ftp)
            overlap_low = max(bucket_low, zone_low)
            overlap_high = min(bucket_high, zone_high)
            if overlap_high > overlap_low:
                fraction = (overlap_high - overlap_low) / bucket_width
                display_zone = ZONE_TO_DISPLAY[zone_name]
                zones[display_zone] += bucket_minutes * fraction
    seconds_450_plus = pd.to_numeric(activity.get("power_450_plus", 0), errors="coerce")
    if not pd.isna(seconds_450_plus) and seconds_450_plus > 0:
        for zone_name in reversed(ZONE_KEYS):
            zone = TRAINING_ZONES[zone_name]
            if 450 >= zone["min"] * float(ftp):
                display_zone = ZONE_TO_DISPLAY[zone_name]
                zones[display_zone] += float(seconds_450_plus) / 60.0
                break
    return zones