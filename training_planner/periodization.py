"""Independent periodized training-plan generator for Cycling Analytics."""

from datetime import date, datetime, timedelta
from itertools import combinations

import pandas as pd

from .availability import get_available_days
from .distribution import calculate_distribution
from .recovery import calculate_recovery_profile

from helpers.metrics import TRAINING_ZONES, get_training_zone


DAY_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

WEEKEND_FIRST_ORDER = [
    "Saturday",
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
]

HARD_TYPES = {"Threshold", "VO2max"}

# ---------------------------------------------------------------------
# ZONES
# ---------------------------------------------------------------------
# TRAINING_ZONES from helpers.metrics is the single source of truth.
#
# Example:
# TRAINING_ZONES = {
#     "Recovery": (0.00, 0.55),
#     "Endurance": (0.55, 0.76),
#     "Tempo": (0.76, 0.91),
#     "Threshold": (0.91, 1.06),
#     "VO2max": (1.06, 1.21),
#     "Anaerobic": (1.21, float("inf")),
# }
#
# Do NOT define zone boundaries or representative IF values here.

ZONE_KEYS = tuple(TRAINING_ZONES.keys())


CATEGORY_ZONE_FOCUS = {
    "Endurance": ("Endurance",),
    "Tempo": ("Tempo",),
    "Threshold": ("Threshold",),
    "VO2max": ("VO2max",),
    "Anaerobic": ("Anaerobic",),
}

def _zone_bounds(zone):
    bounds = TRAINING_ZONES[zone]
    return float(bounds["min"]), float(bounds["max"])

def _zone_representative_if(zone):
    """
    Determine a representative intensity factor for a zone using only
    TRAINING_ZONES from helpers.metrics.

    Finite zone:
        midpoint between lower and upper boundary.

    Open-ended zone:
        use the lower boundary.

    This means there are no duplicated IF values in this planner.
    """
    lower, upper = _zone_bounds(zone)

    if lower is None:
        return 0.0

    if upper is None:
        return lower

    if upper == float("inf"):
        return lower

    return (lower + upper) / 2.0


def _category_if(category):
    """
    Return the representative IF for a training category.

    Categories are mapped to zones through CATEGORY_ZONE_FOCUS,
    which ultimately uses TRAINING_ZONES from metrics.py.
    """
    focus_zones = CATEGORY_ZONE_FOCUS.get(category, (category,))

    values = [
        _zone_representative_if(zone)
        for zone in focus_zones
        if zone in TRAINING_ZONES
    ]

    if not values:
        return 0.0

    return sum(values) / len(values)


# ---------------------------------------------------------------------
# DATE / AVAILABILITY HELPERS
# ---------------------------------------------------------------------

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

    return max(
        0.0,
        float(day_data.get("hours", 0) or 0),
    )


def _workout_hours(workout):
    if not workout:
        return 0.0

    return float(workout.get("duration_minutes", 0) or 0) / 60.0


def _day_priority(day, availability):
    return (
        -_hours(availability.get(day, {})),
        WEEKEND_FIRST_ORDER.index(day),
    )


# ---------------------------------------------------------------------
# ZONE / WORKOUT ANALYSIS
# ---------------------------------------------------------------------

def _workout_zone_minutes(workout):
    """
    Calculate minutes spent in each training zone.

    Zone classification comes directly from get_training_zone()
    in helpers.metrics.
    """
    stored = (workout or {}).get("zone_minutes")

    if isinstance(stored, dict):
        return {
            zone: float(stored.get(zone, 0) or 0)
            for zone in ZONE_KEYS
        }

    zones = {
        zone: 0.0
        for zone in ZONE_KEYS
    }

    for step in (workout or {}).get("steps", []):
        intensity = (
            float(step.get("intensity", 0) or 0)
            / 100.0
        )

        minutes = (float(step.get("duration_seconds", 0) or 0) * float(step.get("repeat", 1) or 1) / 60.0)

        # IMPORTANT:
        # get_training_zone() from metrics.py is the source of truth.
        zone = get_training_zone(intensity)

        if zone not in zones:
            zones[zone] = 0.0

        zones[zone] += minutes

    return zones


def _workout_tss(workout):
    total_tss = 0.0

    for step in (workout or {}).get("steps", []):
        duration_minutes = (float(step.get("duration_seconds", 0) or 0) * float(step.get("repeat", 1) or 1) / 60.0)

        intensity = (
            float(step.get("intensity", 0) or 0)
            / 100.0
        )

        total_tss += (
            duration_minutes
            * (intensity ** 2)
            * 100.0
            / 60.0
        )

    return total_tss


