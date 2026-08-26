from .availability import get_available_days, get_day_weights
from .planner_rules import (
    get_training_phase,
    get_session_categories,
    normalize_distribution_for_categories,
    get_vo2max_budget,
)
from .workout_selection import select_workout

def _effective_weekly_tss(weekly_tss, progression, week_number):
    if week_number % 4 == 0:
        return float(weekly_tss) * 0.7
    return float(weekly_tss) * (1 + float(progression) / 100)

DAY_INDEX = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}


def _load_for_tss(target_tss):
    levels = {"A": 20, "B": 40, "C": 60, "D": 80, "E": 100}
    return min(levels, key=lambda level: abs(levels[level] - float(target_tss or 0)))


def _day_hours(availability, day):
    day_data = availability.get(day, {}) if isinstance(availability, dict) else {}
    if not isinstance(day_data, dict):
        return 0.0
    return float(day_data.get("hours", 0) or 0)


def _workout_hours(workout):
    steps = workout.get("steps", []) if isinstance(workout, dict) else []
    if not steps:
        return 0.0
    seconds = sum(float(step.get("duration_seconds", 0) or 0) for step in steps)
    return seconds / 3600.0

def _build_workout_days_with_vo2_rest(available_days, categories):
    """Assign categories in day order while enforcing a rest day after VO2max."""
    planned = []
    category_index = 0
    blocked_next_day = None

    for day in available_days:
        day_idx = DAY_INDEX.get(day, 99)

        if blocked_next_day is not None and day_idx == blocked_next_day:
            blocked_next_day = None
            continue

        if category_index >= len(categories):
            break

        category = categories[category_index]
        category_index += 1

        planned.append((day, category))

        if category == "VO2max":
            blocked_next_day = day_idx + 1
        else:
            blocked_next_day = None

    return planned


def _allocate_session_tss(total_tss, session_categories, goal, phase):
    if not session_categories:
        return {}

    distribution = normalize_distribution_for_categories(goal, session_categories, phase=phase)

    counts = {}
    for category in session_categories:
        counts[category] = counts.get(category, 0) + 1

    budgets = {
        category: float(total_tss) * float(distribution.get(category, 0.0))
        for category in counts
    }

    if "VO2max" in budgets:
        capped = min(budgets["VO2max"], float(get_vo2max_budget(total_tss, goal)))
        overflow = budgets["VO2max"] - capped
        budgets["VO2max"] = capped
        budgets["Endurance"] = budgets.get("Endurance", 0.0) + max(0.0, overflow)

    return {
        category: (budgets.get(category, 0.0) / max(1, counts[category]))
        for category in counts
    }

def create_training_plan(
    weekly_tss,
    progression,
    availability,
    goal,
    goal_date=None,
    workouts=None,
    week_number=1,
    athlete_level="Amateur",
):
    available_days = get_available_days(availability)
    day_weights = get_day_weights(availability)
    if not available_days:
        return []

    target_tss = _effective_weekly_tss(weekly_tss, progression, week_number)
    phase = get_training_phase(goal_date)

    categories = get_session_categories(len(available_days), phase=phase)

    # Rule: enforce calendar rest day after every VO2max session.
    planned_pairs = _build_workout_days_with_vo2_rest(available_days, categories)
    session_categories = [category for _, category in planned_pairs]
    session_tss = _allocate_session_tss(target_tss, session_categories, goal, phase)

    schedule = [
        {
            "day": day,
            "category": category,
            "target_tss": round(float(session_tss.get(category, 0.0))),
        }
        for day, category in planned_pairs
    ]

    for day in schedule:
        day_weight = float(day_weights.get(day["day"], 1.0))
        if day_weight > 0:
            day["target_tss"] = round(day["target_tss"] * max(0.9, min(1.2, day_weight / 2.0 + 0.5)))

        day["load"] = _load_for_tss(day.get("target_tss", 0))
        if workouts:
            max_hours = _day_hours(availability, day["day"])
            candidates = workouts
            if max_hours > 0:
                fitted = [
                    workout
                    for workout in workouts
                    if _workout_hours(workout) <= max_hours
                ]
                if fitted:
                    candidates = fitted

            day["workout"] = select_workout(
                day["category"],
                day["load"],
                candidates,
                target_tss=day["target_tss"],
            )

    return schedule