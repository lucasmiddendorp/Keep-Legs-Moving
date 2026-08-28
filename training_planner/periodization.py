"""Independent periodized training-plan generator for Cycling Analytics."""

from datetime import date, datetime, timedelta
from itertools import permutations

import pandas as pd

from .availability import get_available_days, get_day_weights
from .distribution import calculate_distribution
from .workout_selection import select_workout
from .recovery import calculate_recovery_profile

DAY_ORDER = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]
HARD_TYPES = {"Threshold", "VO2max"}


def _parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return None


def _hours(day_data):
    if not isinstance(day_data, dict):
        return 0.0
    if day_data.get("hours") is not None:
        return max(0.0, float(day_data.get("hours") or 0))
    return 0.0


def _workout_hours(workout):
    return sum(
        float(step.get("duration_seconds", 0) or 0)
        for step in (workout or {}).get("steps", [])
    ) / 3600


def classify_workout(workout):
    """Return conservative content facts used to admit a workout to a slot."""
    duration = _workout_hours(workout)
    tss = float((workout or {}).get("target_tss", 0) or 0)
    intensity = sum(
        float(step.get("intensity", 0) or 0) * float(step.get("duration_seconds", 0) or 0)
        for step in (workout or {}).get("steps", [])
    ) / max(1, sum(float(step.get("duration_seconds", 0) or 0) for step in (workout or {}).get("steps", [])))
    peak_intensity = max(
        (float(step.get("intensity", 0) or 0) for step in (workout or {}).get("steps", [])),
        default=0,
    )
    category = (workout or {}).get("_category", "")
    hard = category in HARD_TYPES or intensity >= 88 or tss / max(duration, 0.25) >= 85
    return {
        "duration_hours": duration,
        "tss": tss,
        "intensity": intensity,
        "peak_intensity": peak_intensity,
        "hard": hard,
    }


def workout_is_safe(category, workout, max_hours):
    facts = classify_workout(workout)
    if facts["duration_hours"] > max_hours:
        return False
    ceilings = {"VO2max": 1.25, "Threshold": 1.5, "Tempo": 2.5}
    if category in ceilings and facts["duration_hours"] > ceilings[category]:
        return False
    if category == "Endurance" and facts["intensity"] >= 82:
        return False
    if category == "VO2max" and facts["peak_intensity"] < 100:
        return False
    return True


def _phase(weeks_to_goal):
    if weeks_to_goal <= 1:
        return "taper"
    if weeks_to_goal <= 3:
        return "peak"
    if weeks_to_goal <= 8:
        return "build"
    return "base"


def calculate_event_demand(event_distance_km, climb_m=0, event_type="endurance", target_ftp=None):
    """Convert basic event demands into conservative planning targets."""
    distance = max(0.0, float(event_distance_km or 0))
    climb = max(0.0, float(climb_m or 0))
    difficulty = 1.0 + min(0.35, distance / 500) + min(0.25, climb / 10000)
    if target_ftp:
        difficulty *= max(0.8, min(1.2, 250 / float(target_ftp)))
    return {
        "weekly_tss": round(max(200.0, min(900.0, 350.0 * difficulty))),
        "long_ride_hours": round(max(2.0, min(8.0, distance / 30.0)), 1),
        "event_type": str(event_type or "endurance"),
    }


def _phase_distribution(goal, phase):
    phase_mix = {
        "base": {"Endurance": 0.60, "Tempo": 0.25, "Threshold": 0.10, "VO2max": 0.05},
        "build": {"Endurance": 0.45, "Tempo": 0.20, "Threshold": 0.25, "VO2max": 0.10},
        "peak": {"Endurance": 0.35, "Tempo": 0.15, "Threshold": 0.30, "VO2max": 0.20},
        "taper": {"Endurance": 0.55, "Tempo": 0.25, "Threshold": 0.15, "VO2max": 0.05},
    }[phase]
    goal_mix = calculate_distribution(goal)
    return {
        category: goal_mix[category] * 0.4 + phase_mix[category] * 0.6
        for category in phase_mix
    }