def classify_workout(workout):
    duration = _workout_hours(workout)

    tss = float(
        (workout or {}).get(
            "target_tss",
            (workout or {}).get(
                "estimated_tss",
                _workout_tss(workout),
            ),
        )
        or 0
    )

    total_seconds = sum(float(step.get("duration_seconds", 0) or 0) * float(step.get("repeat", 1) or 1) for step in (workout or {}).get("steps", [])
    )

    intensity = (
        sum(
            float(step.get("intensity", 0) or 0)
            * float(step.get("duration_seconds", 0) or 0) * float(step.get("repeat", 1) or 1)
            for step in (workout or {}).get("steps", [])
        )
        / max(1, total_seconds)
    )

    peak_intensity = max(
        (
            float(step.get("intensity", 0) or 0)
            for step in (workout or {}).get("steps", [])
        ),
        default=0,
    )

    category = (workout or {}).get("_category", "")

    hard = (
        category in HARD_TYPES
        or intensity >= 88
        or tss / max(duration, 0.25) >= 85
    )

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

    ceilings = {
        "VO2max": 1.25,
        "Threshold": 1.5,
        "Tempo": 2.5,
        "Anaerobic": 1.25,
    }

    if (
        category in ceilings
        and facts["duration_hours"] > ceilings[category]
    ):
        return False

    if (
        category == "Endurance"
        and facts["intensity"] >= 82
    ):
        return False

    if (
        category == "VO2max"
        and facts["peak_intensity"] < 100
    ):
        return False

    return True


# ---------------------------------------------------------------------
# PERIODIZATION
# ---------------------------------------------------------------------

def _phase(weeks_to_goal):
    if weeks_to_goal <= 1:
        return "taper"

    if weeks_to_goal <= 3:
        return "peak"

    if weeks_to_goal <= 8:
        return "build"

    return "base"


def calculate_event_demand(
    event_distance_km,
    climb_m=0,
    event_type="endurance",
    target_ftp=None,
):
    distance = max(
        0.0,
        float(event_distance_km or 0),
    )

    climb = max(
        0.0,
        float(climb_m or 0),
    )

    difficulty = (
        1.0
        + min(0.35, distance / 500)
        + min(0.25, climb / 10000)
    )

    if target_ftp:
        difficulty *= max(
            0.8,
            min(1.2, 250 / float(target_ftp)),
        )

    return {
        "weekly_tss": round(
            max(
                200.0,
                min(
                    900.0,
                    350.0 * difficulty,
                ),
            )
        ),
        "long_ride_hours": round(
            max(
                2.0,
                min(
                    8.0,
                    distance / 30.0,
                ),
            ),
            1,
        ),
        "event_type": str(
            event_type or "endurance"
        ),
    }


def _phase_distribution(goal, phase):
    phase_mix = {
        "base": {
            "Endurance": 0.60,
            "Tempo": 0.25,
            "Threshold": 0.10,
            "VO2max": 0.05,
        },
        "build": {
            "Endurance": 0.45,
            "Tempo": 0.20,
            "Threshold": 0.25,
            "VO2max": 0.10,
        },
        "peak": {
            "Endurance": 0.35,
            "Tempo": 0.15,
            "Threshold": 0.30,
            "VO2max": 0.20,
        },
        "taper": {
            "Endurance": 0.55,
            "Tempo": 0.25,
            "Threshold": 0.15,
            "VO2max": 0.05,
        },
    }[phase]

    goal_mix = calculate_distribution(goal)

    return {
        category: (
            goal_mix.get(category, 0.0) * 0.4
            + phase_mix[category] * 0.6
        )
        for category in phase_mix
    }


# ---------------------------------------------------------------------
# TSS / ZONE BUDGET
# ---------------------------------------------------------------------

def _tss_per_minute(if_value):
    return (
        float(if_value) ** 2
        * 100.0
        / 60.0
    )


def _calculate_zone_budget(
    week_target_tss,
    goal,
    phase,
):
    distribution = _phase_distribution(
        goal,
        phase,
    )

    tss_budget = {}
    minute_budget = {}

    for category, percentage in distribution.items():
        category_tss = (
            float(week_target_tss)
            * float(percentage)
        )

        # Derived directly from TRAINING_ZONES.
        category_if = _category_if(category)

        tss_per_minute = _tss_per_minute(
            category_if
        )

        minutes = (
            category_tss / tss_per_minute
            if tss_per_minute > 0
            else 0.0
        )

        tss_budget[category] = category_tss
        minute_budget[category] = minutes

    return {
        "distribution": distribution,
        "tss": tss_budget,
        "minutes": minute_budget,
    }


def _zone_minute_budget_to_zone_dict(
    week_target_tss,
    goal,
    phase,
):
    category_budget = _calculate_zone_budget(
        week_target_tss,
        goal,
        phase,
    )

    zone_budget = {
        zone: 0.0
        for zone in ZONE_KEYS
    }

    for category, minutes in category_budget["minutes"].items():
        for zone in CATEGORY_ZONE_FOCUS.get(
            category,
            (category,),
        ):
            if zone in zone_budget:
                zone_budget[zone] += float(minutes)

    return zone_budget


def _remaining_zone_budget(
    zone_budget,
    completed_zone_minutes,
):
    return {
        zone: max(
            0.0,
            float(
                zone_budget.get(zone, 0)
                or 0
            )
            - float(
                (completed_zone_minutes or {}).get(
                    zone,
                    0,
                )
                or 0
            ),
        )
        for zone in ZONE_KEYS
    }


