
"""Structured running workout definitions for the workout library."""
from dataclasses import asdict, dataclass, field
from typing import Any

from helpers.metrics import RUNNING_ZONES


def intensity_to_zone(intensity):
    ratio = float(intensity) / 100
    for zone, limits in RUNNING_ZONES.items():
        if limits["min"] <= ratio < limits["max"]:
            return zone
    return "Anaerobic"


@dataclass(frozen=True)
class Step:
    name: str
    duration_seconds: int
    intensity: float
    duration_type: str = "Time"
    repeat: int = 1
    description: str = ""


@dataclass(frozen=True)
class Workout:
    id: str
    name: str
    category: str
    subtype: str
    steps: tuple[Step, ...]
    target_if: float
    sport: str = "Running"
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def duration_seconds(self) -> int:
        return sum(
            step.duration_seconds * step.repeat
            for step in self.steps
        )

    @property
    def target_tss(self) -> int:
        weighted = sum(
            step.duration_seconds
            * step.repeat
            * (step.intensity / 100) ** 2
            for step in self.steps
        )
        return round(weighted / 3600 * 100)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["steps"] = [asdict(step) for step in self.steps]
        data.update({
            "sport": self.sport,
            "duration_minutes": round(self.duration_seconds / 60),
            "estimated_tss": self.target_tss,
            "target_tss": self.target_tss,
            "target_if": round(self.target_if, 2),
            "interval_count": sum(
                step.repeat
                for step in self.steps
                if "interval" in step.name.lower()
                or "work" in step.name.lower()
            ),
            "interval_duration": next(
                (
                    step.duration_seconds
                    for step in self.steps
                    if "work" in step.name.lower()
                ),
                0,
            ),
            "recovery_duration": next(
                (
                    step.duration_seconds
                    for step in self.steps
                    if "recover" in step.name.lower()
                ),
                0,
            ),
            "sets": max(
                (step.repeat for step in self.steps),
                default=1,
            ),
        })
        return data


def _workout(
    workout_id,
    name,
    category,
    subtype,
    steps,
    tags,
):
    intensity_time = sum(
        step.duration_seconds
        * step.repeat
        * (step.intensity / 100) ** 4
        for step in steps
    )

    duration = sum(
        step.duration_seconds * step.repeat
        for step in steps
    )

    target_if = (
        intensity_time / max(duration, 1)
    ) ** 0.25

    return Workout(
        workout_id,
        name,
        category,
        subtype,
        tuple(steps),
        target_if,
        "Running",
        tuple(tags),
    )


def warmup(minutes=5):
    return Step(
        "Warm-up",
        round(minutes * 60),
        70,
        description="Easy running with gradual progression.",
    )


def cooldown(minutes=5):
    return Step(
        "Cool-down",
        round(minutes * 60),
        65,
        description="Easy running to bring the effort down.",
    )


def recovery(minutes, intensity=65, name="Recovery"):
    return Step(
        name,
        round(minutes * 60),
        intensity,
        description="Easy running or very light jogging.",
    )


def work(minutes, intensity, name="Work interval"):
    return Step(
        name,
        round(minutes * 60),
        intensity,
    )


def work_seconds(seconds, intensity, name="Work interval"):
    return Step(
        name,
        round(seconds),
        intensity,
    )


def build_workout(
    family,
    variant,
    category,
    subtype,
    work_steps,
    tags,
    warmup_minutes=5,
    cooldown_minutes=5,
):
    steps = [
        warmup(warmup_minutes + variant % 3),
        *work_steps,
        cooldown(cooldown_minutes + variant % 2),
    ]

    return _workout(
        f"{category.lower()}_{family}_{variant:02d}",
        f"{family.replace('_', ' ').title()} {variant:02d}",
        category,
        subtype,
        steps,
        [category.lower(), subtype, family, *tags],
    )


