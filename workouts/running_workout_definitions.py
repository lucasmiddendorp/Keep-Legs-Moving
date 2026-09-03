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
            "interval_duration": next((step.duration_seconds for step in self.steps if "work" in step.name.lower()), 0),
            "recovery_duration": next((step.duration_seconds for step in self.steps if "recover" in step.name.lower()), 0),
            "sets": max((step.repeat for step in self.steps), default=1),
        })
        return data

def _workout(workout_id, name, category, subtype, steps, tags):
    intensity_time = sum(step.duration_seconds * step.repeat * (step.intensity / 100) ** 4 for step in steps)
    duration = sum(step.duration_seconds * step.repeat for step in steps)
    target_if = (intensity_time / max(duration, 1)) ** 0.25
    return Workout(workout_id, name, category, subtype, tuple(steps), target_if, "Running", tuple(tags))

def warmup(minutes=5):
    return Step("Warm-up", minutes * 60, 70, description="Easy running with gradual progression.")

def cooldown(minutes=5):
    return Step("Cool-down", minutes * 60, 65, description="Easy running to bring the effort down.")

def recovery(minutes, intensity=65):
    return Step("Recovery", round(minutes * 60), intensity, description="Easy running or very light jogging.")

def work(minutes, intensity, name="Work interval"):
    return Step(name, round(minutes * 60), intensity)

def build_workout(family, variant, category, subtype, work_steps, tags, warmup_minutes=5, cooldown_minutes=5):
    steps = [warmup(warmup_minutes + variant % 3), *work_steps, cooldown(cooldown_minutes + variant % 2)]
    return _workout(f"{category.lower()}_{family}_{variant:02d}", f"{family.replace('_', ' ').title()} {variant:02d}", category, subtype, steps, [category.lower(), subtype, family, *tags])

def strides(count=4, duration_seconds=20, recovery_seconds=60):
    steps = []
    for i in range(count):
        steps.append(Step(f"Stride {i + 1}", duration_seconds, 115, description="Fast relaxed acceleration with good running form."))
        if i < count - 1:
            steps.append(Step(f"Stride recovery {i + 1}", recovery_seconds, 65))
    return steps

