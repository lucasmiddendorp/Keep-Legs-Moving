<<<<<<< Updated upstream
"""Original structured cycling workout definitions used by the library generator."""

from dataclasses import asdict, dataclass, field
from typing import Any

=======
"""Structured running workout definitions for the workout library."""
from dataclasses import asdict, dataclass, field
from typing import Any
>>>>>>> Stashed changes

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
        return sum(step.duration_seconds * step.repeat for step in self.steps)

    @property
    def target_tss(self) -> int:
<<<<<<< Updated upstream
        weighted = sum(
            step.duration_seconds * step.repeat * (step.intensity / 100) ** 2
            for step in self.steps
        )
        return round(weighted / 3600 * 100)

=======
        weighted = sum(step.duration_seconds * step.repeat * (step.intensity / 100) ** 2 for step in self.steps)
        return round(weighted / 3600 * 100)

    @property
    def interval_count(self) -> int:
        return sum(step.repeat for step in self.steps if any(word in step.name.lower() for word in ["interval", "work", "tempo", "threshold", "vo2max", "hill", "stride"]))

>>>>>>> Stashed changes
    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["steps"] = [asdict(step) for step in self.steps]
        data.update({
<<<<<<< Updated upstream
=======
            "sport": self.sport,
>>>>>>> Stashed changes
            "duration_minutes": round(self.duration_seconds / 60),
            "estimated_tss": self.target_tss,
            "target_tss": self.target_tss,
            "target_if": round(self.target_if, 2),
<<<<<<< Updated upstream
            "interval_count": sum(step.repeat for step in self.steps if "interval" in step.name.lower() or "work" in step.name.lower()),
            "interval_duration": next((step.duration_seconds for step in self.steps if "work" in step.name.lower()), 0),
            "recovery_duration": next((step.duration_seconds for step in self.steps if "recover" in step.name.lower()), 0),
            "sets": max((step.repeat for step in self.steps), default=1),
        })
        return data


=======
            "interval_count": self.interval_count,
            "interval_duration": next((step.duration_seconds for step in self.steps if any(word in step.name.lower() for word in ["work", "interval", "tempo", "threshold", "vo2max", "hill"])), 0),
            "recovery_duration": next((step.duration_seconds for step in self.steps if "recovery" in step.name.lower()), 0),
            "sets": max((step.repeat for step in self.steps), default=1)
        })
        return data

>>>>>>> Stashed changes
def _workout(workout_id, name, category, subtype, steps, tags):
    intensity_time = sum(step.duration_seconds * step.repeat * (step.intensity / 100) ** 4 for step in steps)
    duration = sum(step.duration_seconds * step.repeat for step in steps)
    target_if = (intensity_time / max(duration, 1)) ** 0.25
<<<<<<< Updated upstream
    return Workout(workout_id, name, category, subtype, tuple(steps), target_if, tuple(tags))


def warmup(minutes=10):
    return Step("Warm-up", minutes * 60, 60)


def cooldown(minutes=10):
    return Step("Cool-down", minutes * 60, 55)


def recovery(minutes, intensity=50):
    return Step("Recovery", minutes * 60, intensity)

=======
    return Workout(workout_id, name, category, subtype, tuple(steps), target_if, "Running", tuple(tags))

def warmup(minutes=5):
    return Step("Warm-up", round(minutes * 60), 65, description="Easy running with gradual progression.")

def cooldown(minutes=5):
    return Step("Cool-down", round(minutes * 60), 60, description="Easy running to bring the effort down.")

def recovery(minutes, intensity=60, name="Recovery"):
    return Step(name, round(minutes * 60), intensity, description="Easy running or very light jogging.")
>>>>>>> Stashed changes

def work(minutes, intensity, name="Work interval"):
    return Step(name, minutes * 60, intensity)

<<<<<<< Updated upstream

def build_workout(family, variant, category, subtype, work_steps, tags, warmup_minutes=10, cooldown_minutes=10):
    steps = [
        warmup(warmup_minutes + variant),
        Step(f"{family.replace('_', ' ').title()} focus", 30, 60),
        *work_steps,
        cooldown(cooldown_minutes + (variant % 3)),
    ]
    return _workout(
        f"{category.lower()}_{family}_{variant:02d}",
        f"{family.replace('_', ' ').title()} {variant:02d}",
        category,
        subtype,
        steps,
        [category.lower(), subtype, family, *tags],
    )