def _intensity_budget(phase, target_tss, available_minutes):
    """Return phase-specific TSS and zone-minute targets."""
    ratios = {
        "base": (0.88, 0.08, 0.04),
        "build": (0.78, 0.10, 0.12),
        "peak": (0.70, 0.08, 0.22),
        "taper": (0.90, 0.06, 0.04),
    }[phase]
    total_minutes = max(1.0, float(available_minutes))
    z4 = round(total_minutes * ratios[2] * 0.7)
    z5 = round(total_minutes * ratios[2] * 0.3)
    return {
        "easy_tss": round(target_tss * ratios[0]),
        "moderate_tss": round(target_tss * ratios[1]),
        "hard_tss": round(target_tss * ratios[2]),
        "zone_minutes": {
            "Zone 1+2": round(total_minutes * ratios[0]),
            "Zone 3": round(total_minutes * ratios[1]),
            "Zone 4": z4,
            "Zone 5+": z5,
        },
    }


def _remaining_zone_budget(zone_budget, completed_zone_minutes):
    remaining = {}
    for zone in ("Zone 1+2", "Zone 3", "Zone 4", "Zone 5+"):
        minutes = float((zone_budget or {}).get(zone, 0) or 0)
        completed = float((completed_zone_minutes or {}).get(zone, 0) or 0)
        remaining[zone] = max(0.0, minutes - completed)
    return remaining


def _achievable_week_tss(available_days, availability, workouts, training_hours=None, recovery=None):
    training_hours = training_hours if training_hours is not None else sum(_hours(availability.get(day, {})) for day in available_days)
    if training_hours <= 0:
        return 0.0
    max_workout_tss = max(
        (float((workout or {}).get("target_tss", workout.get("estimated_tss", 0)) or 0) for workout in workouts),
        default=0.0,
    )
    if max_workout_tss <= 0:
        return 0.0
    historical_hours = float((recovery or {}).get("avg_hours_per_week", 0) or 0)
    historical_tss = float((recovery or {}).get("avg_stress_per_week", 0) or 0)
    historical_rate = historical_tss / historical_hours if historical_hours > 0 else 80.0
    sustainable_rate = max(50.0, min(90.0, historical_rate * 1.1))
    by_hours = training_hours * sustainable_rate
    by_days = len(available_days) * max_workout_tss * 1.2
    return float(min(by_hours, by_days, 900.0))


def _supported_long_ride_hours(requested_hours, target_tss, phase, recovery):
    if not requested_hours or target_tss <= 0:
        return None
    phase_share = {
        "base": 0.45,
        "build": 0.50,
        "peak": 0.55,
        "taper": 0.35,
    }[phase]
    supported_hours = float(target_tss) * phase_share / 70.0
    if supported_hours < 2.5:
        return None
    history_hours = float(recovery.get("avg_hours_per_week", 0) or 0)
    if history_hours > 0:
        supported_hours = min(supported_hours, history_hours * 0.75)
    if int(recovery.get("rest_days", 1) or 1) >= 4:
        supported_hours = min(supported_hours, 4.0)
    return round(min(float(requested_hours), supported_hours), 1)


def _high_availability_days(days, availability):
    if not days:
        return []
    highest = max(_hours(availability.get(day, {})) for day in days)
    threshold = max(3.0, highest * 0.8)
    return [day for day in days if _hours(availability.get(day, {})) >= threshold]


def _workout_zone_minutes(workout):
    zones = {"Zone 1+2": 0.0, "Zone 3": 0.0, "Zone 4": 0.0, "Zone 5+": 0.0}
    for step in (workout or {}).get("steps", []):
        intensity = float(step.get("intensity", 0) or 0)
        minutes = float(step.get("duration_seconds", 0) or 0) / 60
        if intensity < 76:
            zones["Zone 1+2"] += minutes
        elif intensity < 91:
            zones["Zone 3"] += minutes
        elif intensity <= 105:
            zones["Zone 4"] += minutes
        else:
            zones["Zone 5+"] += minutes
    return zones