def generate_running_workouts():
    workouts = []
    easy_families = {
        "recovery_run": (10, 68),
        "easy_run": (15, 75),
        "aerobic_run": (30, 75),
        "progressive_easy": (30, 74),
    }
    for family, (base_minutes, intensity) in easy_families.items():
        for variant in range(1, 7):
            duration = base_minutes + variant * (3 if family != "recovery_run" else 4)
            if family == "progressive_easy":
                half = duration // 2
                steps = [
                    work(half, intensity - 3, "Easy running"),
                    work(duration - half, intensity + 5, "Progressive finish"),
                ]
            else:
                steps = [work(duration, intensity, "Easy running")]
            workouts.append(build_workout(
                family,
                variant,
                "Endurance",
                family,
                steps,
                ["easy", "aerobic", "running"],
                5,
                5
            ))

    long_families = {
        "long_run": (75, 72),
        "progressive_long_run": (90, 72),
        "long_run_finish": (105, 72),
        "extended_long_run": (120, 72),
        "ultra_long_run": (180, 72),
    }
    for family, (base_minutes, intensity) in long_families.items():
        for variant in range(1, 7):
            if family == "extended_long_run":
                duration = base_minutes + variant * 15
            elif family == "ultra_long_run":
                duration = base_minutes + variant * 20
            else:
                duration = base_minutes + variant * 10
            if family == "progressive_long_run":
                steps = [
                    work(duration - 20, intensity, "Long aerobic block"),
                    work(20, 82 + variant % 3, "Progressive finish"),
                ]
            elif family == "long_run_finish":
                steps = [
                    work(duration - 25, intensity, "Long aerobic block"),
                    work(15, 84, "Tempo finish"),
                    work(10, 90 + variant % 2, "Strong finish"),
                ]
            else:
                steps = [work(duration, intensity, "Long run")]
            workouts.append(build_workout(
                family,
                variant,
                "Endurance",
                family,
                steps,
                ["long-run", "aerobic", "easy"],
                5,
                5,
            ))

    tempo_families = {
        "steady_tempo": (10, 87),
        "tempo_blocks": (12, 90),
        "progressive_tempo": (10, 87),
        "tempo_ladder": (6, 87),
        "tempo_endurance": (15, 85),
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
            workouts.append(build_workout(
                family,
                variant,
                "Tempo",
                family,
                steps,
                ["tempo", "aerobic", "moderate"],
                5,
                5,
            ))

    threshold_families = {
        "cruise_intervals": (3, 8, 3, 98),
        "threshold_intervals": (4, 6, 3, 102),
        "long_threshold": (3, 10, 3, 100),
        "threshold_ladder": (3, 5, 2, 98),
        "broken_threshold": (2, 15, 4, 97),
        "sustained_threshold": (1, 25, 0, 96),
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
                for i in range(count):
                    steps.append(work(work_minutes + variant % 2, intensity, f"Threshold interval {i + 1}"))
                    if i < count - 1 and recover_minutes:
                        steps.append(recovery(recover_minutes))
            workouts.append(build_workout(
                family,
                variant,
                "Threshold",
                family,
                steps,
                ["threshold", "hard", "race-specific"],
                5,
                5,
            ))

    norwegian = {"norwegian_4": (1, 4, 3, 115)}
    for family, (reps, work_minutes, recover_minutes, intensity) in norwegian.items():
        for variant in range(1, 6):
            count = variant
            steps = []

            for i in range(count):
                steps.append(work(
                    work_minutes,
                    intensity,
                    f"Norwegian interval {i + 1}",
                ))

                if i < count - 1:
                    steps.append(recovery(recover_minutes, 65))

            category = intensity_to_zone(intensity)
            workouts.append(build_workout(
                family,
                variant,
                category,
                family,
                steps,
                ["norwegian", "vo2max", "controlled", "running"],
                5,
                5,
            ))

    ronnestad = {"ronnestad_30_15": (30, 15, 115)}
    for family, (work_seconds, recover_seconds, intensity) in ronnestad.items():
        for variant in range(1, 7):
            current_sets = min(3, 1 + (variant - 1) // 2)
            steps = []
            for s in range(current_sets):
                for r in range(13):
                    steps.append(Step(
                        f"Ronnestad 30 sec Work {s + 1}.{r + 1}",
                        work_seconds,
                        intensity + variant % 3,
                    ))
                    if r < 12:
                        steps.append(Step(
                            f"Ronnestad 15 sec Recovery {s + 1}.{r + 1}",
                            recover_seconds,
                            65,
                        ))
                if s < current_sets - 1:
                    steps.append(recovery(3, 65))
            workouts.append(build_workout(
                family,
                variant,
                "VO2max",
                family,
                steps,
                ["ronnestad", "30-15", "vo2max", "high-intensity"],
                5,
                5,
            ))

    test = {"6_min_run": (360, 120)}

    for family, (duration_seconds, intensity) in test.items():
        for variant in range(1, 2):
            steps = [Step("Test Warmup",30,120),
                recovery(2, 65),
                Step("6 Minute Running Test",duration_seconds,intensity),
            ]

            workouts.append(build_workout(
                family,
                variant,
                "TEST",
                family,
                steps,
                ["test", "6-minute", "running", "vo2max"],
                5,
                5,
            ))

    vo2_families = {
        "four_by_four": (4, 4, 3, 108),
        "five_by_three": (5, 3, 2, 110),
        "six_by_two": (6, 2, 2, 112),
        "short_vo2": (10, 1, 1, 116),
        "long_vo2": (4, 5, 3, 108),
        "vo2_ladder": (5, 2, 2, 107),
    }
    for family, (reps, work_minutes, recover_minutes, intensity) in vo2_families.items():
        for variant in range(1, 7):
            count = reps + variant % 2
            steps = []
            for i in range(count):
                current = intensity + (i if family == "vo2_ladder" else 0) + variant % 2
                steps.append(work(work_minutes, current, f"VO2max interval {i + 1}"))
                if i < count - 1:
                    steps.append(recovery(recover_minutes, 65))
            workouts.append(build_workout(
                family,
                variant,
                "VO2max",
                family,
                steps,
                ["vo2max", "high-intensity", "hard"],
                5,
                5,
            ))

    hill_families = {
        "hill_repeats": (8, 1, 2, 108),
        "long_hills": (6, 3, 3, 108),
        "hill_sprints": (10, 0.5, 2, 125),
    }
    for family, (reps, work_minutes, recover_minutes, intensity) in hill_families.items():
        for variant in range(1, 7):
            count = reps + variant % 2
            steps = []
            for i in range(count):
                current_intensity = intensity + variant % 2
                steps.append(work(work_minutes, current_intensity, f"Hill repeat {i + 1}"))
                if i < count - 1:
                    steps.append(recovery(recover_minutes, 65))
            category = intensity_to_zone(current_intensity)
            workouts.append(build_workout(
                family,
                variant,
                category,
                family,
                steps,
                ["hills", "strength", "high-intensity"],
                5,
                5,
            ))

    opener_families = {
        "short_openers": (4, 1, 2, 102),
        "race_openers": (5, 1, 2, 108),
        "progressive_openers": (4, 1, 2, 98),
        "speed_openers": (6, 0.5, 1.5, 115),
    }
    for family, (reps, work_minutes, recover_minutes, intensity) in opener_families.items():
        for variant in range(1, 7):
            count = reps + variant % 2
            steps = []
            for i in range(count):
                if family == "progressive_openers":
                    current_intensity = intensity + i * 4 + variant % 2
                elif family == "speed_openers":
                    current_intensity = intensity + variant % 3
                else:
                    current_intensity = intensity + variant % 3
                steps.append(work(work_minutes, current_intensity, f"Opener {i + 1}"))
                if i < count - 1:
                    steps.append(recovery(recover_minutes, 65))
            workouts.append(build_workout(
                family,
                variant,
                "Openers",
                family,
                steps,
                ["openers", "race-prep", "activation", "running"],
                8,
                5,
            ))

    return workouts