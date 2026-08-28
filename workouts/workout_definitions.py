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
    steps: tuple[Step, ...]
    target_if: float
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def duration_seconds(self) -> int:
        return sum(step.duration_seconds * step.repeat for step in self.steps)

    @property
    def target_tss(self) -> int:
        weighted = sum(
            step.duration_seconds * step.repeat * (step.intensity / 100) ** 2
            for step in self.steps
        )
        return round(weighted / 3600 * 100)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["steps"] = [asdict(step) for step in self.steps]
        data.update({
            "duration_minutes": round(self.duration_seconds / 60),
            "estimated_tss": self.target_tss,
            "target_tss": self.target_tss,
            "target_if": round(self.target_if, 2),
            "interval_count": sum(step.repeat for step in self.steps if "interval" in step.name.lower() or "work" in step.name.lower()),
            "interval_duration": next((step.duration_seconds for step in self.steps if "work" in step.name.lower()), 0),
            "recovery_duration": next((step.duration_seconds for step in self.steps if "recover" in step.name.lower()), 0),
            "sets": max((step.repeat for step in self.steps), default=1),
        })
        return data


def _workout(workout_id, name, category, subtype, steps, tags):
    intensity_time = sum(step.duration_seconds * step.repeat * (step.intensity / 100) ** 4 for step in steps)
    duration = sum(step.duration_seconds * step.repeat for step in steps)
    target_if = (intensity_time / max(duration, 1)) ** 0.25
    return Workout(workout_id, name, category, subtype, tuple(steps), target_if, tuple(tags))


def warmup(minutes=10):
    return Step("Warm-up", minutes * 60, 60)


def cooldown(minutes=10):
    return Step("Cool-down", minutes * 60, 55)


def recovery(minutes, intensity=50):
    return Step("Recovery", minutes * 60, intensity)


def work(minutes, intensity, name="Work interval"):
    return Step(name, minutes * 60, intensity)


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
            if family == "variable_vo2":
                intervals = [Step(f"Work interval {i + 1}", (work_min + i % 3) * 60, intensity + i * 2) for i in range(reps)]
                recoveries = [recovery(recover_min) for _ in range(reps - 1)]
                block = [item for pair in zip(intervals, recoveries) for item in pair][:-1]
            elif family == "over_under_vo2":
                block = [work(2, 105, "Under"), work(2, 120, "Over"), recovery(recover_min)]
                reps = 1
            else:
                block = [work(work_min, intensity), recovery(recover_min)]
            steps = []
            for _ in range(sets):
                steps.extend(block)
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
            count = reps + (variant % 2)
            if family == "threshold_ladder":
                block = []
                for i in range(variant + 2):
                    block.append(work(4 + i, intensity + i, f"Ladder interval {i + 1}"))
                    if i < variant + 1:
                        block.append(recovery(recover_min))
            elif family == "descending_threshold":
                block = []
                for i in range(count):
                    block.append(work(max(5, work_min - i), intensity, f"Descending interval {i + 1}"))
                    if i < count - 1:
                        block.append(recovery(recover_min))
            elif family == "over_under":
                block = [work(2, 88, "Under"), work(2, 102, "Over"), recovery(recover_min)]
            else:
                block = [work(work_min + variant % 3, intensity), recovery(recover_min)] if recover_min else [work(work_min + variant % 3, intensity)]
            workouts.append(build_workout(family, variant, "Threshold", family, block * sets, ["hard", "threshold"], 10, 10))

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
            block = []
            for index in range(sets + variant % 2):
                current = intensity + (index if family in {"progressive_tempo", "tempo_ladder"} else 0)
                block.append(work(work_min + variant % 3, current, "Tempo block"))
                if index < sets - 1:
                    block.append(recovery(3 if family != "tempo_endurance" else 5, 60))
            workouts.append(build_workout(family, variant, "Tempo", family, block, ["moderate", "aerobic"], 10, 10))

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
        for variant in range(1, 9):
            duration = base_min + variant * (15 if family in {"long_z2", "steady_z2"} else 8)
            if family == "z2_tempo":
                steps = [work(duration - 20, intensity, "Endurance block"), work(10 + variant % 3 * 5, 80, "Tempo finish")]
            elif family == "z2_cadence":
                steps = [work(10, intensity + 4 if i % 2 else intensity, "Cadence block") for i in range(max(3, duration // 20))]
            elif family == "z2_surges":
                steps = [work(15, intensity, "Endurance block"), work(30, 85, "Controlled surge")] * max(2, duration // 45)
            else:
                steps = [work(duration, intensity, "Endurance ride")]
            workouts.append(build_workout(family, variant, "Endurance", family, steps, ["easy", "z2", "aerobic"], 8, 8))
    return workouts
