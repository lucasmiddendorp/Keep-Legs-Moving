"""Structured cycling workout definitions used by the library generator."""
from dataclasses import asdict, dataclass, field
from typing import Any

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
    sport: str
    steps: tuple[Step, ...]
    target_if: float
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def duration_seconds(self) -> int:
        return sum(step.duration_seconds * step.repeat for step in self.steps)

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
                    or "interval" in step.name.lower()
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

def _workout(workout_id, name, category, subtype, sport, steps, tags):
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
    target_if = (intensity_time / max(duration, 1)) ** 0.25
    return Workout(
        workout_id,
        name,
        category,
        subtype,
        sport,
        tuple(steps),
        target_if,
        tuple(tags),
    )

def warmup(minutes=10):
    return Step(
        "Warm-up",
        round(minutes * 60),
        60,
        description="Progressive warm-up.",
    )

def cooldown(minutes=10):
    return Step(
        "Cool-down",
        round(minutes * 60),
        55,
        description="Easy riding to finish the workout.",
    )

def recovery(minutes, intensity=50, name="Recovery"):
    return Step(
        name,
        round(minutes * 60),
        intensity,
        description="Easy recovery riding.",
    )

def endurance(minutes, intensity=70, name="Endurance"):
    return Step(
        name,
        round(minutes * 60),
        intensity,
        description="Aerobic endurance riding.",
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
    warmup_minutes=10,
    cooldown_minutes=10,
):
    steps = [*work_steps]

    if warmup_minutes > 0:
        steps.insert(
            0,
            warmup(warmup_minutes + variant % 3),
        )

    if cooldown_minutes > 0:
        steps.append(
            cooldown(cooldown_minutes + variant % 2)
        )

    return _workout(
        f"cycling_{category.lower()}_{family}_{variant:02d}",
        f"{family.replace('_', ' ').title()} {variant:02d}",
        category,
        subtype,
        "Cycling",
        steps,
        [
            "cycling",
            category.lower(),
            subtype,
            family,
            *tags,
        ],
    )

def repeated_intervals(
    count,
    work_duration,
    work_intensity,
    recovery_duration,
    work_name="Work interval",
    recovery_intensity=60,
):
    steps = []

    for i in range(count):
        steps.append(
            work(
                work_duration,
                work_intensity,
                f"{work_name} {i + 1}",
            )
        )

        if i < count - 1 and recovery_duration > 0:
            steps.append(
                recovery(
                    recovery_duration,
                    recovery_intensity,
                    f"Recovery {i + 1}",
                )
            )

    return steps

def repeated_intervals_seconds(
    count,
    work_duration_seconds,
    work_intensity,
    recovery_duration_seconds,
    work_name="Work interval",
    recovery_intensity=60,
):
    steps = []

    for i in range(count):
        steps.append(
            work_seconds(
                work_duration_seconds,
                work_intensity,
                f"{work_name} {i + 1}",
            )
        )

        if i < count - 1 and recovery_duration_seconds > 0:
            steps.append(
                Step(
                    f"Recovery {i + 1}",
                    round(recovery_duration_seconds),
                    recovery_intensity,
                )
            )

    return steps

def ronnestad_set(
    set_number,
    work_seconds_value=30,
    recovery_seconds_value=15,
    reps=13,
    intensity=115,
):
    steps = []

    for rep in range(reps):
        steps.append(
            Step(
                f"Ronnestad 30 sec Work {set_number}.{rep + 1}",
                work_seconds_value,
                intensity,
                description="High-intensity 30-second effort.",
            )
        )

        if rep < reps - 1:
            steps.append(
                Step(
                    f"Ronnestad 15 sec Recovery {set_number}.{rep + 1}",
                    recovery_seconds_value,
                    62,
                    description="Short controlled recovery.",
                )
            )

    return steps

def interval_progression(
    variant,
    max_intervals,
    base_intervals=1,
    endurance_step=10,
):
    """
    Progress quality volume first.

    Example max_intervals=3, base_intervals=1:
    1 -> 1 interval
    2 -> 2 intervals
    3 -> 3 intervals
    4 -> 3 intervals + 10 min endurance
    5 -> 3 intervals + 20 min endurance
    6 -> 3 intervals + 30 min endurance

    Example max_intervals=5, base_intervals=2:
    1 -> 2 intervals
    2 -> 3 intervals
    3 -> 4 intervals
    4 -> 5 intervals
    5 -> 5 intervals + 10 min endurance
    6 -> 5 intervals + 20 min endurance
    """
    quality_variants = max_intervals - base_intervals + 1

    if variant <= quality_variants:
        count = base_intervals + variant - 1
        endurance_minutes = 0
    else:
        count = max_intervals
        endurance_minutes = (
            variant - quality_variants
        ) * endurance_step

    return count, endurance_minutes