# ---------------------------------------------------------------------
# RECOVERY / TRAINING CAPACITY
# ---------------------------------------------------------------------

def _sustainable_tss_rate(recovery):
    historical_hours = float(
        (recovery or {}).get(
            "avg_hours_per_week",
            0,
        )
        or 0
    )

    historical_tss = float(
        (recovery or {}).get(
            "avg_stress_per_week",
            0,
        )
        or 0
    )

    historical_rate = (
        historical_tss / historical_hours
        if historical_hours > 0
        else 55.0
    )

    return max(
        35.0,
        min(
            75.0,
            historical_rate * 1.1,
        ),
    )


def _implied_minutes(
    target_tss,
    recovery,
):
    rate = _sustainable_tss_rate(
        recovery
    )

    return (
        float(target_tss or 0)
        / rate
        * 60
        if rate > 0
        else 0.0
    )


def _achievable_week_tss(
    available_days,
    availability,
    workouts,
    training_hours=None,
    recovery=None,
):
    if training_hours is None:
        training_hours = sum(
            _hours(availability.get(day, {}))
            for day in available_days
        )

    if training_hours <= 0:
        return 0.0

    max_workout_tss = max(
        (
            float(
                workout.get(
                    "target_tss",
                    workout.get(
                        "estimated_tss",
                        _workout_tss(workout),
                    ),
                )
                or 0
            )
            for workout in workouts
        ),
        default=0.0,
    )

    if max_workout_tss <= 0:
        return 0.0

    sustainable_rate = _sustainable_tss_rate(
        recovery
    )

    return float(
        min(
            training_hours * sustainable_rate,
            len(available_days) * max_workout_tss,
            900.0,
        )
    )


def _supported_long_ride_hours(
    requested_hours,
    target_tss,
    phase,
    recovery,
):
    if not requested_hours or target_tss <= 0:
        return None

    phase_share = {
        "base": 0.45,
        "build": 0.50,
        "peak": 0.55,
        "taper": 0.35,
    }[phase]

    supported_hours = (
        float(target_tss)
        * phase_share
        / 70.0
    )

    if supported_hours < 2.5:
        return None

    history_hours = float(
        recovery.get(
            "avg_hours_per_week",
            0,
        )
        or 0
    )

    if history_hours > 0:
        supported_hours = min(
            supported_hours,
            history_hours * 0.75,
        )

    if int(
        recovery.get(
            "rest_days",
            1,
        )
        or 1
    ) >= 4:
        supported_hours = min(
            supported_hours,
            4.0,
        )

    return round(
        min(
            float(requested_hours),
            supported_hours,
        ),
        1,
    )


# ---------------------------------------------------------------------
# SESSION SELECTION
# ---------------------------------------------------------------------

def _select_categories(
    sessions_per_week,
    goal,
    phase,
    max_hard_sessions=2,
    week_index=0,
):
    sessions_per_week = max(2,min(6,int(sessions_per_week or 3)))

    if sessions_per_week <= 3:
        second_quality = ("Tempo" if week_index % 2 == 0 else "Threshold")

        return (["VO2max", second_quality] + (["Endurance"] if sessions_per_week == 3 else []))

    if sessions_per_week == 4:
        return (["VO2max", "Tempo", "Threshold","Endurance"])

    if sessions_per_week == 5:
        return (["VO2max", "Tempo", "Threshold", "Endurance", "Endurance"])

    if sessions_per_week == 6:
        return (["VO2max", "Threshold", "Tempo", "Endurance", "Endurance", "Endurance"])

    distribution = _phase_distribution(
        goal,
        phase,
    )

    quality = ("Threshold" if (max_hard_sessions >= 2 and distribution["Threshold"] >= distribution["Tempo"]) else "Tempo")

    return (["VO2max", quality] + ["Endurance"] * (sessions_per_week - 2))


def _day_spacing_penalty(
    subset,
    ordered_days,
):
    chosen = set(subset)

    penalty = 0
    train_streak = 0
    rest_streak = 0

    for day in ordered_days:
        if day in chosen:
            train_streak += 1
            rest_streak = 0

            penalty += max(
                0,
                train_streak - 1,
            ) ** 2

        else:
            rest_streak += 1
            train_streak = 0

            penalty += max(
                0,
                rest_streak - 1,
            ) ** 2

    return penalty


def _select_training_days(
    ordered_days,
    availability,
    session_count,
):
    session_count = min(
        session_count,
        len(ordered_days),
    )

    if session_count >= len(ordered_days):
        return list(ordered_days)

    best_subset = None
    best_score = None

    for subset in combinations(
        ordered_days,
        session_count,
    ):
        penalty = _day_spacing_penalty(
            subset,
            ordered_days,
        )

        hours = sum(
            _hours(availability.get(day, {}))
            for day in subset
        )

        score = (
            penalty,
            -hours,
        )

        if (
            best_score is None
            or score < best_score
        ):
            best_score = score
            best_subset = subset

    return list(best_subset)