def _category_counts(
    training_days,
    goal,
    phase,
    max_hard_sessions=2,
    ensure_vo2=False,
    rotation_state=None,
):
    distribution = _phase_distribution(goal, phase)
    state = rotation_state if rotation_state is not None else {}
    for category, weight in distribution.items():
        state[category] = state.get(category, 0.0) + weight * training_days
    counts = {category: 0 for category in distribution}
    hard_count = 0
    for _ in range(training_days):
        eligible = [
            category for category in state
            if category not in HARD_TYPES or hard_count < max_hard_sessions
        ]
        if not eligible:
            break
        category = max(eligible, key=state.get)
        counts[category] += 1
        state[category] -= 1.0
        if category in HARD_TYPES:
            hard_count += 1
    categories = [category for category, count in counts.items() for _ in range(count)]
    if ensure_vo2 and "VO2max" not in categories and max_hard_sessions > 0:
        replacement = next(
            (category for category in ("Tempo", "Endurance") if category in categories),
            None,
        )
        if replacement and not any(category in HARD_TYPES for category in categories):
            categories[categories.index(replacement)] = "VO2max"
    return categories


def _valid_sequences(
    days,
    categories,
    weights,
    rest_days=1,
    max_hard_sessions=2,
    max_consecutive_days=5,
):
    longest_day = max(days, key=lambda item: weights.get(item, 0))
    lowest_days = sorted(days, key=lambda item: weights.get(item, 0))
    vo2_count = categories.count("VO2max")
    hard_count = sum(category in HARD_TYPES for category in categories)
    if hard_count > max_hard_sessions:
        return
    vo2_day = next((day for day in lowest_days if day != longest_day), None)
    if vo2_count and vo2_day is None:
        vo2_count = 0

    def build(index, remaining, previous, schedule, training_streak, rests_left):
        if index == len(days):
            if remaining or rests_left:
                return
            if vo2_count and not any(
                day == vo2_day and category == "VO2max"
                for day, category in schedule
            ):
                return
            yield list(schedule)
            return

        day = days[index]
        if day == longest_day and "Endurance" not in remaining:
            return
        if previous in HARD_TYPES:
            yield from build(index + 1, remaining, None, schedule + [(day, None)], 0, rests_left)
            return
        if not remaining and rests_left:
            yield from build(index + 1, remaining, None, schedule + [(day, None)], 0, rests_left - 1)
            return
        if rests_left and day != longest_day:
            yield from build(index + 1, remaining, None, schedule + [(day, None)], 0, rests_left - 1)

        choices = [
            category for category in set(remaining)
            if category != previous
            and not (category in HARD_TYPES and previous in HARD_TYPES)
        ]
        if training_streak >= max_consecutive_days and day != longest_day:
            yield from build(index + 1, remaining, None, schedule + [(day, None)], 0, rests_left)
            return
        if day == longest_day:
            choices = [category for category in choices if category == "Endurance"]
            if not choices and "Endurance" in remaining:
                choices = ["Endurance"]
        if "VO2max" in choices and index + 1 < len(days) and days[index + 1] == longest_day:
            choices.remove("VO2max")
        if day == vo2_day and vo2_count:
            choices = ["VO2max"] if "VO2max" in remaining else []
        for category in choices:
            next_remaining = list(remaining)
            next_remaining.remove(category)
            yield from build(
                index + 1,
                next_remaining,
                category,
                schedule + [(day, category)],
                training_streak + 1,
                rests_left,
            )

    yield from build(0, list(categories), None, [], 0, rest_days)


def _fallback_sequence(
    days,
    categories,
    weights,
    rest_days=1,
    max_hard_sessions=2,
    max_consecutive_days=5,
    ensure_vo2=False,
):
    sequence = next(
        _valid_sequences(
            days,
            categories,
            weights,
            rest_days=rest_days,
            max_hard_sessions=max_hard_sessions,
            max_consecutive_days=max_consecutive_days,
        ),
        None,
    )
    if sequence is not None:
        return sequence
    longest_day = max(days, key=lambda item: weights.get(item, 0))
    longest_index = days.index(longest_day)
    remaining = list(categories)
    result = [(day, None) for day in days]
    result[longest_index] = (longest_day, "Endurance")
    if "Endurance" in remaining:
        remaining.remove("Endurance")
    if ensure_vo2 and "VO2max" in remaining:
        vo2_day = min(
            (day for day in days if day != longest_day),
            key=lambda day: weights.get(day, 0),
            default=None,
        )
        if vo2_day is not None:
            vo2_index = days.index(vo2_day)
            result[vo2_index] = (vo2_day, "VO2max")
            remaining.remove("VO2max")
            if vo2_index + 1 < len(days) and days[vo2_index + 1] != longest_day:
                result[vo2_index + 1] = (days[vo2_index + 1], None)
    for index, day in enumerate(days):
        if index == longest_index or not remaining:
            continue
        previous = result[index - 1][1] if index else None
        if previous is None or all(
            category != previous and not (category in HARD_TYPES and previous in HARD_TYPES)
            for category in remaining
        ):
            result[index] = (day, remaining.pop(0))
    return result


