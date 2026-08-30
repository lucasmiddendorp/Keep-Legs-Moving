"""Structured FIT export for running workouts."""
from helpers.fit_generator import generate_fit_workout
from .running_workout_definitions import Workout

def export_running_workout(workout: Workout, threshold_pace: float) -> bytes:
    return generate_fit_workout(
        sport="Running",
        name=workout.name,
        steps=[step.__dict__ for step in workout.steps],
        threshold_pace=threshold_pace,
    )