def add_endurance(
    steps,
    endurance_minutes,
    intensity=70,
):
    if endurance_minutes > 0:
        steps.insert(
            0,
            endurance(
                endurance_minutes,
                intensity,
                "Endurance before intervals",
            ),
        )
        steps.append(
            endurance(
                endurance_minutes,
                intensity,
                "Endurance after intervals",
            ),
        )

def generate_workouts():
    workouts = []

    # ============================================================
    # VO2MAX
    # Most VO2 workouts progress 2 -> 3 -> 4 -> 5 intervals.
    # After 5 quality intervals, variants become longer through
    # additional endurance before and after the intervals.
    # ============================================================
    vo2_families = {
        "long_vo2": (4, 4, 108, 5, 2),
        "four_by_four": (4, 4, 112, 5, 2),
        "short_vo2": (2, 2, 120, 5, 2),
        "micro_intervals": (1, 1, 118, 5, 2),
        "ascending_vo2": (3, 3, 108, 5, 2),
        "descending_vo2": (4, 4, 112, 5, 2),
        "variable_vo2": (2, 2, 110, 5, 2),
        "repeated_vo2_blocks": (3, 3, 112, 5, 2),
        "progressive_vo2": (4, 4, 107, 5, 2),
        "over_under_vo2": (2, 2, 106, 5, 2),
        "hill_vo2": (3, 3, 110, 5, 2),
    }

    for family, (
        work_min,
        recover_min,
        intensity,
        max_intervals,
        base_intervals,
    ) in vo2_families.items():

        for variant in range(1, 9):
            count, endurance_minutes = interval_progression(
                variant,
                max_intervals,
                base_intervals,
                10,
            )

            steps = []

            if family == "over_under_vo2":
                # One interval consists of one under + one over.
                # This keeps the number of quality blocks capped.
                for i in range(count):
                    steps.append(
                        work(
                            work_min,
                            100,
                            f"Under {i + 1}",
                        )
                    )
                    steps.append(
                        work(
                            work_min,
                            120,
                            f"Over {i + 1}",
                        )
                    )

                    if i < count - 1:
                        steps.append(
                            recovery(
                                recover_min,
                                60,
                                f"Recovery {i + 1}",
                            )
                        )

            else:
                for i in range(count):
                    if family == "variable_vo2":
                        current_intensity = intensity + (i % 3) * 2
                        current_duration = work_min + i % 2

                        steps.append(
                            work(
                                current_duration,
                                current_intensity,
                                f"Work interval {i + 1}",
                            )
                        )

                    elif family == "ascending_vo2":
                        current_intensity = intensity + i * 3

                        steps.append(
                            work(
                                work_min,
                                current_intensity,
                                f"Ascending interval {i + 1}",
                            )
                        )

                    elif family == "descending_vo2":
                        current_intensity = intensity - i * 3

                        steps.append(
                            work(
                                work_min,
                                current_intensity,
                                f"Descending interval {i + 1}",
                            )
                        )

                    else:
                        steps.append(
                            work(
                                work_min,
                                intensity,
                                f"Work interval {i + 1}",
                            )
                        )

                    if i < count - 1:
                        steps.append(
                            recovery(
                                recover_min,
                                60,
                                f"Recovery {i + 1}",
                            )
                        )

            add_endurance(
                steps,
                endurance_minutes,
                70,
            )

            workouts.append(
                build_workout(
                    family,
                    variant,
                    "VO2max",
                    family,
                    steps,
                    ["high-intensity", "hard"],
                    12,
                    10,
                )
            )

    # ============================================================
    # RONNESTAD
    # 1 set -> 2 sets -> 3 sets.
    # Then quality volume is capped at 3 sets and endurance grows.
    # ============================================================
    for variant in range(1, 9):
        sets = min(variant, 3)
        endurance_minutes = max(0, variant - 3) * 10

        steps = []

        for s in range(sets):
            steps.extend(
                ronnestad_set(
                    s + 1,
                    work_seconds_value=30,
                    recovery_seconds_value=15,
                    reps=13,
                    intensity=115,
                )
            )

            if s < sets - 1:
                steps.append(
                    recovery(
                        3,
                        55,
                        f"Set recovery {s + 1}",
                    )
                )

        add_endurance(
            steps,
            endurance_minutes,
            70,
        )

        workouts.append(
            build_workout(
                "ronnestad_30_15",
                variant,
                "VO2max",
                "ronnestad_30_15",
                steps,
                [
                    "ronnestad",
                    "30-15",
                    "vo2max",
                    "high-intensity",
                ],
                15,
                10,
            )
        )

    # ============================================================
    # THRESHOLD
    #
    # Different threshold families have different maximum quality
    # volumes.
    #
    # 10-minute threshold:
    # 1 -> 2 -> 3 intervals -> endurance progression.
    #
    # Longer threshold intervals:
    # 2 -> 3 -> 4 -> 5 intervals -> endurance progression.
    # ============================================================
    threshold_families = {
        "traditional": (8, 98, 5, 2),
        "long_threshold": (12, 95, 4, 2),
        "cruise_intervals": (8, 96, 5, 2),
        "over_under": (5, 95, 5, 2),
        "progressive_threshold": (6, 92, 5, 2),
        "descending_threshold": (10, 98, 4, 2),
        "threshold_ladder": (5, 95, 5, 2),
        "broken_threshold": (10, 97, 4, 2),
        "double_threshold": (10, 94, 4, 2),
        "sustained_threshold": (30, 92, 1, 1),
        "sweetspot_threshold": (10, 90, 3, 1),
    }

    for family, (
        work_min,
        intensity,
        max_intervals,
        base_intervals,
    ) in threshold_families.items():

        for variant in range(1, 9):
            count, endurance_minutes = interval_progression(
                variant,
                max_intervals,
                base_intervals,
                10,
            )

            steps = []

            if family == "sustained_threshold":
                duration = work_min + (variant - 1) * 2

                steps.append(
                    work(
                        duration,
                        intensity,
                        "Sustained threshold",
                    )
                )

            elif family == "threshold_ladder":
                for i in range(count):
                    current_duration = work_min + i * 2
                    current_intensity = intensity + i

                    steps.append(
                        work(
                            current_duration,
                            current_intensity,
                            f"Ladder interval {i + 1}",
                        )
                    )

                    if i < count - 1:
                        steps.append(
                            recovery(
                                3,
                                60,
                                f"Recovery {i + 1}",
                            )
                        )

            elif family == "descending_threshold":
                for i in range(count):
                    current_duration = max(
                        5,
                        work_min - i,
                    )

                    steps.append(
                        work(
                            current_duration,
                            intensity,
                            f"Descending interval {i + 1}",
                        )
                    )

                    if i < count - 1:
                        steps.append(
                            recovery(
                                4,
                                60,
                                f"Recovery {i + 1}",
                            )
                        )

            elif family == "over_under":
                for i in range(count):
                    steps.append(
                        work(
                            2,
                            88,
                            f"Under {i + 1}",
                        )
                    )
                    steps.append(
                        work(
                            2,
                            102,
                            f"Over {i + 1}",
                        )
                    )

                    if i < count - 1:
                        steps.append(
                            recovery(
                                2,
                                60,
                                f"Recovery {i + 1}",
                            )
                        )

            else:
                for i in range(count):
                    current_duration = work_min

                    steps.append(
                        work(
                            current_duration,
                            intensity,
                            f"Threshold interval {i + 1}",
                        )
                    )

                    if i < count - 1:
                        steps.append(
                            recovery(
                                4,
                                60,
                                f"Recovery {i + 1}",
                            )
                        )

            add_endurance(
                steps,
                endurance_minutes,
                70,
            )

            workouts.append(
                build_workout(
                    family,
                    variant,
                    "Threshold",
                    family,
                    steps,
                    ["hard", "threshold"],
                    10,
                    10,
                )
            )

    # ============================================================
    # TEMPO
    # Quality volume progresses first, then endurance.
    # ============================================================
    tempo_families = {
        "short_tempo": (3, 8, 80, 5, 2),
        "tempo_bursts": (4, 6, 82, 5, 2),
        "steady_tempo": (3, 15, 82, 4, 2),
        "progressive_tempo": (3, 12, 78, 4, 2),
        "tempo_intervals": (4, 10, 84, 4, 2),
        "cadence_tempo": (4, 8, 82, 4, 2),
        "sweetspot_tempo": (3, 12, 88, 4, 2),
        "over_under_tempo": (4, 6, 84, 4, 2),
        "variable_tempo": (4, 8, 80, 4, 2),
        "tempo_ladder": (3, 8, 80, 4, 2),
        "long_tempo_blocks": (4, 20, 80, 3, 1),
        "long_steady_tempo": (3, 30, 78, 3, 1),
        "extended_tempo": (2, 40, 76, 2, 1),
    }

    for family, (
        sets,
        work_min,
        intensity,
        max_intervals,
        base_intervals,
    ) in tempo_families.items():

        for variant in range(1, 7):
            count, endurance_minutes = interval_progression(
                variant,
                max_intervals,
                base_intervals,
                10,
            )

            blocks = count
            steps = []

            for s in range(blocks):
                if family == "progressive_tempo":
                    current_intensity = intensity + s * 3
                    current_duration = work_min

                    steps.append(
                        work(
                            current_duration,
                            current_intensity,
                            f"Progressive tempo {s + 1}",
                        )
                    )

                elif family == "tempo_ladder":
                    current_duration = work_min + s * 3
                    current_intensity = intensity + s * 2

                    steps.append(
                        work(
                            current_duration,
                            current_intensity,
                            f"Tempo ladder {s + 1}",
                        )
                    )

                elif family == "over_under_tempo":
                    steps.append(
                        work(
                            work_min,
                            intensity - 4,
                            f"Under {s + 1}",
                        )
                    )
                    steps.append(
                        work(
                            work_min,
                            intensity + 8,
                            f"Over {s + 1}",
                        )
                    )

                elif family == "variable_tempo":
                    steps.append(
                        work(
                            work_min + s % 3,
                            intensity + (s % 2) * 4,
                            f"Variable tempo {s + 1}",
                        )
                    )

                else:
                    steps.append(
                        work(
                            work_min,
                            intensity,
                            f"Tempo block {s + 1}",
                        )
                    )

                if s < blocks - 1:
                    steps.append(
                        recovery(
                            3 if family != "tempo_endurance" else 5,
                            60,
                            f"Recovery {s + 1}",
                        )
                    )

            add_endurance(
                steps,
                endurance_minutes,
                70,
            )

            workouts.append(
                build_workout(
                    family,
                    variant,
                    "Tempo",
                    family,
                    steps,
                    ["moderate", "aerobic"],
                    10,
                    10,
                )
            )

    # ============================================================
    # ENDURANCE
    # These are already endurance-first workouts, so there is no
    # interval-volume progression applied here.
    # ============================================================
    endurance_families = {
        "steady_z2": (60, 70),
        "progressive_z2": (60, 68),
        "long_z2": (120, 68),
        "z2_tempo": (75, 70),
        "z2_cadence": (75, 68),
        "z2_surges": (90, 68),
        "aerobic_progression": (90, 65),
        "recovery_endurance": (45, 60),
    }

    for family, (base_min, intensity) in endurance_families.items():
        variants = 16 if family == "long_z2" else 8

        for variant in range(1, variants + 1):
            duration = (
                120 + variant * 10
                if family == "long_z2"
                else base_min
                + variant
                * (
                    15
                    if family == "steady_z2"
                    else 8
                )
            )

            if family == "z2_tempo":
                steps = [
                    work(
                        duration - 20,
                        intensity,
                        "Endurance block",
                    ),
                    work(
                        10 + variant % 3 * 5,
                        80,
                        "Tempo finish",
                    ),
                ]

            elif family == "z2_cadence":
                block_count = max(
                    3,
                    duration // 20,
                )
                steps = []

                for i in range(block_count):
                    steps.append(
                        work(
                            10,
                            intensity + 4
                            if i % 2
                            else intensity,
                            f"Cadence block {i + 1}",
                        )
                    )

                    if i < block_count - 1:
                        steps.append(
                            recovery(
                                2,
                                60,
                                f"Cadence recovery {i + 1}",
                            )
                        )

            elif family == "z2_surges":
                steps = []
                repetitions = max(
                    2,
                    duration // 45,
                )

                for i in range(repetitions):
                    steps.append(
                        work(
                            15,
                            intensity,
                            f"Endurance block {i + 1}",
                        )
                    )
                    steps.append(
                        work(
                            0.5,
                            85,
                            f"Controlled surge {i + 1}",
                        )
                    )

                    if i < repetitions - 1:
                        steps.append(
                            recovery(
                                3,
                                60,
                                f"Surge recovery {i + 1}",
                            )
                        )

            elif family == "progressive_z2":
                half = duration // 2

                steps = [
                    work(
                        half,
                        intensity,
                        "Endurance block",
                    ),
                    work(
                        duration - half,
                        intensity + 6,
                        "Progressive finish",
                    ),
                ]

            elif family == "aerobic_progression":
                third = duration // 3

                steps = [
                    work(
                        third,
                        60,
                        "Easy aerobic",
                    ),
                    work(
                        third,
                        68,
                        "Aerobic endurance",
                    ),
                    work(
                        duration - third * 2,
                        75,
                        "Progressive finish",
                    ),
                ]

            else:
                steps = [
                    work(
                        duration,
                        intensity,
                        "Endurance ride",
                    )
                ]

            workouts.append(
                build_workout(
                    family,
                    variant,
                    "Endurance",
                    family,
                    steps,
                    ["easy", "z2", "aerobic"],
                    8,
                    8,
                )
            )

    # ============================================================
    # OPENERS
    # ============================================================
    opener_variants = [
        [
            work(10, 55, "Warm-up"),
            work(3, 90, "Opener"),
            recovery(3),
            work(1, 115, "Opener"),
            recovery(3),
            work(0.5, 130, "Opener"),
            recovery(3),
            work(5, 55, "Cool-down"),
        ],
        [
            work(12, 55, "Warm-up"),
            work(2, 95, "Opener"),
            recovery(3),
            work(1, 120, "Opener"),
            recovery(3),
            work(0.5, 135, "Opener"),
            recovery(5),
            work(5, 55, "Cool-down"),
        ],
        [
            work(10, 55, "Warm-up"),
            work(5, 90, "Opener"),
            recovery(4),
            work(2, 110, "Opener"),
            recovery(4),
            work(0.5, 130, "Opener"),
            recovery(5),
            work(5, 55, "Cool-down"),
        ],
    ]

    for variant, steps in enumerate(
        opener_variants,
        1,
    ):
        workouts.append(
            build_workout(
                "openers",
                variant,
                "Openers",
                "openers",
                steps,
                [
                    "openers",
                    "race-prep",
                    "high-intensity",
                ],
                0,
                0,
            )
        )

    # ============================================================
    # RAMP TESTS
    # ============================================================
    ramp_variants = [
        [
            work(5, 50, "Warm-up"),
            work(5, 60, "Ramp"),
            work(5, 70, "Ramp"),
            work(5, 80, "Ramp"),
            work(5, 90, "Ramp"),
            work(5, 100, "Ramp"),
            work(5, 110, "Ramp"),
            work(5, 120, "Ramp"),
        ],
        [
            work(5, 50, "Warm-up"),
            work(5, 60, "Ramp"),
            work(5, 70, "Ramp"),
            work(5, 80, "Ramp"),
            work(5, 90, "Ramp"),
            work(5, 100, "Ramp"),
            work(5, 110, "Ramp"),
            work(5, 120, "Ramp"),
            work(5, 130, "Ramp"),
        ],
        [
            work(10, 50, "Warm-up"),
            work(5, 60, "Ramp"),
            work(5, 70, "Ramp"),
            work(5, 80, "Ramp"),
            work(5, 90, "Ramp"),
            work(5, 100, "Ramp"),
            work(5, 110, "Ramp"),
            work(5, 120, "Ramp"),
            work(5, 130, "Ramp"),
        ],
    ]

    for variant, steps in enumerate(
        ramp_variants,
        1,
    ):
        workouts.append(
            build_workout(
                "ramp_test",
                variant,
                "Testing",
                "ramp_test",
                steps,
                ["test", "ftp", "ramp"],
                0,
                5,
            )
        )

    # ============================================================
    # FTP TESTS
    # ============================================================
    ftp_variants = [
        [
            work(15, 55, "Warm-up"),
            work(5, 100, "FTP test"),
            recovery(5),
            work(20, 100, "FTP test"),
            work(10, 55, "Cool-down"),
        ],
        [
            work(15, 55, "Warm-up"),
            work(5, 105, "FTP test"),
            recovery(5),
            work(20, 105, "FTP test"),
            work(10, 55, "Cool-down"),
        ],
        [
            work(20, 55, "Warm-up"),
            work(5, 110, "FTP test"),
            recovery(5),
            work(20, 100, "FTP test"),
            work(10, 55, "Cool-down"),
        ],
    ]

    for variant, steps in enumerate(
        ftp_variants,
        1,
    ):
        workouts.append(
            build_workout(
                "ftp_test",
                variant,
                "Testing",
                "ftp_test",
                steps,
                ["test", "ftp", "threshold"],
                0,
                0,
            )
        )

    return workouts