def _select_week(days, availability, categories, target_tss, workouts, rest_days=1, max_hard_sessions=2, max_consecutive_days=5, used_files=None, long_ride_hours=None, intensity_budget=None, ensure_vo2=False):
    weights = get_day_weights(availability)
    high_availability_days = _high_availability_days(days, availability)
    candidates = list(_valid_sequences(days, categories, weights, rest_days, max_hard_sessions, max_consecutive_days))
    if not candidates:
        candidates = [_fallback_sequence(days, categories, weights, rest_days, max_hard_sessions, max_consecutive_days, ensure_vo2)]

    best_schedule = None
    best_score = float("inf")
    for sequence_index, sequence in enumerate(candidates):
        schedule = []
        workout_options = []
        session_count = sum(1 for _, category in sequence if category)
        training_hours = sum(
            _hours(availability.get(day, {}))
            for day, category in sequence
            if category
        )
        training_days = [day for day, category in sequence if category]
        rest_days = [day for day, category in sequence if category is None]
        long_ride_candidates = [
            day for day, category in sequence
            if category == "Endurance" and day in high_availability_days
        ]
        primary_long_day = max(
            long_ride_candidates,
            key=lambda day: _hours(availability.get(day, {})),
            default=None,
        )
        secondary_long_days = {
            day for day in long_ride_candidates
            if primary_long_day is not None
            and abs(days.index(day) - days.index(primary_long_day)) == 1
            and day != primary_long_day
        }
        for day, category in sequence:
            if category is None:
                workout_options.append([])
                schedule.append({
                    "day": day,
                    "category": None,
                    "target_tss": 0,
                    "workout": None,
                    "rest": True,
                })
                continue
            day_hours = _hours(availability.get(day, {}))
            day_target = target_tss * day_hours / max(training_hours, 1.0)
            options = [
                workout for workout in workouts
                if workout.get("_category") == category
                and workout_is_safe(category, workout, day_hours)
                and workout.get("_file") not in (used_files or set())
            ] or [
                workout for workout in workouts
                if workout.get("_category") == category
                and workout_is_safe(category, workout, day_hours)
            ]
            workout = select_workout(category, "C", options, target_tss=day_target) if options else None
            requested_hours = None
            if day == primary_long_day:
                requested_hours = long_ride_hours
            elif day in secondary_long_days and long_ride_hours:
                requested_hours = round(long_ride_hours * 0.6, 1)
            if category == "Endurance" and requested_hours:
                long_options = [item for item in options if _workout_hours(item) <= requested_hours]
                if long_options:
                    workout = min(long_options, key=lambda item: abs(_workout_hours(item) - requested_hours))
            schedule.append({
                "day": day,
                "category": category,
                "target_tss": round(day_target),
                "workout": workout,
                "rest": False,
            })
            workout_options.append(options)

        def workout_tss(item):
            return float((item or {}).get("target_tss", (item or {}).get("estimated_tss", 0)) or 0)

        current_total = sum(workout_tss(item.get("workout")) for item in schedule)
        for index, options in enumerate(workout_options):
            if not options:
                continue
            current_workout = schedule[index].get("workout")
            best_workout = current_workout
            best_error = abs(current_total - target_tss)
            for option in options:
                candidate_total = current_total - workout_tss(current_workout) + workout_tss(option)
                candidate_error = abs(candidate_total - target_tss)
                if candidate_error < best_error:
                    best_workout = option
                    best_error = candidate_error
            if best_workout is not current_workout:
                current_total = current_total - workout_tss(current_workout) + workout_tss(best_workout)
                schedule[index]["workout"] = best_workout
        actual = sum(float((item["workout"] or {}).get("target_tss", 0) or 0) for item in schedule)
        duration_error = 0.0
        if long_ride_hours:
            for item in schedule:
                if item["day"] == primary_long_day:
                    duration_error = abs(_workout_hours(item.get("workout")) - long_ride_hours) * 20
        hard_count = sum(item["category"] in HARD_TYPES for item in schedule)
        hard_tss = sum(
            float((item.get("workout") or {}).get("target_tss", 0) or 0)
            for item in schedule
            if item["category"] in HARD_TYPES
        )
        hard_budget = float((intensity_budget or {}).get("hard_tss", hard_tss))
        zone_totals = {zone: 0.0 for zone in ("Zone 1+2", "Zone 3", "Zone 4", "Zone 5+")}
        for item in schedule:
            for zone, minutes in _workout_zone_minutes(item.get("workout")).items():
                zone_totals[zone] += minutes
        planned_minutes = sum(_hours(availability.get(day, {})) * 60 for day, category in sequence if category)
        if intensity_budget and planned_minutes > 0:
            total_minutes = float(intensity_budget.get("_planned_minutes", planned_minutes) or planned_minutes)
            scale = planned_minutes / max(1.0, total_minutes)
            zone_budget = {
                zone: max(0.0, float(minutes) * scale)
                for zone, minutes in (intensity_budget or {}).get("zone_minutes", {}).items()
            }
        else:
            zone_budget = (intensity_budget or {}).get("zone_minutes", {})
        zone_error = (
            abs(zone_totals["Zone 1+2"] - float(zone_budget.get("Zone 1+2", zone_totals["Zone 1+2"])))
            + abs(zone_totals["Zone 3"] - float(zone_budget.get("Zone 3", zone_totals["Zone 3"])))
            + abs(zone_totals["Zone 4"] - float(zone_budget.get("Zone 4", zone_totals["Zone 4"])))
            + abs(zone_totals["Zone 5+"] - float(zone_budget.get("Zone 5+", zone_totals["Zone 5+"])))
        )
        score = (
            abs(actual - target_tss) * 20
            + duration_error
            + abs(hard_tss - hard_budget) * 0.25
            + zone_error * 0.05
            + max(0, hard_count - max_hard_sessions) * 1000
            + max(0, 7 - session_count) * 50
        )
        if score < best_score:
            best_schedule = schedule
            best_score = score

        print(
            "PLAN_DEBUG",
            {
                "sequence_index": sequence_index,
                "phase": intensity_budget.get("phase") if intensity_budget else None,
                "target_tss": round(target_tss, 1),
                "max_realistic_tss": round(float((intensity_budget or {}).get("max_realistic_tss", target_tss)), 1),
                "training_days": training_days,
                "rest_days": rest_days,
                "categories": [category for _, category in sequence if category],
                "actual_tss": round(actual, 1),
                "delta_tss": round(actual - target_tss, 1),
                "score": round(score, 2),
                "hard_tss": round(hard_tss, 1),
                "hard_budget": round(hard_budget, 1),
                "zone_totals": zone_totals,
                "zone_budget": zone_budget,
                "available_hours": {
                    day: round(_hours(availability.get(day, {})), 1)
                    for day in days
                },
                "planned_hours": {
                    item["day"]: round(_workout_hours(item.get("workout")), 2)
                    for item in schedule
                },
                "day_hours": {
                    item["day"]: {
                        "available": round(_hours(availability.get(item["day"], {})), 1),
                        "planned": round(_workout_hours(item.get("workout")), 2),
                        "primary_long_ride": item["day"] == primary_long_day,
                    }
                    for item in schedule
                },
                "primary_long_ride": primary_long_day,
            },
        )
    return best_schedule or []