def generate_workouts():
    workouts = []
    vo2_families = {
        "ronnestad_30_15": lambda v: (2 + v % 3, 8 + v % 5, 30, 15, 115),
        "long_vo2": lambda v: (3 + v % 3, 3 + v % 3, 4, 4, 108),
        "four_by_four": lambda v: (3 + v % 3, 4 + v % 2, 4, 4, 112),
        "short_vo2": lambda v: (2 + v % 3, 12 + v % 5, 1, 1, 120),
        "micro_intervals": lambda v: (3 + v % 2, 10 + v % 4, 1, 1, 118),
        "ascending_vo2": lambda v: (3, 3, 3, 3, 108 + v),
        "descending_vo2": lambda v: (3, 3, 4, 4, 112 - v),
        "variable_vo2": lambda v: (3, 4, 2, 2, 110),
        "repeated_vo2_blocks": lambda v: (2 + v % 2, 4 + v % 3, 3, 3, 112),
        "progressive_vo2": lambda v: (3, 4, 4, 4, 105 + v * 2),
        "over_under_vo2": lambda v: (3, 4, 2, 2, 106),
        "hill_vo2": lambda v: (3, 5 + v % 2, 3, 3, 110),
    }
    for family, recipe in vo2_families.items():
        for variant in range(1, 7):
            sets, reps, work_min, recover_min, intensity = recipe(variant)
            steps = []
            for s in range(sets):
                if family == "ronnestad_30_15":
                    for r in range(reps):
                        steps.append(Step(f"30 sec Work {r + 1}", 30, intensity))
                        if r < reps - 1:
                            steps.append(Step(f"15 sec Recovery {r + 1}", 15, 50))
                    if s < sets - 1:
                        steps.append(recovery(3))
                elif family == "variable_vo2":
                    for r in range(reps):
                        steps.append(work(work_min + r % 3, intensity + r * 2, f"Work interval {r + 1}"))
                        if r < reps - 1:
                            steps.append(recovery(recover_min))
                elif family == "over_under_vo2":
                    steps.extend([work(2, 105, "Under"), work(2, 120, "Over")])
                    if s < sets - 1:
                        steps.append(recovery(recover_min))
                else:
                    for r in range(reps):
                        steps.append(work(work_min, intensity, f"Work interval {r + 1}"))
                        if r < reps - 1:
                            steps.append(recovery(recover_min))
                    if s < sets - 1:
                        steps.append(recovery(recover_min))
            workouts.append(build_workout(family, variant, "VO2max", family, steps, ["high-intensity", "hard"], 12, 10))

    threshold_families = {
        "traditional": (3, 8, 5, 4, 98),
        "long_threshold": (2, 3, 12, 6, 95),
        "cruise_intervals": (3, 4, 8, 3, 96),
        "over_under": (3, 5, 2, 2, 95),
        "progressive_threshold": (3, 4, 6, 4, 92),
        "descending_threshold": (3, 4, 10, 4, 98),
        "threshold_ladder": (1, 4, 5, 3, 95),
        "broken_threshold": (2, 3, 10, 5, 97),
        "double_threshold": (2, 3, 10, 4, 94),
        "sustained_threshold": (1, 1, 30, 0, 92),
        "sweetspot_threshold": (3, 4, 10, 3, 90),
    }
    for family, (sets, reps, work_min, recover_min, intensity) in threshold_families.items():
        for variant in range(1, 7):
            count = reps + variant % 2
            steps = []
            for s in range(sets):
                if family == "threshold_ladder":
                    for i in range(variant + 2):
                        steps.append(work(4 + i, intensity + i, f"Ladder interval {i + 1}"))
                        if i < variant + 1:
                            steps.append(recovery(recover_min))
                elif family == "descending_threshold":
                    for i in range(count):
                        steps.append(work(max(5, work_min - i), intensity, f"Descending interval {i + 1}"))
                        if i < count - 1:
                            steps.append(recovery(recover_min))
                elif family == "over_under":
                    steps.extend([work(2, 88, "Under"), work(2, 102, "Over")])
                    if s < sets - 1:
                        steps.append(recovery(recover_min))
                else:
                    for r in range(count):
                        steps.append(work(work_min + variant % 3, intensity, f"Threshold interval {r + 1}"))
                        if r < count - 1 and recover_min:
                            steps.append(recovery(recover_min))
                    if s < sets - 1 and recover_min:
                        steps.append(recovery(recover_min))
            workouts.append(build_workout(family, variant, "Threshold", family, steps, ["hard", "threshold"], 10, 10))

    tempo_families = {
        "steady_tempo": (2, 15, 82),
        "progressive_tempo": (3, 10, 78),
        "tempo_intervals": (4, 8, 84),
        "long_tempo_blocks": (2, 20, 80),
        "tempo_endurance": (2, 12, 80),
        "cadence_tempo": (4, 8, 82),
        "sweetspot_tempo": (3, 10, 88),
        "over_under_tempo": (4, 6, 84),
        "variable_tempo": (4, 7, 80),
        "tempo_ladder": (1, 5, 80),
    }
    for family, (sets, work_min, intensity) in tempo_families.items():