def add_endurance(
    steps,
    endurance_minutes,
    intensity=72,
):
    """Add endurance volume after the quality interval cap.

    The requested endurance time is total additional endurance,
    split before and after the quality work.
    """
    if endurance_minutes <= 0:
        return

    before = endurance_minutes // 2
    after = endurance_minutes - before

    if before > 0:
        steps.insert(
            0,
            work(
                before,
                intensity,
                "Endurance before intervals",
            ),
        )

    if after > 0:
        steps.append(
            work(
                after,
                intensity,
                "Endurance after intervals",
            ),
        )


def progression(
    variant,
    max_intervals,
    base_intervals=1,
    endurance_step=10,
):
    """Increase quality volume until capped, then add endurance."""
    quality_variants = (
        max_intervals - base_intervals + 1
    )

    if variant <= quality_variants:
        count = (
            base_intervals
            + variant
            - 1
        )
        endurance_minutes = 0
    else:
        count = max_intervals
        endurance_minutes = (
            variant - quality_variants
        ) * endurance_step

    return count, endurance_minutes


def strides(
    count=4,
    duration_seconds=20,
    recovery_seconds=60,
):
    steps = []

    for i in range(count):
        steps.append(
            Step(
                f"Stride {i + 1}",
                duration_seconds,
                115,
                description=(
                    "Fast relaxed acceleration "
                    "with good running form."
                ),
            )
        )

        if i < count - 1:
            steps.append(
                Step(
                    f"Stride recovery {i + 1}",
                    recovery_seconds,
                    65,
                )
            )

    return steps


