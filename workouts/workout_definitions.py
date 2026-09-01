"""Original structured cycling workout definitions used by the library generator."""
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
        weighted = sum(step.duration_seconds * step.repeat * (step.intensity / 100) ** 2 for step in self.steps)
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
            "interval_count": sum(step.repeat for step in self.steps if "interval" in step.name.lower() or "work" in step.name.lower()),
            "interval_duration": next((step.duration_seconds for step in self.steps if "work" in step.name.lower() or "interval" in step.name.lower()), 0),
            "recovery_duration": next((step.duration_seconds for step in self.steps if "recover" in step.name.lower()), 0),
            "sets": max((step.repeat for step in self.steps), default=1),
        })
        return data
def _workout(workout_id, name, category, subtype, sport, steps, tags):
    intensity_time = sum(step.duration_seconds * step.repeat * (step.intensity / 100) ** 4 for step in steps)
    duration = sum(step.duration_seconds * step.repeat for step in steps)
    target_if = (intensity_time / max(duration, 1)) ** 0.25
    return Workout(workout_id, name, category, subtype, sport, tuple(steps), target_if, tuple(tags))
def warmup(minutes=10):
    return Step("Warm-up", round(minutes * 60), 60, description="Progressive warm-up.")
def cooldown(minutes=10):
    return Step("Cool-down", round(minutes * 60), 55, description="Easy riding to finish the workout.")
def recovery(minutes, intensity=50, name="Recovery"):
    return Step(name, round(minutes * 60), intensity, description="Easy recovery riding.")
def work(minutes, intensity, name="Work interval"):
    return Step(name, round(minutes * 60), intensity)
def work_seconds(seconds, intensity, name="Work interval"):
    return Step(name, round(seconds), intensity)
def build_workout(family, variant, category, subtype, work_steps, tags, warmup_minutes=10, cooldown_minutes=10):
    steps = [warmup(warmup_minutes + variant % 3), *work_steps, cooldown(cooldown_minutes + variant % 2)]
    return _workout(
        f"cycling_{category.lower()}_{family}_{variant:02d}",
        f"{family.replace('_', ' ').title()} {variant:02d}",
        category,
        subtype,
        "Cycling",
        steps,
        ["cycling", category.lower(), subtype, family, *tags],
    )
def repeated_intervals(count, work_duration, work_intensity, recovery_duration, work_name="Work interval", recovery_intensity=60):
    steps = []
    for i in range(count):
        steps.append(work(work_duration, work_intensity, f"{work_name} {i + 1}"))
        if i < count - 1 and recovery_duration > 0:
            steps.append(recovery(recovery_duration, recovery_intensity, f"Recovery {i + 1}"))
    return steps
def repeated_intervals_seconds(count, work_duration_seconds, work_intensity, recovery_duration_seconds, work_name="Work interval", recovery_intensity=60):
    steps = []
    for i in range(count):
        steps.append(work_seconds(work_duration_seconds, work_intensity, f"{work_name} {i + 1}"))
        if i < count - 1 and recovery_duration_seconds > 0:
            steps.append(Step(f"Recovery {i + 1}", round(recovery_duration_seconds), recovery_intensity))
    return steps
def ronnestad_set(set_number, work_seconds_value=30, recovery_seconds_value=15, reps=13, intensity=115):
    steps = []
    for rep in range(reps):
        steps.append(Step(
            f"Ronnestad 30 sec Work {set_number}.{rep + 1}",
            work_seconds_value,
            intensity,
            description="High-intensity 30-second effort."
        ))
        if rep < reps - 1:
            steps.append(Step(
                f"Ronnestad 15 sec Recovery {set_number}.{rep + 1}",
                recovery_seconds_value,
                62,
                description="Short controlled recovery."
            ))
    return steps