=======
def work_seconds(seconds, intensity, name="Work interval"):
    return Step(name, round(seconds), intensity)

def build_workout(family, variant, category, subtype, work_steps, tags, warmup_minutes=5, cooldown_minutes=5):
    steps = [warmup(warmup_minutes + variant % 3), *work_steps, cooldown(cooldown_minutes + variant % 2)]
    return _workout(f"{category.lower()}_{family}_{variant:02d}", f"{family.replace('_', ' ').title()} {variant:02d}", category, subtype, steps, [category.lower(), subtype, family, *tags])

def repeated_intervals(count, work_duration, work_intensity, recovery_duration, work_name="Work interval", recovery_intensity=60):
    steps = []
    for i in range(count):
        steps.append(work(work_duration, work_intensity, f"{work_name} {i + 1}"))
        if i < count - 1 and recovery_duration > 0:
            steps.append(recovery(recovery_duration, recovery_intensity))
    return steps

def repeated_intervals_seconds(count, work_duration_seconds, work_intensity, recovery_duration_seconds, work_name="Work interval", recovery_intensity=60):
    steps = []
    for i in range(count):
        steps.append(work_seconds(work_duration_seconds, work_intensity, f"{work_name} {i + 1}"))
        if i < count - 1 and recovery_duration_seconds > 0:
            steps.append(recovery(recovery_duration_seconds / 60, recovery_intensity, f"Recovery {i + 1}"))
    return steps

def strides(count=4, duration_seconds=20, recovery_seconds=60):
    steps = []
    for i in range(count):
        steps.append(Step(f"Stride {i + 1}", duration_seconds, 115, description="Fast relaxed acceleration with good running form."))
        if i < count - 1:
            steps.append(Step(f"Stride recovery {i + 1}", recovery_seconds, 60, description="Easy jogging recovery between strides."))
    return steps

def ronnestad_set(set_number, work_seconds_value=30, recovery_seconds_value=15, reps=13, intensity=115):
    steps = []
    for rep in range(reps):
        steps.append(Step(f"Ronnestad 30 sec Work {set_number}.{rep + 1}", work_seconds_value, intensity, description="High-intensity 30-second effort."))
        if rep < reps - 1:
            steps.append(Step(f"Ronnestad 15 sec Recovery {set_number}.{rep + 1}", recovery_seconds_value, 62, description="Short controlled recovery."))
    return steps