def _assign_categories_to_days(
    available_days,
    availability,
    categories,
    max_hard_sessions=2,
):
    categories = list(categories)

    ordered_days = [
        day
        for day in DAY_ORDER
        if day in available_days
    ]

    training_days = _select_training_days(
        ordered_days,
        availability,
        len(categories),
    )

    assignment = {}

    if "Endurance" in categories and training_days:
        primary_day = min(
            training_days,
            key=lambda day: _day_priority(
                day,
                availability,
            ),
        )

        assignment[primary_day] = "Endurance"
        categories.remove("Endurance")

    remaining_days = [
        day
        for day in training_days
        if day not in assignment
    ]

    hard = [
        category
        for category in categories
        if category in HARD_TYPES
    ]

    soft = [
        category
        for category in categories
        if category not in HARD_TYPES
    ]

    hard_days = [
        remaining_days[index]
        for index in _spread_indices(
            len(remaining_days),
            len(hard),
        )
    ]

    for day, category in zip(
        hard_days,
        hard,
    ):
        assignment[day] = category

    placed_hard = sorted(
        (
            day
            for day, category
            in assignment.items()
            if category in HARD_TYPES
        ),
        key=ordered_days.index,
    )

    for first, second in zip(
        placed_hard,
        placed_hard[1:],
    ):
        if (
            ordered_days.index(second)
            - ordered_days.index(first)
            != 1
        ):
            continue

        for candidate in remaining_days:
            if (
                candidate in (first, second)
                or assignment.get(candidate)
                in HARD_TYPES
            ):
                continue

            if (
                abs(
                    ordered_days.index(candidate)
                    - ordered_days.index(first)
                )
                > 1
            ):
                assignment[candidate], assignment[second] = (
                    assignment.get(second),
                    assignment.get(candidate),
                )
                break

    leftover_days = sorted(
        (
            day
            for day in remaining_days
            if day not in assignment
        ),
        key=lambda day: _day_priority(
            day,
            availability,
        ),
    )

    for day, category in zip(
        leftover_days,
        soft,
    ):
        assignment[day] = category

    return assignment


def _spread_indices(
    count,
    n,
):
    if n <= 0 or count <= 0:
        return []

    if n >= count:
        return list(range(count))

    indices = []

    for position in range(n):
        index = round(
            (position + 0.5)
            * count
            / n
            - 0.5
        )

        index = max(
            0,
            min(
                count - 1,
                index,
            ),
        )

        while (
            index in indices
            and index < count - 1
        ):
            index += 1

        indices.append(index)

    return sorted(set(indices))


# ---------------------------------------------------------------------
# WORKOUT MATCHING
# ---------------------------------------------------------------------

def _workout_zone_difference(
    workout,
    target_zone,
    target_minutes,
):
    zone_minutes = _workout_zone_minutes(
        workout
    )

    actual_minutes = float(
        zone_minutes.get(
            target_zone,
            0.0,
        )
    )

    return abs(
        actual_minutes
        - float(target_minutes)
    )


def _select_best_workout(
    options,
    category,
    target_minutes,
):
    if not options:
        return None

    focus_zones = CATEGORY_ZONE_FOCUS.get(
        category,
        (category,),
    )

    if len(focus_zones) == 1:
        target_zone = focus_zones[0]

        return min(
            options,
            key=lambda workout:
            _workout_zone_difference(
                workout,
                target_zone,
                target_minutes,
            ),
        )

    return min(
        options,
        key=lambda workout:
        abs(
            sum(
                _workout_zone_minutes(
                    workout
                ).get(
                    zone,
                    0.0,
                )
                for zone in focus_zones
            )
            - float(target_minutes)
        ),
    )


# ---------------------------------------------------------------------
# WEEK SELECTION
# ---------------------------------------------------------------------

