from __future__ import annotations
import os
import datetime
import io
import tempfile
from typing import Iterable

from fit_tool.fit_file import FitFile
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


# =========================================================
# FIT constants
# =========================================================

POWER_PERCENT_OFFSET = 1000
PACE_PERCENT_OFFSET = 0


# =========================================================
# FIT file ID
# =========================================================

def _create_file_id_message() -> FileIdMessage:
    """
    Create the mandatory file_id message for a workout FIT file.
    """

    message = FileIdMessage()

    message.type = FileType.WORKOUT
    message.manufacturer = Manufacturer.DEVELOPMENT.value
    message.product = 0

    # FIT timestamp is milliseconds since FIT epoch.
    message.time_created = round(
        datetime.datetime.now().timestamp() * 1000
    )

    message.serial_number = 0x12345678

    return message


# =========================================================
# Intensity mapping
# =========================================================

def _get_intensity(
    step_name: str,
    intensity: float,
) -> Intensity:

    name = step_name.lower()

    if "warm" in name:
        return Intensity.WARMUP

    if "cool" in name:
        return Intensity.COOLDOWN

    if "recover" in name or "rest" in name:
        return Intensity.RECOVERY

    if intensity < 60:
        return Intensity.RECOVERY

    return Intensity.ACTIVE


# =========================================================
# Cycling power target
# =========================================================

def _cycling_power_target(
    ftp: float,
    intensity: float,
):
    """
    FIT's custom power target uses an offset of 1000.

    The value 0-1000 represents %FTP.
    """

    percent = max(
        0,
        min(250, intensity),
    )

    # FIT convention:
    # 1000 + percentage of FTP
    #
    # Example:
    # 90% FTP -> 1090
    target_value = POWER_PERCENT_OFFSET + percent

    return int(round(target_value))


# =========================================================
# Running pace target
# =========================================================

def _pace_seconds_to_speed_mps(
    pace_seconds_per_km: float,
) -> float:

    if pace_seconds_per_km <= 0:
        raise ValueError(
            "Threshold pace must be greater than zero."
        )

    # seconds/km -> m/s
    return 1000 / pace_seconds_per_km


def _running_target_speed(
    threshold_pace_seconds: float,
    intensity: float,
) -> float:
    """
    Convert % threshold pace into target running speed.

    100% = threshold pace.

    Example:

    threshold = 4:00/km
    110% = 3:38/km approximately
    90%  = 4:27/km approximately
    """

    threshold_speed = _pace_seconds_to_speed_mps(
        threshold_pace_seconds
    )

    target_speed = (
        threshold_speed
        * intensity
        / 100
    )

    return target_speed


# =========================================================
# Create a workout step
# =========================================================

def _create_step(
    *,
    index: int,
    name: str,
    duration_type: str,
    duration_value: float,
    intensity: float,
    sport: str,
    ftp: float | None,
    threshold_pace: float | None,
) -> WorkoutStepMessage:

    step = WorkoutStepMessage()

    step.message_index = index

    step.workout_step_name = str(name)[:32]

    step.intensity = _get_intensity(
        name,
        intensity,
    )

    # -----------------------------------------------------
    # Duration
    # -----------------------------------------------------

    if duration_type == "Time":

        step.duration_type = (
            WorkoutStepDuration.TIME
        )

        # UI is in minutes.
        step.duration_time = (
            float(duration_value) * 60
        )

    elif duration_type == "Distance":

        step.duration_type = (
            WorkoutStepDuration.DISTANCE
        )

        # UI is in km.
        step.duration_distance = (
            float(duration_value) * 1000
        )

    else:

        raise ValueError(
            f"Unsupported duration type: {duration_type}"
        )

    # -----------------------------------------------------
    # Cycling
    # -----------------------------------------------------

    if sport == "Cycling":

        step.target_type = (
            WorkoutStepTarget.POWER
        )

        step.target_value = (
            _cycling_power_target(
                ftp=ftp,
                intensity=intensity,
            )
        )

    # -----------------------------------------------------
    # Running
    # -----------------------------------------------------

    elif sport == "Running":

        step.target_type = (
            WorkoutStepTarget.SPEED
        )

        speed = _running_target_speed(
            threshold_pace_seconds=threshold_pace,
            intensity=intensity,
        )

        # FIT speed is m/s.
        #
        # custom_target_speed_* uses:
        # m/s * 1000 in the FIT representation.
        step.custom_target_speed_low = speed
        step.custom_target_speed_high = speed

        step.target_value = 0

    else:

        raise ValueError(
            f"Unsupported sport: {sport}"
        )

    return step


