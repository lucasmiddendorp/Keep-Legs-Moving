"""Availability helpers for weekly training-plan generation."""

from datetime import datetime


DAY_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def _hours_from_window(start, end):
    if not start or not end:
        return 0.0

    try:
        start_dt = datetime.strptime(start, "%H:%M")
        end_dt = datetime.strptime(end, "%H:%M")
    except Exception:
        return 0.0

    delta = (end_dt - start_dt).total_seconds() / 3600.0
    return max(0.0, delta)


def _day_hours(day_data):
    """Extract training hours from mixed availability formats."""
    if isinstance(day_data, bool):
        return 1.0 if day_data else 0.0

    if not isinstance(day_data, dict):
        return 0.0

    if "hours" in day_data:
        return max(0.0, float(day_data.get("hours", 0) or 0))

    if not day_data.get("available", False):
        return 0.0

    return _hours_from_window(day_data.get("start"), day_data.get("end"))


def get_day_weights(availability):
    """Return day->weight mapping for available days."""
    weights = {}

    for day in DAY_ORDER:
        hours = _day_hours(availability.get(day, {}))
        if hours > 0:
            # Keep at least a small positive weight to avoid zero-day allocation.
            weights[day] = max(0.5, hours)

    return weights


def get_available_days(availability):
    """Return available days ordered Monday..Sunday."""
    return list(get_day_weights(availability).keys())