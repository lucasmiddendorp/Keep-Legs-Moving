"""Select a workout for a given category and load level."""


def _workout_level(workout):
    return str(workout.get("level") or workout.get("_level") or "").upper()


def _workout_category(workout):
    return str(workout.get("category") or workout.get("_category") or "")


def select_workout(category, load_level, workouts, target_tss=None):
    category_options = [
        workout
        for workout in workouts
        if _workout_category(workout) == category
    ]

    if not category_options:
        return None

    level_options = [
        workout
        for workout in category_options
        if _workout_level(workout) == str(load_level).upper()
    ]

    options = level_options or category_options

    if target_tss is None:
        return options[0]

    return min(
        options,
        key=lambda workout: abs(float(workout.get("target_tss", 0) or 0) - float(target_tss)),
    )