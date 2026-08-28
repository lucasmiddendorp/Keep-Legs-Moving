"""Recovery analysis and validation rules for weekly plans."""

from datetime import timedelta

import pandas as pd


DAY_ORDER = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}


def _as_activity_frame(activities):
    if activities is None:
        return pd.DataFrame()
    if isinstance(activities, pd.DataFrame):
        return activities.copy()
    return pd.DataFrame(activities)


def _first_numeric(frame, columns):
    for column in columns:
        if column in frame:
            values = pd.to_numeric(frame[column], errors="coerce").dropna()
            if not values.empty:
                return float(values.iloc[-1])
    return None


def _numeric_column(frame, column, default=0.0):
    if column not in frame:
        return pd.Series(default, index=frame.index, dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce").fillna(default)


def _activity_duration_hours(frame):
    for column in ("moving_time", "elapsed_time", "duration_seconds"):
        if column in frame:
            return pd.to_numeric(frame[column], errors="coerce").fillna(0) / 3600
    if "duration" in frame:
        duration = pd.to_numeric(frame["duration"], errors="coerce").fillna(0)
        return duration / 3600 if duration.median() > 20 else duration / 60
    return pd.Series(0.0, index=frame.index)


def _hard_session_mask(frame):
    stress = _numeric_column(frame, "stress")
    intensity = pd.to_numeric(
        frame["IF"] if "IF" in frame else frame.get("intensity_factor", 0),
        errors="coerce",
    )
    if not isinstance(intensity, pd.Series):
        intensity = pd.Series(0.0, index=frame.index)
    intensity = intensity.fillna(0)
    return (stress >= 75) | (intensity >= 0.85)


def _athlete_level(frame):
    for column in ("athlete_level", "level"):
        if column in frame and frame[column].notna().any():
            return str(frame[column].dropna().iloc[-1]).lower()
    return ""


def calculate_recovery_profile(activities, athlete_level=None):
    """Estimate individualized recovery needs from recent activity history.

    The input may be a pandas DataFrame or an iterable of activity records. The
    most recent eight weeks are used, including zero-activity weeks, so the
    frequency metrics reflect actual recovery days rather than only active data.
    """
    frame = _as_activity_frame(activities)
    empty_profile = {
        "avg_training_days": 0.0,
        "avg_hours_per_week": 0.0,
        "avg_stress_per_week": 0.0,
        "avg_hard_sessions": 0.0,
        "ctl": None,
        "atl": None,
        "tsb": None,
        "baseline_rest_days": 2,
        "rest_days": 2,
        "max_consecutive_training_days": 0,
    }
    if frame.empty or "date" not in frame:
        return empty_profile

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame.dropna(subset=["date"]).sort_values("date")
    if frame.empty:
        return empty_profile

    end_date = frame["date"].max().normalize()
    start_date = end_date - timedelta(weeks=8) + timedelta(days=1)
    frame = frame[frame["date"] >= start_date].copy()
    if frame.empty:
        return empty_profile

    frame["training_day"] = frame["date"].dt.normalize()
    frame["hours"] = _activity_duration_hours(frame)
    frame["stress_value"] = _numeric_column(frame, "stress")
    frame["hard_session"] = _hard_session_mask(frame)

    frame["week_start"] = start_date + pd.to_timedelta(
        ((frame["date"].dt.normalize() - start_date).dt.days // 7) * 7,
        unit="D",
    )
    week_index = pd.date_range(start=start_date, end=end_date, freq="7D")
    weekly = frame.groupby("week_start").agg(
        training_days=("training_day", "nunique"),
        hours=("hours", "sum"),
        stress=("stress_value", "sum"),
        hard_sessions=("hard_session", "sum"),
    )
    weekly = weekly.reindex(week_index, fill_value=0)

    ctl = _first_numeric(frame, ("CTL", "ctl"))
    atl = _first_numeric(frame, ("ATL", "atl"))
    tsb = _first_numeric(frame, ("TSB", "tsb"))
    if ctl is None or atl is None:
        daily = frame.groupby("training_day")["stress_value"].sum()
        daily = daily.reindex(pd.date_range(start=start_date, end=end_date, freq="D"), fill_value=0)
        derived_ctl = daily.ewm(span=42, adjust=False).mean().iloc[-1]
        derived_atl = daily.ewm(span=7, adjust=False).mean().iloc[-1]
        ctl = float(derived_ctl) if ctl is None else ctl
        atl = float(derived_atl) if atl is None else atl
    if tsb is None and ctl is not None and atl is not None:
        tsb = ctl - atl

    avg_days = float(weekly["training_days"].mean())
    avg_hours = float(weekly["hours"].mean())
    avg_stress = float(weekly["stress"].mean())
    avg_hard = float(weekly["hard_sessions"].mean())

    baseline_rest = round(7 - avg_days)
    baseline_rest = max(1, min(4, baseline_rest))
    level = str(athlete_level or _athlete_level(frame)).lower()
    if any(value in level for value in ("beginner", "novice", "recreational")):
        baseline_rest += 1
    elif any(value in level for value in ("advanced", "elite")):
        baseline_rest -= 1

    if (tsb is not None and tsb < -10) or (atl is not None and ctl is not None and atl > ctl * 1.15):
        baseline_rest += 1
    if avg_stress > 500 or avg_hard > 2.5:
        baseline_rest += 1
    baseline_rest = max(1, min(5, baseline_rest))

    training_days = set(frame["training_day"])
    max_consecutive = 0
    current_streak = 0
    for day in pd.date_range(start=start_date, end=end_date, freq="D"):
        if day in training_days:
            current_streak += 1
            max_consecutive = max(max_consecutive, current_streak)
        else:
            current_streak = 0

    return {
        "avg_training_days": round(avg_days, 2),
        "avg_hours_per_week": round(avg_hours, 2),
        "avg_stress_per_week": round(avg_stress, 2),
        "avg_hard_sessions": round(avg_hard, 2),
        "ctl": round(ctl, 2) if ctl is not None else None,
        "atl": round(atl, 2) if atl is not None else None,
        "tsb": round(tsb, 2) if tsb is not None else None,
        "baseline_rest_days": baseline_rest,
        "rest_days": baseline_rest,
        "max_consecutive_training_days": max_consecutive,
    }


def validate_recovery(schedule, max_hard_sessions=2, min_gap_days=1):
    hard_categories = {"VO2max", "Threshold"}

    hard = [
        item
        for item in schedule
        if item.get("category") in hard_categories
    ]

    if len(hard) > max_hard_sessions:
        return False

    hard_day_index = sorted(
        DAY_ORDER.get(item.get("day"), 99)
        for item in hard
    )

    for idx in range(1, len(hard_day_index)):
        if hard_day_index[idx] - hard_day_index[idx - 1] <= min_gap_days:
            return False

    return True