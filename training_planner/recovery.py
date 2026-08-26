"""Recovery validation rules for weekly plans."""


DAY_ORDER = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
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