def generate_running_workouts():
    workouts = []

    easy_families = {
        "recovery_run": (30, 58),
        "easy_run": (45, 65),
        "aerobic_run": (55, 70),
        "progressive_easy": (50, 68)
    }

    for family, (base_minutes, intensity) in easy_families.items():
        for variant in range(1, 7):
            duration = base_minutes + variant * (5 if family != "recovery_run" else 3)
            if family == "progressive_easy":
                half = duration // 2
                steps = [
                    work(half, intensity - 3, "Easy running"),
                    work(duration - half, intensity + 5, "Progressive finish")
                ]
            else:
                steps = [work(duration, intensity, "Easy running")]
            workouts.append(build_workout(family, variant, "Endurance", family, steps, ["easy", "aerobic", "running"], 5 if family == "recovery_run" else 10, 5 if family == "recovery_run" else 8))

    long_families = {
        "long_run": (70, 68),
        "progressive_long_run": (75, 68),
        "long_run_finish": (80, 68)
    }

    for family, (base_minutes, intensity) in long_families.items():
        for variant in range(1, 7):
            duration = base_minutes + variant * 8
            if family == "progressive_long_run":
                steps = [
                    work(duration - 20, intensity, "Long aerobic block"),
                    work(20, 76 + variant % 3, "Progressive finish")
                ]
            elif family == "long_run_finish":
                steps = [
                    work(duration - 25, intensity, "Long aerobic block"),
                    work(15, 76, "Tempo finish"),
                    work(10, 82 + variant % 2, "Strong finish")
                ]
            else:
                steps = [work(duration, intensity, "Long run")]
            workouts.append(build_workout(family, variant, "Endurance", family, steps, ["long-run", "aerobic", "easy"], 5, 5))

    tempo_families = {
        "steady_tempo": (10, 82),
        "tempo_blocks": (12, 84),
        "progressive_tempo": (10, 80),
        "tempo_ladder": (6, 82),
        "tempo_endurance": (15, 80)
    }

    for family, (work_minutes, intensity) in tempo_families.items():
        for variant in range(1, 7):
            blocks = 2 + variant % 3
            steps = []

            if family == "tempo_ladder":
                for i in range(blocks):
                    steps.append(work(work_minutes + i * 3 + variant % 2, intensity + i * 2, f"Tempo block {i + 1}"))
                    if i < blocks - 1:
                        steps.append(recovery(2))

            elif family == "progressive_tempo":
                for i in range(blocks):
                    steps.append(work(work_minutes + variant % 2, intensity + i * 3, f"Progressive tempo {i + 1}"))
                    if i < blocks - 1:
                        steps.append(recovery(2))

            else:
                for i in range(blocks):
                    steps.append(work(work_minutes + variant % 3, intensity, f"Tempo block {i + 1}"))
                    if i < blocks - 1:
                        steps.append(recovery(3))

            workouts.append(build_workout(family, variant, "Tempo", family, steps, ["tempo", "aerobic", "moderate"], 5, 5))

    threshold_families = {
        "cruise_intervals": (3, 8, 3, 96),
        "threshold_intervals": (4, 6, 3, 100),
        "long_threshold": (3, 10, 3, 98),
        "threshold_ladder": (3, 5, 2, 98),
        "broken_threshold": (2, 15, 4, 96),
        "sustained_threshold": (1, 25, 0, 95)
    }

    for family, (reps, work_minutes, recover_minutes, intensity) in threshold_families.items():
        for variant in range(1, 7):
            count = reps + variant % 2
            steps = []

            if family == "threshold_ladder":
                for i in range(count):
                    steps.append(work(work_minutes + i * 2 + variant % 2, intensity + i, f"Threshold ladder {i + 1}"))
                    if i < count - 1:
                        steps.append(recovery(recover_minutes))

            elif family == "sustained_threshold":
                steps = [work(work_minutes + variant * 2, intensity, "Sustained threshold")]

            else:
                steps = repeated_intervals(count, work_minutes + variant % 2, intensity, recover_minutes, "Threshold interval", 60)

            workouts.append(build_workout(family, variant, "Threshold", family, steps, ["threshold", "hard", "race-specific"], 5, 5))

    norwegian = {
        "norwegian_4x4": (4, 4, 3, 105),
        "norwegian_5x6": (5, 6, 2, 95),
        "norwegian_3x10": (3, 10, 2, 94),
        "norwegian_4x8": (4, 8, 2, 96),
        "norwegian_double_threshold": (2, 15, 3, 94),
        "norwegian_cruise": (5, 8, 1, 96)
    }

    for family, (reps, work_minutes, recover_minutes, intensity) in norwegian.items():
>>>>>>> Stashed changes
        for variant in range(1, 7):
            count = reps + (variant % 2 if family in {"norwegian_5x6", "norwegian_cruise"} else 0)
            steps = []