def reforecast_plan(plan, completed_activities, current_date=None):
    """Adjust future weekly targets from completed-versus-planned TSS."""
    if not isinstance(plan, list):
        return []
    activities = completed_activities.copy() if isinstance(completed_activities, pd.DataFrame) else pd.DataFrame(completed_activities or [])
    if activities.empty or "date" not in activities:
        return plan
    activities["date"] = pd.to_datetime(activities["date"], errors="coerce")
    activities["stress"] = pd.to_numeric(
        activities["stress"] if "stress" in activities else 0,
        errors="coerce",
    )
    if not isinstance(activities["stress"], pd.Series):
        activities["stress"] = pd.Series(0.0, index=activities.index)
    activities["stress"] = activities["stress"].fillna(0)
    cutoff = pd.Timestamp(current_date or date.today())
    completed = activities[activities["date"] < cutoff]
    if completed.empty:
        return plan
    actual_by_week = completed.groupby(completed["date"].dt.to_period("W-MON"))["stress"].sum()
    updated = [dict(item) for item in plan]
    for item in updated:
        if pd.Timestamp(item["date"]) < cutoff:
            continue
        week = pd.Timestamp(item["date"]).to_period("W-MON")
        actual = float(actual_by_week.get(week, 0))
        planned = float(item.get("week_target_tss", 0) or 0)
        if planned and actual:
            adjustment = max(0.85, min(1.1, actual / planned))
            item["week_target_tss"] = round(planned * adjustment)
            item["reforecast_factor"] = round(adjustment, 2)
    return updated


