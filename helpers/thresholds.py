from typing import Any, Iterable, Optional

import numpy as np
import pandas as pd


RUNNING_TEST_SECONDS = 6 * 60
CYCLING_TEST_SECONDS = 20 * 60
POWER_CURVE_DURATIONS = [5, 15, 30, 60, 120, 300, 600, 1200, 1800, 3600]
RUNNING_CURVE_DISTANCES = [500, 1000, 2000, 5000, 10000, 21097.5, 42195]
CURVE_CACHE_VERSION = 4


def _activity_frames(records: Iterable[dict[str, Any]]) -> Iterable[pd.DataFrame]:
    frame = pd.DataFrame(records or [])
    if frame.empty or "activity_id" not in frame.columns:
        return []
    return (activity for _, activity in frame.groupby("activity_id", sort=False))


def best_6_min_running(records: Iterable[dict[str, Any]]) -> Optional[float]:
    """Return the greatest distance, in metres, covered in six minutes."""
    best_distance = None
    for activity in _activity_frames(records):
        if "time" not in activity.columns or "distance" not in activity.columns:
            continue
        elapsed = pd.to_numeric(activity["time"], errors="coerce").to_numpy(float)
        distance = pd.to_numeric(activity["distance"], errors="coerce").to_numpy(float)
        valid = np.isfinite(elapsed) & np.isfinite(distance)
        elapsed = elapsed[valid]
        distance = distance[valid]
        if len(elapsed) < 2:
            continue
        order = np.argsort(elapsed)
        elapsed = elapsed[order]
        distance = distance[order]
        elapsed, unique_indices = np.unique(elapsed, return_index=True)
        distance = distance[unique_indices]
        if elapsed[-1] - elapsed[0] < RUNNING_TEST_SECONDS:
            continue
        end_times = elapsed[elapsed >= elapsed[0] + RUNNING_TEST_SECONDS]
        start_times = end_times - RUNNING_TEST_SECONDS
        start_distances = np.interp(start_times, elapsed, distance)
        end_distances = np.interp(end_times, elapsed, distance)
        distances = end_distances - start_distances
        if len(distances):
            distance_value = float(np.max(distances))
            best_distance = max(best_distance or 0.0, distance_value)
    return best_distance


def best_6_min_running_pace(records: Iterable[dict[str, Any]]) -> Optional[float]:
    """Return the best six-minute running pace in minutes per kilometre."""
    distance = best_6_min_running(records)
    if not distance or distance <= 0:
        return None
    return RUNNING_TEST_SECONDS / 60 / (distance / 1000)


def calculated_running_threshold_pace(best_six_minute_pace: Optional[float]) -> Optional[float]:
    """Return threshold pace after reducing six-minute speed by 20 percent."""
    if best_six_minute_pace is None or best_six_minute_pace <= 0:
        return None
    return best_six_minute_pace * 1.2


def best_20_min_cycling(records: Iterable[dict[str, Any]]) -> Optional[float]:
    """Return the highest twenty-minute average cycling power in watts."""
    curve = build_power_curve(records)
    return next(
        (float(point["value"]) for point in curve if point["duration"] == CYCLING_TEST_SECONDS),
        None,
    )

def build_power_curve(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for duration in POWER_CURVE_DURATIONS:
        best = None
        for activity in _activity_frames(records):
            if "time" not in activity.columns or "watts" not in activity.columns:
                continue
            frame = pd.DataFrame({
                "time": pd.to_numeric(activity["time"], errors="coerce"),
                "watts": pd.to_numeric(activity["watts"], errors="coerce"),
            })
            if "moving" in activity.columns:
                frame["moving"] = activity["moving"].fillna(False).astype(bool)
            else:
                frame["moving"] = True
            frame = frame.dropna(subset=["time"])
            if frame.empty:
                continue
            frame = frame.sort_values("time").drop_duplicates("time")
            frame["gap"] = frame["time"].diff().fillna(1) > 1.5
            frame["invalid"] = frame["watts"].isna() | ~frame["moving"]
            frame["segment"] = (frame["gap"] | frame["invalid"]).cumsum()
            for _, segment in frame[~frame["invalid"]].groupby("segment"):
                if segment["time"].iloc[-1] - segment["time"].iloc[0] < duration:
                    continue
                samples = np.arange(segment["time"].iloc[0], segment["time"].iloc[-1] + 1)
                values = np.interp(samples, segment["time"], segment["watts"])
                averages = np.convolve(values, np.ones(duration), mode="valid") / duration
                value = float(np.max(averages))
                if best is None or value > best:
                    best = value
        if best is not None:
            result.append({"duration": duration, "value": best})
    return result


def build_running_curve(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for distance_target in RUNNING_CURVE_DISTANCES:
        best_speed = None
        for activity in _activity_frames(records):
            if "time" not in activity.columns or "distance" not in activity.columns:
                continue
            frame = pd.DataFrame({
                "time": pd.to_numeric(activity["time"], errors="coerce"),
                "distance": pd.to_numeric(activity["distance"], errors="coerce"),
            }).dropna()
            if frame.empty:
                continue
            frame = frame.sort_values("distance").drop_duplicates("distance")
            if frame["distance"].iloc[-1] - frame["distance"].iloc[0] < distance_target:
                continue
            ends = frame["distance"][frame["distance"] >= frame["distance"].iloc[0] + distance_target]
            starts = ends - distance_target
            duration = np.interp(ends, frame["distance"], frame["time"]) - np.interp(starts, frame["distance"], frame["time"])
            valid = duration > 0
            if valid.any():
                value = float(np.max(distance_target / duration[valid]))
                best_speed = max(best_speed or 0.0, value)
        if best_speed:
            result.append({"distance": distance_target, "speed": best_speed})
    return result
