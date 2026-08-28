"""Structured FIT export using the project's established fit-tool dependency."""

from helpers.fit_generator import generate_fit_workout
from .workout_definitions import Workout


def export_workout(workout: Workout) -> bytes:
    return generate_fit_workout(
        sport="Cycling",
        name=workout.name,
        steps=[step.__dict__ for step in workout.steps],
        ftp=250,
    )