def calculate_athlete_state(activities, plan=None, current_date=None, ftp=0):
    """Summarize recent load, intensity, recovery, and plan adherence."""
    frame = activities.copy() if isinstance(activities, pd.DataFrame) else pd.DataFrame(activities or [])
    cutoff = pd.Timestamp(current_date or date.today()).normalize()
    recovery = calculate_recovery_profile(frame, athlete_level=None)
    state = {
        "ctl": recovery.get("ctl"),
        "atl": recovery.get("atl"),
        "tsb": recovery.get("tsb"),
        "recent_tss": 0.0,
        "recent_volume_hours": 0.0,
        "zones": {},
        "hard_sessions": recovery.get("avg_hard_sessions", 0.0),
        "recovery": recovery,
        "adherence": None,
    }
    if not frame.empty and "date" in frame:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        recent = frame[frame["date"] >= cutoff - pd.Timedelta(days=27)]
        if "stress" in recent:
            state["recent_tss"] = float(pd.to_numeric(recent["stress"], errors="coerce").fillna(0).sum())
        for column in ("moving_time", "elapsed_time", "duration_seconds"):
            if column in recent:
                state["recent_volume_hours"] = float(pd.to_numeric(recent[column], errors="coerce").fillna(0).sum()) / 3600
                break
        state["hard_sessions"] = int(recent.shape[0]) if "stress" not in recent else int((pd.to_numeric(recent["stress"], errors="coerce").fillna(0) >= 75).sum())
        for column in ("time_z1_hr", "time_z2_hr", "time_z3_hr", "time_z4_hr", "time_z5_hr"):
            if column in recent:
                state["zones"][column] = float(pd.to_numeric(recent[column], errors="coerce").fillna(0).sum()) / 60
        if ftp and ftp > 0 and "moving_time" in recent:
            power = recent.get("weighted_average_watts", recent.get("average_watts"))
            if power is not None:
                for _, activity in recent.iterrows():
                    value = power.loc[activity.name] if activity.name in power.index else None
                    if pd.isna(value):
                        continue
                    intensity = float(value) / float(ftp)
                    if intensity < 0.76:
                        zone = "Zone 1+2"
                    elif intensity < 0.91:
                        zone = "Zone 3"
                    elif intensity <= 1.05:
                        zone = "Zone 4"
                    else:
                        zone = "Zone 5+"
                    state["zones"][zone] = state["zones"].get(zone, 0.0) + float(activity.get("moving_time", 0) or 0) / 3600
    if plan:
        scheduled = {
            item.get("date") for item in plan
            if item.get("date") and item.get("workout") and pd.Timestamp(item["date"]) < cutoff
        }
        completed = set()
        if not frame.empty and "date" in frame:
            completed = {
                value.date().isoformat() for value in frame["date"].dropna()
                if value < cutoff
            }
        if scheduled:
            state["adherence"] = round(len(scheduled & completed) / len(scheduled), 3)
    return state


def generate_long_term_plan(*args, **kwargs):
    """Generate the stable full-horizon plan toward the goal or event."""
    return _generate_plan(*args, **kwargs)


