"""Strict validation for generated workout definitions and FIT payloads."""

import io

from fitparse import FitFile

from .workout_definitions import Workout


def validate_definition(workout: Workout) -> None:
    if not workout.steps:
        raise ValueError(f"{workout.id}: workout has no steps")
    if workout.duration_seconds <= 0:
        raise ValueError(f"{workout.id}: duration must be positive")
    if not 0.3 <= workout.target_if <= 1.5:
        raise ValueError(f"{workout.id}: target IF is outside 0.30-1.50")
    for step in workout.steps:
        if step.duration_seconds <= 0 or step.repeat <= 0:
            raise ValueError(
                f"{workout.id}: invalid step "
                f"name={step.name!r}, "
                f"duration_seconds={step.duration_seconds}, "
                f"repeat={step.repeat}"
            )
        if not 0 <= step.intensity <= 150:
            raise ValueError(f"{workout.id}: intensity is outside 0-150% FTP")
    if workout.steps[0].name.lower().find("warm") < 0:
        raise ValueError(f"{workout.id}: workout must start with a warm-up")
    if workout.steps[-1].name.lower().find("cool") < 0:
        raise ValueError(f"{workout.id}: workout must end with a cool-down")
    interval_labels = [step.name.lower() for step in workout.steps]
    interval_work = (
        sum("interval" in label for label in interval_labels) > 1
        or any("under" in label or "over" in label for label in interval_labels)
    )
    if workout.category in {"VO2max", "Threshold"} and interval_work and workout.subtype != "sustained_threshold":
        if not any("recover" in step.name.lower() for step in workout.steps):
            raise ValueError(f"{workout.id}: hard workout needs recovery steps")


def validate_fit(payload: bytes) -> None:
    if not payload or len(payload) < 20:
        raise ValueError("FIT payload is empty or too small")
    list(FitFile(io.BytesIO(payload)).get_messages("workout"))
    steps = list(FitFile(io.BytesIO(payload)).get_messages("workout_step"))
    if not steps:
        raise ValueError("FIT payload contains no workout steps")


def validate_unique(workouts: list[Workout]) -> None:
    ids = [workout.id for workout in workouts]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate workout IDs detected")
    signatures = [
        tuple((step.name, step.duration_seconds, step.intensity, step.repeat) for step in workout.steps)
        for workout in workouts
    ]
    if len(signatures) != len(set(signatures)):
        raise ValueError("Duplicate workout structures detected")