def generate_workouts():
    workouts = []
    vo2_families = {
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
                for r in range(reps):
                    if family == "variable_vo2":
                        current_intensity = intensity + r * 2
                        current_duration = work_min + r % 3
                        steps.append(work(current_duration, current_intensity, f"Work interval {s + 1}.{r + 1}"))
                    elif family == "over_under_vo2":
                        steps.append(work(2, 100, f"Under {s + 1}.{r + 1}"))
                        steps.append(work(2, 120, f"Over {s + 1}.{r + 1}"))
                    else:
                        steps.append(work(work_min, intensity, f"Work interval {s + 1}.{r + 1}"))
                    if r < reps - 1:
                        steps.append(recovery(recover_min, 60, f"Recovery {s + 1}.{r + 1}"))
                if s < sets - 1:
                    steps.append(recovery(3, 55, f"Set recovery {s + 1}"))
            workouts.append(build_workout(family, variant, "VO2max", family, steps, ["high-intensity", "hard"], 12, 10))
    ronnestad_variants = {
        1: 1,
        2: 1,
        3: 1,
        4: 2,
        5: 2,
        6: 3,
    }
    for variant, sets in ronnestad_variants.items():
        steps = []
        for s in range(sets):
            steps.extend(ronnestad_set(s + 1, 30, 15, 13, 115 + variant % 3))
            if s < sets - 1:
                steps.append(recovery(3, 55, f"Set recovery {s + 1}"))
        workouts.append(build_workout("ronnestad_30_15", variant, "VO2max", "ronnestad_30_15", steps, ["ronnestad", "30-15", "vo2max", "high-intensity"], 15, 10))
    threshold_families = {
        "traditional": (3, 8, 5, 98),
        "long_threshold": (2, 3, 12, 95),
        "cruise_intervals": (3, 4, 8, 96),
        "over_under": (3, 5, 2, 95),
        "progressive_threshold": (3, 4, 6, 92),
        "descending_threshold": (3, 4, 10, 98),
        "threshold_ladder": (1, 4, 5, 95),
        "broken_threshold": (2, 3, 10, 97),
        "double_threshold": (2, 3, 10, 94),
        "sustained_threshold": (1, 1, 30, 92),
        "sweetspot_threshold": (3, 4, 10, 90),
    }
    for family, (sets, reps, work_min, intensity) in threshold_families.items():
        for variant in range(1, 7):
            count = reps + variant % 2
            steps = []
            for s in range(sets):
                if family == "threshold_ladder":
                    for i in range(variant + 2):
                        steps.append(work(4 + i, intensity + i, f"Ladder interval {s + 1}.{i + 1}"))
                        if i < variant + 1:
                            steps.append(recovery(3, 60, f"Recovery {s + 1}.{i + 1}"))
                elif family == "descending_threshold":
                    for i in range(count):
                        steps.append(work(max(5, work_min - i), intensity, f"Descending interval {s + 1}.{i + 1}"))
                        if i < count - 1:
                            steps.append(recovery(4, 60, f"Recovery {s + 1}.{i + 1}"))
                elif family == "over_under":
                    for i in range(count):
                        steps.append(work(2, 88, f"Under {s + 1}.{i + 1}"))
                        steps.append(work(2, 102, f"Over {s + 1}.{i + 1}"))
                        if i < count - 1:
                            steps.append(recovery(2, 60, f"Recovery {s + 1}.{i + 1}"))
                elif family == "sustained_threshold":
                    steps.append(work(work_min + variant * 2, intensity, f"Sustained threshold {s + 1}"))
                else:
                    for r in range(count):
                        steps.append(work(work_min + variant % 3, intensity, f"Threshold interval {s + 1}.{r + 1}"))
                        if r < count - 1:
                            steps.append(recovery(4, 60, f"Recovery {s + 1}.{r + 1}"))
                if s < sets - 1:
                    steps.append(recovery(5, 55, f"Set recovery {s + 1}"))
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
        for variant in range(1, 7):
            blocks = sets + variant % 2
            steps = []
            for s in range(blocks):
                if family == "progressive_tempo":
                    current_intensity = intensity + s * 3
                    current_duration = work_min + variant % 2
                    steps.append(work(current_duration, current_intensity, f"Progressive tempo {s + 1}"))
                elif family == "tempo_ladder":
                    current_duration = work_min + s * 3
                    current_intensity = intensity + s * 2
                    steps.append(work(current_duration, current_intensity, f"Tempo ladder {s + 1}"))
                elif family == "over_under_tempo":
                    steps.append(work(work_min, intensity - 4, f"Under {s + 1}"))
                    steps.append(work(work_min, intensity + 8, f"Over {s + 1}"))
                elif family == "variable_tempo":
                    steps.append(work(work_min + s % 3, intensity + (s % 2) * 4, f"Variable tempo {s + 1}"))
                else:
                    steps.append(work(work_min + variant % 3, intensity, f"Tempo block {s + 1}"))
                if s < blocks - 1:
                    steps.append(recovery(3 if family != "tempo_endurance" else 5, 60, f"Recovery {s + 1}"))
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
            duration = 120 + variant * 10 if family == "long_z2" else base_min + variant * (15 if family == "steady_z2" else 8)
            if family == "z2_tempo":
                steps = [work(duration - 20, intensity, "Endurance block"), work(10 + variant % 3 * 5, 80, "Tempo finish")]
            elif family == "z2_cadence":
                block_count = max(3, duration // 20)
                steps = []
                for i in range(block_count):
                    steps.append(work(10, intensity + 4 if i % 2 else intensity, f"Cadence block {i + 1}"))
                    if i < block_count - 1:
                        steps.append(recovery(2, 60, f"Cadence recovery {i + 1}"))
            elif family == "z2_surges":
                steps = []
                repetitions = max(2, duration // 45)
                for i in range(repetitions):
                    steps.append(work(15, intensity, f"Endurance block {i + 1}"))
                    steps.append(work(0.5, 85, f"Controlled surge {i + 1}"))
                    if i < repetitions - 1:
                        steps.append(recovery(3, 60, f"Surge recovery {i + 1}"))
            elif family == "progressive_z2":
                half = duration // 2
                steps = [work(half, intensity, "Endurance block"), work(duration - half, intensity + 6, "Progressive finish")]
            elif family == "aerobic_progression":
                third = duration // 3
                steps = [work(third, 60, "Easy aerobic"), work(third, 68, "Aerobic endurance"), work(duration - third * 2, 75, "Progressive finish")]
            else:
                steps = [work(duration, intensity, "Endurance ride")]
            workouts.append(build_workout(family, variant, "Endurance", family, steps, ["easy", "z2", "aerobic"], 8, 8))
    opener_variants = [
        [work(10, 55, "Warm-up"), work(3, 90, "Opener"), recovery(3), work(1, 115, "Opener"), recovery(3), work(0.5, 130, "Opener"), recovery(3), work(5, 55, "Cool-down")],
        [work(12, 55, "Warm-up"), work(2, 95, "Opener"), recovery(3), work(1, 120, "Opener"), recovery(3), work(0.5, 135, "Opener"), recovery(5), work(5, 55, "Cool-down")],
        [work(10, 55, "Warm-up"), work(5, 90, "Opener"), recovery(4), work(2, 110, "Opener"), recovery(4), work(0.5, 130, "Opener"), recovery(5), work(5, 55, "Cool-down")],
    ]
    for variant, steps in enumerate(opener_variants, 1):
        workouts.append(build_workout("openers", variant, "Openers", "openers", steps, ["openers", "race-prep", "high-intensity"], 0, 0))
    ramp_variants = [
        [work(5, 50, "Warm-up"), work(5, 60, "Ramp"), work(5, 70, "Ramp"), work(5, 80, "Ramp"), work(5, 90, "Ramp"), work(5, 100, "Ramp"), work(5, 110, "Ramp"), work(5, 120, "Ramp")],
        [work(5, 50, "Warm-up"), work(5, 60, "Ramp"), work(5, 70, "Ramp"), work(5, 80, "Ramp"), work(5, 90, "Ramp"), work(5, 100, "Ramp"), work(5, 110, "Ramp"), work(5, 120, "Ramp"), work(5, 130, "Ramp")],
        [work(10, 50, "Warm-up"), work(5, 60, "Ramp"), work(5, 70, "Ramp"), work(5, 80, "Ramp"), work(5, 90, "Ramp"), work(5, 100, "Ramp"), work(5, 110, "Ramp"), work(5, 120, "Ramp"), work(5, 130, "Ramp")],
    ]
    for variant, steps in enumerate(ramp_variants, 1):
        workouts.append(build_workout("ramp_test", variant, "Testing", "ramp_test", steps, ["test", "ftp", "ramp"], 0, 0))
    ftp_variants = [
        [work(15, 55, "Warm-up"), work(5, 100, "FTP test"), recovery(5), work(20, 100, "FTP test"), work(10, 55, "Cool-down")],
        [work(15, 55, "Warm-up"), work(5, 105, "FTP test"), recovery(5), work(20, 105, "FTP test"), work(10, 55, "Cool-down")],
        [work(20, 55, "Warm-up"), work(5, 110, "FTP test"), recovery(5), work(20, 100, "FTP test"), work(10, 55, "Cool-down")],
    ]
    for variant, steps in enumerate(ftp_variants, 1):
        workouts.append(build_workout("ftp_test", variant, "Testing", "ftp_test", steps, ["test", "ftp", "threshold"], 0, 0))
    return workouts