def reoptimize_future_plan(
    plan,
    goal,
    goal_date,
    availability,
    workouts,
    baseline_tss,
    progression=8,
    activities=None,
    athlete_level=None,
    event_demand=None,
    completed_zone_minutes=None,
    completed_tss=0.0,
    current_date=None,
    horizon_days=14,
):
    """Re-optimize only the next 7-14 days and preserve completed plan rows."""
    if not isinstance(plan, list):
        return generate_long_term_plan(
            goal, goal_date, availability, workouts, baseline_tss,
            progression, current_date, activities, athlete_level,
            event_demand, completed_zone_minutes, completed_tss,
        )
    cutoff = _parse_date(current_date) or date.today()
    horizon = cutoff + timedelta(days=max(7, min(14, int(horizon_days))))
    future_rows = [
        item for item in plan
        if item.get("date") and cutoff < _parse_date(item["date"]) <= horizon
    ]
    if not future_rows:
        return plan
    baseline = max(
        (float(item.get("week_target_tss", 0) or 0) for item in future_rows),
        default=float(baseline_tss or 0),
    )
    adaptive = generate_long_term_plan(
        goal=goal,
        goal_date=horizon,
        availability=availability,
        workouts=workouts,
        baseline_tss=baseline,
        progression=progression,
        start_date=cutoff + timedelta(days=1),
        activities=activities,
        athlete_level=athlete_level,
        event_demand=event_demand,
        completed_zone_minutes=completed_zone_minutes,
        completed_tss=completed_tss,
    )
    replacement = {
        item["date"]: item for item in adaptive
        if item.get("date") and cutoff < _parse_date(item["date"]) <= horizon
    }
    return [
        replacement.get(item.get("date"), item)
        if item.get("date") and cutoff < _parse_date(item["date"]) <= horizon
        else item
        for item in plan
    ]