# =========================================================
# Generate workout
# =========================================================

def generate_fit_workout(
    *,
    sport: str,
    name: str,
    steps: Iterable[dict],
    ftp: float | None = None,
    threshold_pace: float | None = None,
) -> bytes:
    """
    Generate a FIT workout file.

    Parameters
    ----------
    sport:
        "Cycling" or "Running"

    name:
        Workout name.

    steps:
        Iterable of dictionaries generated by the Workout Builder.

        Example:

        {
            "name": "Warm Up",
            "duration_type": "Time",
            "duration_value": 15,
            "intensity": 55,
            "repeat": 1,
        }

    ftp:
        Cycling FTP in watts.

    threshold_pace:
        Running threshold pace in seconds/km.

    Returns
    -------
    bytes
        Complete FIT file.
    """

    if sport not in {
        "Cycling",
        "Running",
    }:

        raise ValueError(
            "Sport must be Cycling or Running."
        )

    if not name:
        name = (
            "Cycling Workout"
            if sport == "Cycling"
            else "Running Workout"
        )

    # -----------------------------------------------------
    # Validate settings
    # -----------------------------------------------------

    if sport == "Cycling":

        if ftp is None or ftp <= 0:

            raise ValueError(
                "A valid cycling FTP is required."
            )

    if sport == "Running":

        if (
            threshold_pace is None
            or threshold_pace <= 0
        ):

            raise ValueError(
                "A valid running threshold pace is required."
            )

    # -----------------------------------------------------
    # Build FIT workout steps
    # -----------------------------------------------------

    workout_steps = []

    for original_step in steps:

        step_name = str(
            original_step.get(
                "name",
                "Step",
            )
        )

        duration_type = original_step.get(
            "duration_type",
            "Time",
        )

        duration_value = float(
            original_step.get(
                "duration_value",
                1,
            )
        )

        intensity = float(
            original_step.get(
                "intensity",
                70,
            )
        )

        repeat = int(
            original_step.get(
                "repeat",
                1,
            )
        )

        if repeat < 1:
            repeat = 1

        # -------------------------------------------------
        # Normal step
        # -------------------------------------------------

        if repeat == 1:

            step = _create_step(
                index=len(workout_steps),
                name=step_name,
                duration_type=duration_type,
                duration_value=duration_value,
                intensity=intensity,
                sport=sport,
                ftp=ftp,
                threshold_pace=threshold_pace,
            )

            workout_steps.append(step)

        # -------------------------------------------------
        # Repeated step
        #
        # For now we expand the repetitions into individual
        # FIT steps. This is deliberately simple and very
        # compatible with Garmin/Wahoo.
        # -------------------------------------------------

        else:

            for repetition in range(repeat):

                repeated_name = (
                    f"{step_name} "
                    f"{repetition + 1}/{repeat}"
                )

                step = _create_step(
                    index=len(workout_steps),
                    name=repeated_name,
                    duration_type=duration_type,
                    duration_value=duration_value,
                    intensity=intensity,
                    sport=sport,
                    ftp=ftp,
                    threshold_pace=threshold_pace,
                )

                workout_steps.append(step)

    if not workout_steps:

        raise ValueError(
            "The workout contains no steps."
        )

    # =====================================================
    # Workout message
    # =====================================================

    workout_message = WorkoutMessage()

    workout_message.workout_name = str(name)[:32]

    if sport == "Cycling":

        workout_message.sport = Sport.CYCLING

    else:

        workout_message.sport = Sport.RUNNING

    workout_message.num_valid_steps = (
        len(workout_steps)
    )

    # =====================================================
    # Build FIT
    # =====================================================

    builder = FitFileBuilder(
        auto_define=True,
        min_string_size=50,
    )

    builder.add(
        _create_file_id_message()
    )

    builder.add(
        workout_message
    )

    builder.add_all(
        workout_steps
    )

    fit_file = builder.build()

    # =========================================================
    # Write FIT file
    # =========================================================
    
    with tempfile.NamedTemporaryFile(
        suffix=".fit",
        delete=False,
    ) as tmp:

        temp_path = tmp.name

    try:

        fit_file.to_file(
            temp_path
        )

        with open(
            temp_path,
            "rb",
        ) as f:

            fit_bytes = f.read()

    finally:

        if os.path.exists(temp_path):

            os.remove(temp_path)

    return fit_bytes