def _select_week(
    available_days,
    availability,
    categories,
    category_tss_budget,
    category_minutes_budget,
    workouts,
    max_hard_sessions=2,
    used_files=None,
    long_ride_hours=None,
    week_target_tss=0.0,
):
    ordered_days = [
        day
        for day in DAY_ORDER
        if day in available_days
    ]

    assignment = _assign_categories_to_days(
        ordered_days,
        availability,
        categories,
        max_hard_sessions=max_hard_sessions,
    )

    used_files = used_files or set()

    category_days = {}

    for day, category in assignment.items():
        category_days.setdefault(
            category,
            [],
        ).append(day)

    endurance_days = category_days.get(
        "Endurance",
        [],
    )

    primary_long_day = (
        min(
            endurance_days,
            key=lambda day: _day_priority(
                day,
                availability,
            ),
        )
        if endurance_days
        else None
    )

    category_session_targets = {}

    for category, days_for_category in category_days.items():
        total_minutes = float(
            category_minutes_budget.get(
                category,
                0,
            )
            or 0
        )

        total_hours = (
            sum(
                _hours(
                    availability.get(
                        day,
                        {},
                    )
                )
                for day in days_for_category
            )
            or 1.0
        )

        for day in days_for_category:
            day_hours = _hours(
                availability.get(
                    day,
                    {},
                )
            )

            share = (
                day_hours
                / total_hours
            )

            category_session_targets[day] = (
                total_minutes * share
            )

    schedule = []

    for day in ordered_days:
        category = assignment.get(day)

        if category is None:
            schedule.append({
                "day": day,
                "category": None,
                "target_tss": 0,
                "workout": None,
                "rest": True,
            })
            continue

        day_hours = _hours(
            availability.get(
                day,
                {},
            )
        )

        target_minutes = category_session_targets.get(
            day,
            0.0,
        )

        options = [
            workout
            for workout in workouts
            if (
                workout.get("_category")
                == category
                and workout_is_safe(
                    category,
                    workout,
                    day_hours,
                )
                and workout.get("_file")
                not in used_files
            )
        ]

        if not options:
            options = [
                workout
                for workout in workouts
                if (
                    workout.get("_category")
                    == category
                    and workout_is_safe(
                        category,
                        workout,
                        day_hours,
                    )
                )
            ]

        workout = None

        if (
            category == "Endurance"
            and day == primary_long_day
        ):
            # Maximum sensible duration for the long ride
            requested_hours = min(
                day_hours,
                long_ride_hours or day_hours,
            )

            # Remaining Endurance/Z2 requirement
            target_zone_minutes = float(target_minutes)

            # Only consider workouts that fit within the available
            # time on the day.
            long_options = [
                item
                for item in options
                if _workout_hours(item) <= requested_hours
            ]

            if long_options:
                def long_ride_score(item):
                    zone_minutes = _workout_zone_minutes(item)

                    endurance_minutes = zone_minutes.get(
                        "Endurance",
                        0.0,
                    )

                    duration_hours = _workout_hours(item)

                    # How well does this workout fill the remaining
                    # Endurance/Z2 requirement?
                    zone_error = abs(
                        endurance_minutes
                        - target_zone_minutes
                    )

                    # How well does it use the available long-ride time?
                    duration_error = abs(
                        duration_hours
                        - requested_hours
                    )

                    # Zone fulfilment is more important than duration.
                    return (
                        zone_error * 2.0
                        + duration_error
                    )

                workout = min(
                    long_options,
                    key=long_ride_score,
                )

            else:
                workout = None

        else:
            workout = _select_best_workout(options,category,target_minutes)

        if workout is not None:
            used_files.add(
                workout.get("_file")
            )

        actual_tss = float(
            (workout or {}).get(
                "target_tss",
                (workout or {}).get(
                    "estimated_tss",
                    _workout_tss(workout),
                ),
            )
            or 0
        )

        schedule.append({
            "day": day,
            "category": category,
            "target_tss": round(actual_tss),
            "workout": workout,
            "rest": False,
        })

    training_days = [
        item["day"]
        for item in schedule
        if item["category"]
    ]

    rest_days = [
        item["day"]
        for item in schedule
        if not item["category"]
    ]

    planned_tss = sum(
        float(
            item.get(
                "target_tss",
                0,
            )
            or 0
        )
        for item in schedule
    )

    planned_zone_minutes = {
        zone: 0.0
        for zone in ZONE_KEYS
    }

    for item in schedule:
        for zone, minutes in _workout_zone_minutes(
            item.get("workout")
        ).items():
            planned_zone_minutes[zone] += minutes


    # print(
    #     "PLAN_DEBUG",
    #     {
    #         "sessions_per_week": len(categories),
    #         "categories": categories,
    #         "week_target_tss": round(
    #             float(week_target_tss),
    #             1,
    #         ),
    #         "category_tss_targets": {
    #             category: round(
    #                 float(value),
    #                 1,
    #             )
    #             for category, value
    #             in category_tss_budget.items()
    #         },
    #         "category_minute_targets": {
    #             category: round(
    #                 float(value),
    #                 1,
    #             )
    #             for category, value
    #             in category_minutes_budget.items()
    #         },
    #         "representative_zone_if": {
    #             category: round(
    #                 _category_if(category),
    #                 3,
    #             )
    #             for category
    #             in category_minutes_budget
    #         },
    #         "planned_zone_minutes": {
    #             zone: round(
    #                 value,
    #                 1,
    #             )
    #             for zone, value
    #             in planned_zone_minutes.items()
    #         },
    #         "planned_tss": round(
    #             planned_tss,
    #             1,
    #         ),
    #         "training_days": training_days,
    #         "rest_days": rest_days,
    #         "available_hours": {
    #             day: round(
    #                 _hours(
    #                     availability.get(
    #                         day,
    #                         {},
    #                     )
    #                 ),
    #                 1,
    #             )
    #             for day in ordered_days
    #         },
    #         "planned_hours": {
    #             item["day"]: round(
    #                 _workout_hours(
    #                     item.get("workout")
    #                 ),
    #                 2,
    #             )
    #             for item in schedule
    #         },
    #     },
    # )

    return schedule


# ---------------------------------------------------------------------
# REFORECAST
# ---------------------------------------------------------------------

