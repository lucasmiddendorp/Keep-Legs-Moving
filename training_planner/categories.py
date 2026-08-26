"""Assign categories to each available day."""

from math import floor

from .training_load import calculate_daily_tss


DAY_ORDER = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}

CATEGORY_PRIORITY = ["VO2max", "Threshold", "Tempo", "Endurance"]


def _session_slots(distribution, day_count):
    raw = {
        category: max(0.0, float(pct or 0.0)) * day_count
        for category, pct in distribution.items()
    }

    slots = {
        category: floor(value)
        for category, value in raw.items()
    }

    assigned = sum(slots.values())
    remainder = max(0, day_count - assigned)

    ranked = sorted(
        raw.items(),
        key=lambda item: (item[1] - floor(item[1]), item[1]),
        reverse=True,
    )

    for category, _ in ranked:
        if remainder <= 0:
            break
        slots[category] += 1
        remainder -= 1

    while remainder > 0 and ranked:
        for category, _ in ranked:
            if remainder <= 0:
                break
            slots[category] += 1
            remainder -= 1

    return slots


def _pick_category(remaining_slots, recent_categories):
    candidates = [
        category
        for category, count in remaining_slots.items()
        if count > 0 and category not in recent_categories
    ]

    if not candidates:
        candidates = [
            category
            for category, count in remaining_slots.items()
            if count > 0
        ]

    if not candidates:
        return "Endurance"

    return max(
        candidates,
        key=lambda category: (
            remaining_slots.get(category, 0),
            -CATEGORY_PRIORITY.index(category) if category in CATEGORY_PRIORITY else -99,
        ),
    )


def enforce_category_spacing(schedule, min_workouts_between=2):
    """Ensure the same category is not repeated too soon in workout sequence."""
    if min_workouts_between <= 0:
        return schedule

    for index, item in enumerate(schedule):
        recent = {
            schedule[idx].get("category")
            for idx in range(max(0, index - min_workouts_between), index)
        }

        category = item.get("category")
        if category not in recent:
            continue

        replacement = next(
            (
                candidate
                for candidate in CATEGORY_PRIORITY
                if candidate not in recent
            ),
            None,
        )

        if replacement:
            item["category"] = replacement

    return schedule


def assign_training_categories(available_days, weekly_tss, distribution, day_weights):
    if not available_days:
        return []

    ordered_days = sorted(available_days, key=lambda day: DAY_ORDER.get(day, 99))

    daily_tss = calculate_daily_tss(weekly_tss, day_weights)
    slots = _session_slots(distribution, len(ordered_days))

    categories = []
    category_history = []

    for day in ordered_days:
        recent = set(category_history[-2:])
        category = _pick_category(slots, recent)
        slots[category] = max(0, slots.get(category, 0) - 1)
        category_history.append(category)

        categories.append(
            {
                "day": day,
                "category": category,
                "target_tss": float(daily_tss.get(day, 0.0)),
            }
        )

    return enforce_category_spacing(categories, min_workouts_between=2)