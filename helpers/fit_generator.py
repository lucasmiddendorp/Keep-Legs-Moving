from __future__ import annotations

import datetime
import os
import tempfile
from typing import Iterable

from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.workout_message import WorkoutMessage
from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_tool.profile.profile_type import (
    Sport,
    Intensity,
    WorkoutStepDuration,
    WorkoutStepTarget,
    Manufacturer,
    FileType,
)


def _file_id():
    m = FileIdMessage()
    m.type = FileType.WORKOUT
    m.manufacturer = Manufacturer.DEVELOPMENT.value
    m.product = 0
    m.time_created = round(datetime.datetime.now().timestamp() * 1000)
    m.serial_number = int(datetime.datetime.now().timestamp())
    return m


def _intensity(name, value):
    name = name.lower()
    if "warm" in name:
        return Intensity.WARMUP
    if "cool" in name:
        return Intensity.COOLDOWN
    if "rest" in name or "recover" in name or value < 60:
        return Intensity.RECOVERY
    return Intensity.ACTIVE


def _power_target(intensity):
    # FIT custom power target: 100 = 100% FTP, 120 = 120% FTP
    return int(round(max(0, min(1000, intensity))))


def _speed_target(threshold_pace, intensity):
    speed_mps = (1000 / threshold_pace) * (intensity / 100)
    return int(round(speed_mps * 1000))


def _duration(step):
    if "duration_value" in step:
        return float(step["duration_value"])

    minutes = float(step.get("duration_minutes", 0))
    seconds = float(step.get("duration_seconds", 0))
    return minutes * 60 + seconds


def _create_step(
    index,
    name,
    duration_type,
    duration_value,
    intensity,
    sport,
    ftp,
    threshold_pace,
):
    step = WorkoutStepMessage()
    step.message_index = index
    step.workout_step_name = str(name)[:32]
    step.intensity = _intensity(name, intensity)

    if duration_type == "Time":
        step.duration_type = WorkoutStepDuration.TIME
        step.duration_time = int(round(duration_value))
    elif duration_type == "Distance":
        step.duration_type = WorkoutStepDuration.DISTANCE
        step.duration_distance = int(round(duration_value * 1000))
    else:
        raise ValueError(f"Unsupported duration type: {duration_type}")

    if sport == "Cycling":
        target = _power_target(intensity)
        step.target_type = WorkoutStepTarget.POWER
        step.target_value = 0
        step.custom_target_power_low = target
        step.custom_target_power_high = target

    elif sport == "Running":
        target = _speed_target(threshold_pace, intensity)
        step.target_type = WorkoutStepTarget.SPEED
        step.target_value = 0
        step.custom_target_speed_low = target
        step.custom_target_speed_high = target

    else:
        raise ValueError(f"Unsupported sport: {sport}")

    return step


def generate_fit_workout(
    *,
    sport: str,
    name: str,
    steps: Iterable[dict],
    ftp: float | None = None,
    threshold_pace: float | None = None,
) -> bytes:

    if sport not in {"Cycling", "Running"}:
        raise ValueError("Sport must be Cycling or Running.")

    if sport == "Cycling" and (ftp is None or ftp <= 0):
        raise ValueError("A valid cycling FTP is required.")

    if sport == "Running" and (
        threshold_pace is None or threshold_pace <= 0
    ):
        raise ValueError("A valid running threshold pace is required.")

    workout_steps = []

    for original in steps:
        name_step = str(original.get("name", "Step"))
        duration_type = original.get("duration_type", "Time")
        duration_value = _duration(original)
        intensity = float(original.get("intensity", 70))
        repeat = max(1, int(original.get("repeat", 1)))

        for r in range(repeat):
            step_name = (
                name_step
                if repeat == 1
                else f"{name_step} {r + 1}/{repeat}"
            )

            workout_steps.append(
                _create_step(
                    index=len(workout_steps),
                    name=step_name,
                    duration_type=duration_type,
                    duration_value=duration_value,
                    intensity=intensity,
                    sport=sport,
                    ftp=ftp,
                    threshold_pace=threshold_pace,
                )
            )

    if not workout_steps:
        raise ValueError("The workout contains no steps.")

    workout = WorkoutMessage()
    workout.workout_name = str(name or "Workout")[:32]
    workout.sport = (
        Sport.CYCLING if sport == "Cycling" else Sport.RUNNING
    )
    workout.num_valid_steps = len(workout_steps)

    builder = FitFileBuilder(
        auto_define=True,
        min_string_size=50,
    )

    builder.add(_file_id())
    builder.add(workout)
    builder.add_all(workout_steps)

    fit_file = builder.build()

    with tempfile.NamedTemporaryFile(
        suffix=".fit",
        delete=False,
    ) as tmp:
        path = tmp.name

    try:
        fit_file.to_file(path)
        with open(path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(path):
            os.remove(path)