def reforecast_plan(
    plan,
    completed_activities,
    current_date=None,
):
    if not isinstance(plan, list):
        return []

    activities = (
        completed_activities.copy()
        if isinstance(
            completed_activities,
            pd.DataFrame,
        )
        else pd.DataFrame(
            completed_activities or []
        )
    )

    if (
        activities.empty
        or "date" not in activities
    ):
        return plan

    activities["date"] = pd.to_datetime(
        activities["date"],
        errors="coerce",
    )

    activities["stress"] = pd.to_numeric(
        activities["stress"]
        if "stress" in activities
        else 0,
        errors="coerce",
    )

    if not isinstance(
        activities["stress"],
        pd.Series,
    ):
        activities["stress"] = pd.Series(
            0.0,
            index=activities.index,
        )

    activities["stress"] = (
        activities["stress"]
        .fillna(0)
    )

    cutoff = pd.Timestamp(
        current_date or date.today()
    )

    completed = activities[
        activities["date"] < cutoff
    ]

    if completed.empty:
        return plan

    actual_by_week = (
        completed.groupby(
            completed["date"].dt.to_period(
                "W-MON"
            )
        )["stress"]
        .sum()
    )

    updated = [
        dict(item)
        for item in plan
    ]

    for item in updated:
        if (
            pd.Timestamp(item["date"])
            < cutoff
        ):
            continue

        week = pd.Timestamp(
            item["date"]
        ).to_period("W-MON")

        actual = float(
            actual_by_week.get(
                week,
                0,
            )
        )

        planned = float(
            item.get(
                "week_target_tss",
                0,
            )
            or 0
        )

        if planned and actual:
            adjustment = max(
                0.85,
                min(
                    1.1,
                    actual / planned,
                ),
            )

            item["week_target_tss"] = round(
                planned * adjustment
            )

            item["reforecast_factor"] = round(
                adjustment,
                2,
            )

    return updated


# ---------------------------------------------------------------------
# ATHLETE STATE
# ---------------------------------------------------------------------

def calculate_athlete_state(
    activities,
    plan=None,
    current_date=None,
    ftp=0,
):
    frame = (
        activities.copy()
        if isinstance(
            activities,
            pd.DataFrame,
        )
        else pd.DataFrame(
            activities or []
        )
    )

    cutoff = pd.Timestamp(
        current_date or date.today()
    ).normalize()

    recovery = calculate_recovery_profile(
        frame,
        athlete_level=None,
    )

    state = {
        "ctl": recovery.get("ctl"),
        "atl": recovery.get("atl"),
        "tsb": recovery.get("tsb"),
        "recent_tss": 0.0,
        "recent_volume_hours": 0.0,
        "zones": {},
        "hard_sessions": recovery.get(
            "avg_hard_sessions",
            0.0,
        ),
        "recovery": recovery,
        "adherence": None,
    }

    if (
        not frame.empty
        and "date" in frame
    ):
        frame["date"] = pd.to_datetime(
            frame["date"],
            errors="coerce",
        )

        recent = frame[
            frame["date"]
            >= cutoff - pd.Timedelta(days=27)
        ]

        if "stress" in recent:
            state["recent_tss"] = float(
                pd.to_numeric(
                    recent["stress"],
                    errors="coerce",
                )
                .fillna(0)
                .sum()
            )

        for column in (
            "moving_time",
            "elapsed_time",
            "duration_seconds",
        ):
            if column in recent:
                state[
                    "recent_volume_hours"
                ] = float(
                    pd.to_numeric(
                        recent[column],
                        errors="coerce",
                    )
                    .fillna(0)
                    .sum()
                ) / 3600

                break

        state["hard_sessions"] = int(
            (
                pd.to_numeric(
                    recent["stress"],
                    errors="coerce",
                )
                .fillna(0)
                >= 75
            ).sum()
        ) if "stress" in recent else int(
            recent.shape[0]
        )

        for column in (
            "time_z1_hr",
            "time_z2_hr",
            "time_z3_hr",
            "time_z4_hr",
        ):
            if column in recent:
                state["zones"][column] = float(
                    pd.to_numeric(
                        recent[column],
                        errors="coerce",
                    )
                    .fillna(0)
                    .sum()
                ) / 60

        if (
            ftp
            and ftp > 0
            and "moving_time" in recent
        ):
            power = recent.get(
                "weighted_average_watts",
                recent.get(
                    "average_watts"
                ),
            )

            if power is not None:
                for _, activity in recent.iterrows():
                    value = (
                        power.loc[activity.name]
                        if activity.name
                        in power.index
                        else None
                    )

                    if pd.isna(value):
                        continue

                    intensity = (
                        float(value)
                        / float(ftp)
                    )

                    # Again, classification comes
                    # directly from metrics.py.
                    zone = get_training_zone(
                        intensity
                    )

                    state["zones"][zone] = (
                        state["zones"].get(
                            zone,
                            0.0,
                        )
                        + float(
                            activity.get(
                                "moving_time",
                                0,
                            )
                            or 0
                        )
                        / 3600
                    )

    if plan:
        scheduled = {
            item.get("date")
            for item in plan
            if (
                item.get("date")
                and item.get("workout")
                and pd.Timestamp(
                    item["date"]
                ) < cutoff
            )
        }

        completed = set()

        if (
            not frame.empty
            and "date" in frame
        ):
            completed = {
                value.date().isoformat()
                for value in frame["date"].dropna()
                if value < cutoff
            }

        if scheduled:
            state["adherence"] = round(
                len(
                    scheduled & completed
                )
                / len(scheduled),
                3,
            )

    return state