<<<<<<< Updated upstream
            for i in range(blocks):
                current = intensity + i if family in {"progressive_tempo", "tempo_ladder"} else intensity
                if family == "over_under_tempo":
                    steps.extend([work(work_min, current - 4, "Under"), work(work_min, current + 8, "Over")])
                elif family == "variable_tempo":
                    steps.append(work(work_min + i % 3, current, "Tempo block"))
                else:
                    steps.append(work(work_min + variant % 3, current, "Tempo block"))
                if i < blocks - 1:
                    steps.append(recovery(3 if family != "tempo_endurance" else 5))
            workouts.append(build_workout(family, variant, "Tempo", family, steps, ["moderate", "aerobic"], 10, 10))

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
            if family == "long_z2":
                duration = 120 + variant * 10
            elif family == "steady_z2":
                duration = base_min + variant * 15
            else:
                duration = base_min + variant * 8
            if family == "z2_tempo":
                steps = [work(duration - 20, intensity, "Endurance block"), work(10 + variant % 3 * 5, 80, "Tempo finish")]
            elif family == "z2_cadence":
                block_count = max(3, duration // 20)
                steps = [work(10, intensity + 4 if i % 2 else intensity, "Cadence block") for i in range(block_count)]
            elif family == "z2_surges":
                steps = [work(15, intensity, "Endurance block"), work(30 / 60, 85, "Controlled surge")] * max(2, duration // 45)
            else:
                steps = [work(duration, intensity, "Endurance ride")]
            workouts.append(build_workout(family, variant, "Endurance", family, steps, ["easy", "z2", "aerobic"], 8, 8))

    special_workouts = []

    opener_variants = [
        [work(10, 55, "Warm-up"), work(3, 90, "Opener"), recovery(3), work(1, 115, "Opener"), recovery(3), work(0.5, 130, "Opener"), recovery(3), work(5, 55, "Cool-down")],
        [work(12, 55, "Warm-up"), work(2, 95, "Opener"), recovery(3), work(1, 120, "Opener"), recovery(3), work(0.5, 135, "Opener"), recovery(5), work(5, 55, "Cool-down")],
        [work(10, 55, "Warm-up"), work(5, 90, "Opener"), recovery(4), work(2, 110, "Opener"), recovery(4), work(0.5, 130, "Opener"), recovery(5), work(5, 55, "Cool-down")],
    ]
    for variant, steps in enumerate(opener_variants, 1):
        special_workouts.append(build_workout("openers", variant, "Openers", "openers", steps, ["openers", "race-prep", "high-intensity"], 8, 8))

    ramp_variants = [
        [work(5, 50, "Warm-up"), work(5, 60, "Ramp"), work(5, 70, "Ramp"), work(5, 80, "Ramp"), work(5, 90, "Ramp"), work(5, 100, "Ramp"), work(5, 110, "Ramp"), work(5, 120, "Ramp")],
        [work(5, 50, "Warm-up"), work(5, 60, "Ramp"), work(5, 70, "Ramp"), work(5, 80, "Ramp"), work(5, 90, "Ramp"), work(5, 100, "Ramp"), work(5, 110, "Ramp"), work(5, 120, "Ramp"), work(5, 130, "Ramp")],
        [work(10, 50, "Warm-up"), work(5, 60, "Ramp"), work(5, 70, "Ramp"), work(5, 80, "Ramp"), work(5, 90, "Ramp"), work(5, 100, "Ramp"), work(5, 110, "Ramp"), work(5, 120, "Ramp"), work(5, 130, "Ramp")],
    ]
    for variant, steps in enumerate(ramp_variants, 1):
        special_workouts.append(build_workout("ramp_test", variant, "Testing", "ramp_test", steps, ["test", "ftp", "ramp"], 10, 10))

    ftp_variants = [
        [work(15, 55, "Warm-up"), work(5, 100, "FTP test"), recovery(5), work(20, 100, "FTP test"), work(10, 55, "Cool-down")],
        [work(15, 55, "Warm-up"), work(5, 105, "FTP test"), recovery(5), work(20, 105, "FTP test"), work(10, 55, "Cool-down")],
        [work(20, 55, "Warm-up"), work(5, 110, "FTP test"), recovery(5), work(20, 100, "FTP test"), work(10, 55, "Cool-down")],
    ]
    for variant, steps in enumerate(ftp_variants, 1):
        special_workouts.append(build_workout("ftp_test", variant, "Testing", "ftp_test", steps, ["test", "ftp", "threshold"], 10, 10))

    workouts.extend(special_workouts)
=======

            for i in range(count):
                current = intensity + (variant - 1) % 3 if family in {"norwegian_4x4", "norwegian_4x8"} else intensity
                steps.append(work(work_minutes + (variant % 2 if family == "norwegian_3x10" else 0), current, f"Norwegian interval {i + 1}"))
                if i < count - 1:
                    steps.append(recovery(recover_minutes, 62, f"Norwegian recovery {i + 1}"))

            workouts.append(build_workout(family, variant, "Threshold", family, steps, ["norwegian", "threshold", "controlled", "running"], 5, 5))

    # =========================================================
    # Rønnestad 30-15
    # =========================================================
    # Every set is ALWAYS 13 repetitions:
    # 13 x (30 sec work + 15 sec recovery), with no recovery after
    # the final 15-second recovery of the set.
    # Multiple sets are separated by 3 minutes of easy recovery.
    # Variants progressively increase the number of sets:
    # 1 set for variants 1-2, 2 sets for variants 3-4, 3 sets for variants 5-6.
    # =========================================================

    for variant in range(1, 7):
        current_sets = min(3, 1 + (variant - 1) // 2)
        steps = []

        for set_number in range(1, current_sets + 1):
            set_steps = ronnestad_set(
                set_number=set_number,
                work_seconds_value=30,
                recovery_seconds_value=15,
                reps=13,
                intensity=115 + variant % 3
            )
            steps.extend(set_steps)

            if set_number < current_sets:
                steps.append(recovery(3, 60, f"Ronnestad set recovery {set_number}"))

        workouts.append(build_workout("ronnestad_30_15", variant, "VO2max", "ronnestad_30_15", steps, ["ronnestad", "30-15", "vo2max", "high-intensity"], 5, 5))

    vo2_families = {
        "four_by_four": (4, 4, 3, 108),
        "five_by_three": (5, 3, 2, 110),
        "six_by_two": (6, 2, 2, 112),
        "short_vo2": (10, 1, 1, 118),
        "long_vo2": (4, 5, 3, 108),
        "vo2_ladder": (5, 2, 2, 106)
    }

    for family, (reps, work_minutes, recover_minutes, intensity) in vo2_families.items():
        for variant in range(1, 7):
            count = reps + variant % 2
            steps = []

            for i in range(count):
                current = intensity + (i if family == "vo2_ladder" else 0) + variant % 2
                steps.append(work(work_minutes, current, f"VO2max interval {i + 1}"))
                if i < count - 1:
                    steps.append(recovery(recover_minutes, 62, f"VO2max recovery {i + 1}"))

            workouts.append(build_workout(family, variant, "VO2max", family, steps, ["vo2max", "high-intensity", "hard"], 5, 5))

    hill_families = {
        "hill_repeats": (8, 1, 2, 108),
        "long_hills": (6, 3, 3, 105),
        "hill_sprints": (10, 0.5, 2, 120)
    }

    for family, (reps, work_minutes, recover_minutes, intensity) in hill_families.items():
        for variant in range(1, 7):
            count = reps + variant % 2
            steps = []

            for i in range(count):
                steps.append(work(work_minutes, intensity + variant % 2, f"Hill repeat {i + 1}"))
                if i < count - 1:
                    steps.append(recovery(recover_minutes, 60, f"Hill recovery {i + 1}"))

            category = "VO2max" if intensity >= 108 else "Threshold"
            workouts.append(build_workout(family, variant, category, family, steps, ["hills", "strength", "high-intensity"], 5, 5))

    for variant in range(1, 7):
        steps = [
            work(20 + variant * 5, 65, "Easy running"),
            *strides(4 + variant % 3, 20 + variant % 2 * 5, 60),
            work(10 + variant, 68, "Easy running")
        ]
        workouts.append(build_workout("strides", variant, "Anaerobic", "strides", steps, ["strides", "speed", "running-form"]))

>>>>>>> Stashed changes
    return workouts