def _generate_plan(
    goal,
    goal_date,
    availability,
    workouts,
    baseline_tss,
    progression=8,
    start_date=None,
    activities=None,
    athlete_level=None,
    event_demand=None,
    completed_zone_minutes=None,
    completed_tss=0.0,
):
    """Generate a complete dated plan through the goal date."""
    first_day = start_date or date.today()
    goal_day = _parse_date(goal_date)
    if goal_day is None or goal_day < first_day:
        return []

    first_week = first_day - timedelta(days=first_day.weekday())
    last_week = goal_day - timedelta(days=goal_day.weekday())
    weeks = ((last_week - first_week).days // 7) + 1
    plan = []
    previous_workouts = None
    previous_target = None
    used_files = set()
    vo2_history = []
    category_rotation_state = {}
    recovery = calculate_recovery_profile(activities, athlete_level=athlete_level)
    max_hard_sessions = 2
    if recovery["avg_hard_sessions"] > 2.5 or recovery["tsb"] is not None and recovery["tsb"] < -10:
        max_hard_sessions = 1
    if athlete_level and str(athlete_level).lower() in {"beginner", "novice"}:
        max_hard_sessions = 1

    for week_index in range(weeks):
        week_start = first_week + timedelta(days=week_index * 7)
        weeks_to_goal = ((last_week - week_start).days // 7)
        phase = _phase(weeks_to_goal)
        deload = weeks_to_goal > 0 and weeks_to_goal % 4 == 0 and week_index != 2
        target = previous_target * 0.8 if deload and previous_target else baseline_tss * ((1 + progression / 100) ** week_index)
        if event_demand and isinstance(event_demand, dict):
            target = max(target, float(event_demand.get("weekly_tss", target)))
        available_days = get_available_days(availability)
        longest_available_hours = max(
            (_hours(availability.get(day, {})) for day in available_days),
            default=0.0,
        )
        long_ride_hours = (
            float(event_demand.get("long_ride_hours"))
            if isinstance(event_demand, dict) and event_demand.get("long_ride_hours")
            else longest_available_hours if longest_available_hours >= 3 else None
        )
        training_day_limit = min(
            len(available_days),
            max(1, len(available_days) - int(recovery.get("rest_days", 1))),
        )
        rest_days = min(
            max(1, int(recovery.get("rest_days", 1))),
            max(0, len(available_days) - 1),
        )
        ensure_vo2 = week_index >= 1 and not vo2_history[-1]
        week_planning_target = max(
            0.0,
            target - float(completed_tss or 0)
            if week_index == 0
            else target,
        )
        categories = _category_counts(
            training_day_limit,
            goal,
            phase,
            max_hard_sessions=max_hard_sessions,
            ensure_vo2=ensure_vo2,
            rotation_state=category_rotation_state,
        )
        training_capacity_hours = sum(
            sorted(
                (_hours(availability.get(day, {})) for day in available_days),
                reverse=True,
            )[:training_day_limit]
        )
        available_minutes = training_capacity_hours * 60
        weekly_cap = _achievable_week_tss(
            available_days,
            availability,
            workouts,
            training_hours=training_capacity_hours,
            recovery=recovery,
        )
        if weekly_cap > 0:
            week_planning_target = min(float(week_planning_target), float(weekly_cap))
        long_ride_hours = _supported_long_ride_hours(
            long_ride_hours,
            week_planning_target,
            phase,
            recovery,
        )
        budget = _intensity_budget(phase, week_planning_target, available_minutes)
        budget["_planned_minutes"] = available_minutes
        budget["max_realistic_tss"] = weekly_cap
        budget["phase"] = phase
        budget["phase"] = phase
        if budget["hard_tss"] >= max(20.0, week_planning_target * 0.05):
            if not any(category in HARD_TYPES for category in categories):
                replacement = next(
                    (category for category in ("Endurance", "Tempo") if category in categories),
                    None,
                )
                if replacement:
                    categories[categories.index(replacement)] = "Threshold"
        original_zone_budget = dict((budget.get("zone_minutes") or {}))
        if week_index == 0 and completed_zone_minutes:
            remaining_zone_budget = _remaining_zone_budget(original_zone_budget, completed_zone_minutes)
            budget["zone_minutes"] = remaining_zone_budget
            high_intensity_done = (
                float(completed_zone_minutes.get("Zone 3", 0) or 0) >= float(original_zone_budget.get("Zone 3", 0) or 0)
                and float(completed_zone_minutes.get("Zone 4", 0) or 0)
                + float(completed_zone_minutes.get("Zone 5+", 0) or 0)
                >= float(original_zone_budget.get("Zone 4", 0) or 0)
                + float(original_zone_budget.get("Zone 5+", 0) or 0)
            )
            if high_intensity_done:
                categories = ["Endurance"]

        if deload and previous_workouts:
            weekly = [dict(item) for item in previous_workouts]
            for item in weekly:
                item["target_tss"] = round(item["target_tss"] * 0.8)
        else:
            weekly = _select_week(
                available_days,
                availability,
                categories,
                week_planning_target,
                workouts,
                rest_days=rest_days,
                max_hard_sessions=max_hard_sessions,
                max_consecutive_days=max(1, int(recovery.get("max_consecutive_training_days", 5) or 5)),
                used_files=used_files,
                long_ride_hours=long_ride_hours,
                intensity_budget=budget,
                ensure_vo2=ensure_vo2,
            )
            for item in weekly:
                item["intensity_budget"] = budget
                item["max_hard_sessions"] = max_hard_sessions
                item["phase"] = phase
                if item.get("workout"):
                    item["workout_facts"] = classify_workout(item["workout"])
            previous_workouts = weekly
            used_files.update(
                item["workout"].get("_file")
                for item in weekly
                if item.get("workout")
            )
        previous_target = target
        vo2_history.append(any(item.get("category") == "VO2max" for item in weekly))
        by_day = {item["day"]: item for item in weekly}

        for offset in range(7):
            current = week_start + timedelta(days=offset)
            if current < first_day or current > goal_day:
                continue
            day_name = current.strftime("%A")
            item = dict(by_day.get(day_name, {
                "day": day_name,
                "category": None,
                "target_tss": 0,
                "workout": None,
                "rest": True,
            }))
            item.update({
                "date": current.isoformat(),
                "week_number": week_index + 1,
                "week_target_tss": round(target),
                "phase": phase,
                "deload": deload,
            })
            plan.append(item)

    return plan


def generate_plan(*args, **kwargs):
    """Backward-compatible alias for stable full-horizon plan generation."""
    return generate_long_term_plan(*args, **kwargs)