# ---------------------------------------------------------------------
# PUBLIC PLAN API
# ---------------------------------------------------------------------

def generate_long_term_plan(
    *args,
    **kwargs,
):
    return _generate_plan(
        *args,
        **kwargs,
    )


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
    sessions_per_week=None,
):
    if not isinstance(plan, list):
        return generate_long_term_plan(
            goal,
            goal_date,
            availability,
            workouts,
            baseline_tss,
            progression,
            current_date,
            activities,
            athlete_level,
            event_demand,
            completed_zone_minutes,
            completed_tss,
        )

    cutoff = (
        _parse_date(current_date)
        or date.today()
    )

    next_monday = (
        cutoff
        + timedelta(
            days=(
                7 - cutoff.weekday()
            ) % 7
            or 7
        )
    )

    horizon = (
        next_monday
        + timedelta(
            days=max(
                7,
                min(
                    14,
                    int(horizon_days),
                ),
            )
            - 1
        )
    )

    future_rows = [
        item
        for item in plan
        if (
            item.get("date")
            and next_monday
            <= _parse_date(item["date"])
            <= horizon
        )
    ]

    if not future_rows:
        return plan

    baseline = max(
        (
            float(
                item.get(
                    "week_target_tss",
                    0,
                )
                or 0
            )
            for item in future_rows
        ),
        default=float(
            baseline_tss or 0
        ),
    )

    adaptive = generate_long_term_plan(
        goal=goal,
        goal_date=horizon,
        availability=availability,
        workouts=workouts,
        baseline_tss=baseline,
        progression=progression,
        start_date=next_monday,
        activities=activities,
        athlete_level=athlete_level,
        event_demand=event_demand,
        completed_zone_minutes=None,
        completed_tss=0.0,
        sessions_per_week=sessions_per_week,
    )

    replacement = {
        item["date"]: item
        for item in adaptive
        if (
            item.get("date")
            and next_monday
            <= _parse_date(item["date"])
            <= horizon
        )
    }

    return [
        replacement.get(
            item.get("date"),
            item,
        )
        if (
            item.get("date")
            and next_monday
            <= _parse_date(item["date"])
            <= horizon
        )
        else item
        for item in plan
    ]


