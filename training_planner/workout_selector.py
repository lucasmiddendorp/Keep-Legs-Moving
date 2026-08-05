import random

from training_planner.workout_library import WORKOUT_LIBRARY
from training_planner.training_state import evaluate_training_state
from helpers.metrics import calculate_workout_metrics


def select_category(
        athlete,
        phase,
        goal_distribution
):

    state = evaluate_training_state(
        athlete
    )["state"]


    if state == "Recovery":

        return "Recovery"



    if state == "Fatigued":

        choices = [
            category
            for category in [
                "Endurance",
                "Tempo",
                "Recovery"
            ]
            if category in goal_distribution
        ]

        return random.choice(
            choices
        )



    if state == "Fresh":

        hard_sessions = [
            category
            for category in [
                "Threshold",
                "VO2 Max"
            ]
            if category in goal_distribution
        ]

        if hard_sessions:

            return random.choice(
                hard_sessions
            )



    categories = list(
        goal_distribution.keys()
    )


    weights = list(
        goal_distribution.values()
    )


    return random.choices(
        categories,
        weights=weights,
        k=1
    )[0]



def select_workout(
        category,
        athlete,
        available_hours=None
):

    workouts = WORKOUT_LIBRARY.get(
        category,
        WORKOUT_LIBRARY["Endurance"]
    )


    # Availability constraint

    if available_hours is not None:

        max_duration = available_hours * 60


        filtered = []


        for workout in workouts:

            duration = sum(
                step["duration"]
                for step in workout["steps"]
            )


            if duration <= max_duration:

                filtered.append(
                    workout
                )


        if filtered:

            workouts = filtered



    # Fatigue constraint

    if athlete.tsb < -15:

        filtered = []


        for workout in workouts:

            metrics = calculate_workout_metrics(
                workout
            )


            if metrics["tss"] < 120:

                filtered.append(
                    workout
                )


        if filtered:

            workouts = filtered



    # Safety fallback

    if not workouts:

        workouts = WORKOUT_LIBRARY["Recovery"]



    workout = random.choice(
        workouts
    ).copy()


    metrics = calculate_workout_metrics(
        workout
    )


    workout.update(
        metrics
    )


    return workout