def generate_running_workouts():
    workouts = []

    # ============================================================
    # ENDURANCE / EASY RUNNING
    # ============================================================

    easy_families = {
        # Keep the shortest generated workout around 15-20 min.
        "recovery_run": (8, 65),
        "easy_run": (15, 72),
        "aerobic_run": (30, 75),
        "progressive_easy": (30, 72),
    }

    for family, (base_minutes, intensity) in easy_families.items():
        for variant in range(1, 7):
            if family == "recovery_run":
                duration = base_minutes + variant * 2
            else:
                duration = base_minutes + variant * 5

            if family == "progressive_easy":
                half = duration // 2

                steps = [
                    work(
                        half,
                        intensity - 4,
                        "Easy running",
                    ),
                    work(
                        duration - half,
                        intensity + 5,
                        "Progressive finish",
                    ),
                ]
            else:
                steps = [
                    work(
                        duration,
                        intensity,
                        "Easy running",
                    )
                ]

            workouts.append(
                build_workout(
                    family,
                    variant,
                    "Endurance",
                    family,
                    steps,
                    ["easy", "aerobic", "running"],
                    3 if family == "recovery_run" else 5,
                    3 if family == "recovery_run" else 5,
                )
            )

    # ============================================================
    # LONG RUNS
    # Maximum total workout duration stays below 3 hours.
    # ============================================================

    long_families = {
        "long_run": (60, 72, 10),
        "progressive_long_run": (70, 72, 10),
        "long_run_finish": (75, 72, 10),
        "extended_long_run": (90, 70, 15),
        "ultra_long_run": (120, 68, 10),
    }

    for family, (
        base_minutes,
        intensity,
        progression_step,
    ) in long_families.items():

        for variant in range(1, 7):
            duration = (
                base_minutes
                + variant * progression_step
            )

            # Never allow the running library to exceed 3 hours.
            duration = min(duration, 168)

            if family == "progressive_long_run":
                finish = min(20, duration // 4)

                steps = [
                    work(
                        duration - finish,
                        intensity,
                        "Long aerobic block",
                    ),
                    work(
                        finish,
                        82 + variant % 3,
                        "Progressive finish",
                    ),
                ]

            elif family == "long_run_finish":
                tempo = min(15, duration // 6)
                strong = min(10, duration // 8)
                aerobic = duration - tempo - strong

                steps = [
                    work(
                        aerobic,
                        intensity,
                        "Long aerobic block",
                    ),
                    work(
                        tempo,
                        84,
                        "Tempo finish",
                    ),
                    work(
                        strong,
                        88 + variant % 2,
                        "Strong finish",
                    ),
                ]

            else:
                steps = [
                    work(
                        duration,
                        intensity,
                        "Long run",
                    )
                ]

            workouts.append(
                build_workout(
                    family,
                    variant,
                    "Endurance",
                    family,
                    steps,
                    ["long-run", "aerobic", "easy"],
                    5,
                    5,
                )
            )

    # ============================================================
    # TEMPO
    #
    # First increase the number of blocks.
    # Once capped, add endurance.
    # ============================================================

    tempo_families = {
        # work duration, intensity, max blocks, base blocks
        "steady_tempo": (8, 87, 4, 2),
        "tempo_blocks": (10, 90, 4, 2),
        "progressive_tempo": (8, 87, 4, 2),
        "tempo_ladder": (6, 87, 4, 2),
        "tempo_endurance": (15, 85, 3, 1),
    }

    for family, (
        work_minutes,
        intensity,
        max_blocks,
        base_blocks,
    ) in tempo_families.items():

        for variant in range(1, 7):
            blocks, endurance_minutes = progression(
                variant,
                max_blocks,
                base_blocks,
                endurance_step=10,
            )

            steps = []

            for i in range(blocks):
                if family == "tempo_ladder":
                    duration = (
                        work_minutes
                        + i * 2
                    )
                    current_intensity = (
                        intensity
                        + i * 2
                    )

                elif family == "progressive_tempo":
                    duration = work_minutes
                    current_intensity = (
                        intensity
                        + i * 3
                    )

                else:
                    duration = work_minutes
                    current_intensity = intensity

                steps.append(
                    work(
                        duration,
                        current_intensity,
                        f"Tempo block {i + 1}",
                    )
                )

                if i < blocks - 1:
                    steps.append(
                        recovery(
                            2 if family != "tempo_endurance" else 3
                        )
                    )

            add_endurance(
                steps,
                endurance_minutes,
                72,
            )

            workouts.append(
                build_workout(
                    family,
                    variant,
                    "Tempo",
                    family,
                    steps,
                    ["tempo", "aerobic", "moderate"],
                    5,
                    5,
                )
            )

    # ============================================================
    # THRESHOLD
    #
    # Important progression:
    # 10 min threshold -> 1 -> 2 -> 3 intervals -> endurance.
    # ============================================================

    threshold_families = {
        # work duration, recovery, max intervals, base intervals, intensity
        "cruise_intervals": (8, 3, 5, 2, 98),
        "threshold_intervals": (6, 3, 5, 2, 102),
        "long_threshold": (10, 3, 4, 1, 100),
        "threshold_ladder": (5, 2, 4, 2, 98),
        "broken_threshold": (15, 3, 3, 1, 97),

        # Specifically:
        # 1 x 25 -> 2 x 25 -> 3 x 25 -> endurance.
        "sustained_threshold": (25, 0, 3, 1, 96),
    }

    for family, (
        work_minutes,
        recover_minutes,
        max_intervals,
        base_intervals,
        intensity,
    ) in threshold_families.items():

        for variant in range(1, 7):
            count, endurance_minutes = progression(
                variant,
                max_intervals,
                base_intervals,
                endurance_step=10,
            )

            steps = []

            if family == "threshold_ladder":
                for i in range(count):
                    duration = (
                        work_minutes
                        + i * 2
                    )
                    current_intensity = (
                        intensity
                        + i
                    )

                    steps.append(
                        work(
                            duration,
                            current_intensity,
                            f"Threshold ladder {i + 1}",
                        )
                    )

                    if i < count - 1:
                        steps.append(
                            recovery(
                                recover_minutes
                            )
                        )

            elif family == "sustained_threshold":
                # For this family, increasing the number of
                # intervals is more useful than endlessly
                # extending a single threshold effort.
                for i in range(count):
                    steps.append(
                        work(
                            work_minutes,
                            intensity,
                            f"10 min threshold interval {i + 1}"
                            if work_minutes == 10
                            else f"Sustained threshold {i + 1}",
                        )
                    )

                    if i < count - 1:
                        steps.append(
                            recovery(3)
                        )

            else:
                for i in range(count):
                    steps.append(
                        work(
                            work_minutes,
                            intensity,
                            f"Threshold interval {i + 1}",
                        )
                    )

                    if i < count - 1 and recover_minutes:
                        steps.append(
                            recovery(
                                recover_minutes
                            )
                        )

            add_endurance(
                steps,
                endurance_minutes,
                72,
            )

            workouts.append(
                build_workout(
                    family,
                    variant,
                    "Threshold",
                    family,
                    steps,
                    ["threshold", "hard", "race-specific"],
                    5,
                    5,
                )
            )

    # ============================================================
    # NORWEGIAN VO2
    #
    # 1 -> 2 -> 3 -> 4 -> 5 intervals
    # then endurance.
    # ============================================================

    norwegian = {
        "norwegian_4": (4, 3, 5, 1, 115),
    }

    for family, (
        work_minutes,
        recover_minutes,
        max_intervals,
        base_intervals,
        intensity,
    ) in norwegian.items():

        for variant in range(1, 7):
            count, endurance_minutes = progression(
                variant,
                max_intervals,
                base_intervals,
                endurance_step=10,
            )

            steps = []

            for i in range(count):
                steps.append(
                    work(
                        work_minutes,
                        intensity,
                        f"Norwegian interval {i + 1}",
                    )
                )

                if i < count - 1:
                    steps.append(
                        recovery(
                            recover_minutes,
                            65,
                        )
                    )

            add_endurance(
                steps,
                endurance_minutes,
                72,
            )

            workouts.append(
                build_workout(
                    family,
                    variant,
                    "VO2max",
                    family,
                    steps,
                    [
                        "norwegian",
                        "vo2max",
                        "controlled",
                        "running",
                    ],
                    5,
                    5,
                )
            )

    # ============================================================
    # RONNESTAD
    #
    # 1 -> 2 -> 3 sets
    # then endurance.
    # ============================================================

    ronnestad = {
        "ronnestad_30_15": (30, 15, 115),
    }

    for family, (
        work_seconds_value,
        recover_seconds_value,
        intensity,
    ) in ronnestad.items():

        for variant in range(1, 7):
            current_sets = min(
                variant,
                3,
            )

            endurance_minutes = max(
                0,
                variant - 3,
            ) * 10

            steps = []

            for s in range(current_sets):
                for r in range(13):
                    steps.append(
                        work_seconds(
                            work_seconds_value,
                            intensity,
                            f"Ronnestad 30 sec Work {s + 1}.{r + 1}",
                        )
                    )

                    if r < 12:
                        steps.append(
                            work_seconds(
                                recover_seconds_value,
                                65,
                                f"Ronnestad 15 sec Recovery {s + 1}.{r + 1}",
                            )
                        )

                if s < current_sets - 1:
                    steps.append(
                        recovery(
                            3,
                            65,
                            f"Set recovery {s + 1}",
                        )
                    )

            add_endurance(
                steps,
                endurance_minutes,
                72,
            )

            workouts.append(
                build_workout(
                    family,
                    variant,
                    "VO2max",
                    family,
                    steps,
                    [
                        "ronnestad",
                        "30-15",
                        "vo2max",
                        "high-intensity",
                    ],
                    5,
                    5,
                )
            )

    # ============================================================
    # VO2MAX
    #
    # Progress interval count first.
    # Then add endurance.
    # ============================================================

    vo2_families = {
        # work, recovery, max intervals, base intervals, intensity
        "four_by_four": (4, 4, 5, 2, 108),
        "five_by_three": (3, 2, 5, 2, 110),
        "six_by_two": (2, 2, 6, 2, 112),
        "short_vo2": (1, 1, 10, 4, 116),
        "long_vo2": (5, 3, 4, 1, 108),
        "vo2_ladder": (2, 2, 5, 2, 107),
    }

    for family, (
        work_minutes,
        recover_minutes,
        max_intervals,
        base_intervals,
        intensity,
    ) in vo2_families.items():

        for variant in range(1, 7):
            count, endurance_minutes = progression(
                variant,
                max_intervals,
                base_intervals,
                endurance_step=10,
            )

            steps = []

            for i in range(count):
                if family == "vo2_ladder":
                    current_intensity = (
                        intensity
                        + i * 2
                    )
                else:
                    current_intensity = intensity

                steps.append(
                    work(
                        work_minutes,
                        current_intensity,
                        f"VO2max interval {i + 1}",
                    )
                )

                if i < count - 1:
                    steps.append(
                        recovery(
                            recover_minutes,
                            65,
                        )
                    )

            add_endurance(
                steps,
                endurance_minutes,
                72,
            )

            workouts.append(
                build_workout(
                    family,
                    variant,
                    "VO2max",
                    family,
                    steps,
                    [
                        "vo2max",
                        "high-intensity",
                        "hard",
                    ],
                    5,
                    5,
                )
            )

    # ============================================================
    # HILLS
    #
    # Increase hill repetitions first, then endurance.
    # ============================================================

    hill_families = {
        "hill_repeats": (1, 2, 8, 4, 108),
        "long_hills": (3, 3, 6, 2, 108),
        "hill_sprints": (0.5, 2, 8, 4, 125),
    }

    for family, (
        work_minutes,
        recover_minutes,
        max_repeats,
        base_repeats,
        intensity,
    ) in hill_families.items():

        for variant in range(1, 7):
            count, endurance_minutes = progression(
                variant,
                max_repeats,
                base_repeats,
                endurance_step=10,
            )

            steps = []

            for i in range(count):
                current_intensity = (
                    intensity
                    + (variant % 2)
                )

                steps.append(
                    work(
                        work_minutes,
                        current_intensity,
                        f"Hill repeat {i + 1}",
                    )
                )

                if i < count - 1:
                    steps.append(
                        recovery(
                            recover_minutes,
                            65,
                        )
                    )

            add_endurance(
                steps,
                endurance_minutes,
                72,
            )

            workouts.append(
                build_workout(
                    family,
                    variant,
                    "VO2max",
                    family,
                    steps,
                    [
                        "hills",
                        "strength",
                        "high-intensity",
                    ],
                    5,
                    5,
                )
            )

    # ============================================================
    # OPENERS
    #
    # These remain short and are not treated as normal
    # interval-progression workouts.
    # ============================================================

    opener_families = {
        "short_openers": (4, 1, 2, 102),
        "race_openers": (5, 1, 2, 108),
        "progressive_openers": (4, 1, 2, 98),
        "speed_openers": (6, 0.5, 1.5, 115),
    }

    for family, (
        reps,
        work_minutes,
        recover_minutes,
        intensity,
    ) in opener_families.items():

        for variant in range(1, 7):
            count = reps + variant % 2
            steps = []

            for i in range(count):
                if family == "progressive_openers":
                    current_intensity = (
                        intensity
                        + i * 4
                        + variant % 2
                    )
                elif family == "speed_openers":
                    current_intensity = (
                        intensity
                        + variant % 3
                    )
                else:
                    current_intensity = (
                        intensity
                        + variant % 3
                    )

                steps.append(
                    work(
                        work_minutes,
                        current_intensity,
                        f"Opener {i + 1}",
                    )
                )

                if i < count - 1:
                    steps.append(
                        recovery(
                            recover_minutes,
                            65,
                        )
                    )

            workouts.append(
                build_workout(
                    family,
                    variant,
                    "Openers",
                    family,
                    steps,
                    [
                        "openers",
                        "race-prep",
                        "activation",
                        "running",
                    ],
                    8,
                    5,
                )
            )

    # ============================================================
    # 6-MINUTE RUNNING TEST
    # ============================================================

    test = {
        "6_min_run": (360, 120),
    }

    for family, (
        duration_seconds,
        intensity,
    ) in test.items():

        for variant in range(1, 2):
            steps = [
                Step(
                    "Test Warmup",
                    30,
                    120,
                ),
                recovery(
                    2,
                    65,
                ),
                Step(
                    "6 Minute Running Test",
                    duration_seconds,
                    intensity,
                ),
            ]

            workouts.append(
                build_workout(
                    family,
                    variant,
                    "TEST",
                    family,
                    steps,
                    [
                        "test",
                        "6-minute",
                        "running",
                        "vo2max",
                    ],
                    5,
                    5,
                )
            )

    return workouts