# ---------------------------------------------------------------------
# PLAN GENERATOR
# ---------------------------------------------------------------------

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
    sessions_per_week=None,
):
    first_day = start_date or date.today()

    goal_day = _parse_date(
        goal_date
    )

    if (
        goal_day is None
        or goal_day < first_day
    ):
        return []

    first_week = (
        first_day
        - timedelta(
            days=first_day.weekday()
        )
    )

    last_week = (
        goal_day
        - timedelta(
            days=goal_day.weekday()
        )
    )

    weeks = (
        (last_week - first_week).days
        // 7
    ) + 1

    plan = []

    previous_workouts = None
    previous_target = None

    used_files = set()

    recovery = calculate_recovery_profile(
        activities,
        athlete_level=athlete_level,
    )

    max_hard_sessions = 2

    if (
        recovery["avg_hard_sessions"] > 2.5
        or (
            recovery["tsb"] is not None
            and recovery["tsb"] < -10
        )
    ):
        max_hard_sessions = 1

    if (
        athlete_level
        and str(athlete_level).lower()
        in {
            "beginner",
            "novice",
        }
    ):
        max_hard_sessions = 1

    for week_index in range(weeks):
        week_start = (
            first_week
            + timedelta(
                days=week_index * 7
            )
        )

        weeks_to_goal = (
            last_week - week_start
        ).days // 7

        phase = _phase(
            weeks_to_goal
        )

        deload = (
            weeks_to_goal > 0
            and weeks_to_goal % 4 == 0
            and week_index != 2
        )

        if (
            phase == "taper"
            and previous_target
        ):
            target = (
                previous_target * 0.55
            )

        else:
            target = (
                previous_target * 0.8
                if (
                    deload
                    and previous_target
                )
                else baseline_tss
                * (
                    (1 + progression / 100)
                    ** week_index
                )
            )

            if (
                event_demand
                and isinstance(
                    event_demand,
                    dict,
                )
            ):
                target = max(
                    target,
                    float(
                        event_demand.get(
                            "weekly_tss",
                            target,
                        )
                    ),
                )

        available_days = (
            get_available_days(
                availability
            )
        )

        longest_available_hours = max(
            (
                _hours(
                    availability.get(
                        day,
                        {},
                    )
                )
                for day in available_days
            ),
            default=0.0,
        )

        long_ride_hours = (
            float(
                event_demand.get(
                    "long_ride_hours"
                )
            )
            if (
                isinstance(
                    event_demand,
                    dict,
                )
                and event_demand.get(
                    "long_ride_hours"
                )
            )
            else (
                longest_available_hours
                if longest_available_hours >= 3
                else None
            )
        )

        default_sessions = max(
            1,
            len(available_days)
            - int(
                recovery.get(
                    "rest_days",
                    1,
                )
            ),
        )

        week_sessions = max(2, min( 6,
                int(
                    sessions_per_week
                    or default_sessions
                ),
            ),
        )

        week_sessions = min(
            week_sessions,
            max(
                1,
                len(available_days),
            ),
        )

        week_planning_target = max(
            0.0,
            (
                target
                - float(
                    completed_tss or 0
                )
                if week_index == 0
                else target
            ),
        )

        categories = _select_categories(
            week_sessions,
            goal,
            phase,
            max_hard_sessions=max_hard_sessions,
            week_index=week_index,
        )

        training_capacity_hours = sum(
            sorted(
                (
                    _hours(
                        availability.get(
                            day,
                            {},
                        )
                    )
                    for day in available_days
                ),
                reverse=True,
            )[:len(categories)]
        )

        weekly_cap = _achievable_week_tss(
            available_days,
            availability,
            workouts,
            training_hours=training_capacity_hours,
            recovery=recovery,
        )

        if weekly_cap > 0:
            week_planning_target = min(
                float(
                    week_planning_target
                ),
                float(weekly_cap),
            )

        long_ride_hours = (
            _supported_long_ride_hours(
                long_ride_hours,
                week_planning_target,
                phase,
                recovery,
            )
        )

        zone_budget = _calculate_zone_budget(
            week_planning_target,
            goal,
            phase,
        )

        category_tss_budget = (
            zone_budget["tss"]
        )

        category_minutes_budget = (
            zone_budget["minutes"]
        )

        budget = {
            "target_tss": round(
                week_planning_target
            ),
            "zone_minutes": (
                category_minutes_budget
            ),
            "zone_tss": (
                category_tss_budget
            ),
            "planned_minutes": sum(
                category_minutes_budget.values()
            ),
            "max_realistic_tss": (
                weekly_cap
            ),
            "phase": phase,
        }

        if (
            week_index == 0
            and completed_zone_minutes
        ):
            completed_by_category = {
                category: float(
                    completed_zone_minutes.get(
                        zone,
                        0,
                    )
                    or 0
                )
                for category, zones
                in CATEGORY_ZONE_FOCUS.items()
                for zone in zones
            }

            remaining_category_budget = {
                category: max(
                    0.0,
                    float(
                        category_minutes_budget.get(
                            category,
                            0,
                        )
                        or 0
                    )
                    - float(
                        completed_by_category.get(
                            category,
                            0,
                        )
                        or 0
                    ),
                )
                for category
                in category_minutes_budget
            }

            category_minutes_budget = (
                remaining_category_budget
            )

            budget["zone_minutes"] = (
                category_minutes_budget
            )

            high_intensity_done = (
                completed_by_category.get(
                    "Threshold",
                    0,
                )
                >= float(
                    zone_budget["minutes"].get(
                        "Threshold",
                        0,
                    )
                    or 0
                )
                and completed_by_category.get(
                    "VO2max",
                    0,
                )
                >= float(
                    zone_budget["minutes"].get(
                        "VO2max",
                        0,
                    )
                    or 0
                )
            )

            if high_intensity_done:
                categories = [
                    "Endurance"
                ]

        if (
            deload
            and previous_workouts
        ):
            weekly = [
                dict(item)
                for item in previous_workouts
            ]

            for item in weekly:
                item["target_tss"] = round(
                    float(
                        item.get(
                            "target_tss",
                            0,
                        )
                        or 0
                    )
                    * 0.8
                )

        else:
            weekly = _select_week(
                available_days,
                availability,
                categories,
                category_tss_budget,
                category_minutes_budget,
                workouts,
                max_hard_sessions=max_hard_sessions,
                used_files=used_files,
                long_ride_hours=long_ride_hours,
                week_target_tss=week_planning_target,
            )

            for item in weekly:
                item["intensity_budget"] = (
                    budget
                )

                item["max_hard_sessions"] = (
                    max_hard_sessions
                )

                item["phase"] = phase

                if item.get("workout"):
                    item["workout_facts"] = (
                        classify_workout(
                            item["workout"]
                        )
                    )

        previous_workouts = weekly
        previous_target = target

        by_day = {
            item["day"]: item
            for item in weekly
        }

        for offset in range(7):
            current = (
                week_start
                + timedelta(days=offset)
            )

            if (
                current < first_day
                or current > goal_day
            ):
                continue

            day_name = current.strftime(
                "%A"
            )

            item = dict(
                by_day.get(
                    day_name,
                    {
                        "day": day_name,
                        "category": None,
                        "target_tss": 0,
                        "workout": None,
                        "rest": True,
                    },
                )
            )

            item.update({
                "date": current.isoformat(),
                "week_number": week_index + 1,
                "week_target_tss": round(
                    target
                ),
                "phase": phase,
                "deload": deload,
            })

            plan.append(item)

    return plan


def generate_plan(*args, **kwargs):
    return generate_long_term_plan(
        *args,
        **kwargs,
    )