"""Structured cycling and running workout definitions."""
from dataclasses import asdict, dataclass, field
from typing import Any
from helpers.metrics import get_training_zone

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
    def duration_seconds(self):
        return sum(s.duration_seconds * s.repeat for s in self.steps)
    @property
    def target_tss(self):
        weighted = sum(s.duration_seconds * s.repeat * (s.intensity / 100) ** 2 for s in self.steps)
        return round(weighted / 3600 * 100)
    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["steps"] = [asdict(s) for s in self.steps]
        data.update({"duration_minutes": round(self.duration_seconds / 60),"estimated_tss": self.target_tss,"target_tss": self.target_tss,"target_if": round(self.target_if, 2),"sport": self.sport,"interval_count": sum(s.repeat for s in self.steps if "interval" in s.name.lower() or "work" in s.name.lower()),"interval_duration": next((s.duration_seconds for s in self.steps if "work" in s.name.lower()), 0),"recovery_duration": next((s.duration_seconds for s in self.steps if "recover" in s.name.lower()), 0),"sets": max((s.repeat for s in self.steps), default=1),"zones": self._zones()})
        return data
    def _zones(self):
        zones = {}
        for step in self.steps:
            zone = get_training_zone(step.intensity)
            zones[zone] = zones.get(zone, 0) + step.duration_seconds * step.repeat / 60
        return {k: round(v, 1) for k, v in zones.items()}

def _workout(workout_id, name, category, subtype, sport, steps, tags):
    intensity_time = sum(s.duration_seconds * s.repeat * (s.intensity / 100) ** 4 for s in steps)
    duration = sum(s.duration_seconds * s.repeat for s in steps)
    target_if = (intensity_time / max(duration, 1)) ** 0.25
    return Workout(workout_id, name, category, subtype, sport, tuple(steps), target_if, tuple(tags))

def warmup(minutes=10, sport="Cycling"):
    return Step("Warm-up", minutes * 60, 60 if sport == "Cycling" else 65)

def cooldown(minutes=10, sport="Cycling"):
    return Step("Cool-down", minutes * 60, 55 if sport == "Cycling" else 60)

def recovery(minutes, sport="Cycling"):
    return Step("Recovery", minutes * 60, 50 if sport == "Cycling" else 60)

def work(minutes, intensity, name="Work interval"):
    return Step(name, round(minutes * 60), intensity)

def build_workout(family, variant, category, subtype, sport, work_steps, tags, warmup_minutes=10, cooldown_minutes=10):
    if sport == "Running":
        warmup_minutes += 3
        cooldown_minutes += 3
    steps = [warmup(warmup_minutes + variant, sport),Step(f"{family.replace('_', ' ').title()} focus", 30, 60 if sport == "Cycling" else 65),*work_steps,cooldown(cooldown_minutes + variant % 3, sport)]
    return _workout(f"{sport.lower()}_{category.lower()}_{family}_{variant:02d}",f"{family.replace('_', ' ').title()} {variant:02d}",category,subtype,sport,steps,[sport.lower(),category.lower(),subtype,family,*tags])

def generate_workouts(sport="Cycling"):
    workouts = []
    vo2_families = {"ronnestad_30_15": lambda v: (2 + v % 3, 8 + v % 5, 0.5, 0.25, 115),"long_vo2": lambda v: (3 + v % 3, 3 + v % 3, 4, 4, 108),"four_by_four": lambda v: (3 + v % 3, 4 + v % 2, 4, 4, 112),"short_vo2": lambda v: (2 + v % 3, 12 + v % 5, 1, 1, 120),"micro_intervals": lambda v: (3 + v % 2, 10 + v % 4, 1, 1, 118),"ascending_vo2": lambda v: (3, 3, 3, 3, 108 + v),"descending_vo2": lambda v: (3, 3, 4, 4, 112 - v),"variable_vo2": lambda v: (3, 4, 2, 2, 110),"repeated_vo2_blocks": lambda v: (2 + v % 2, 4 + v % 3, 3, 3, 112),"progressive_vo2": lambda v: (3, 4, 4, 4, 105 + v * 2),"over_under_vo2": lambda v: (3, 4, 2, 2, 106),"hill_vo2": lambda v: (3, 5 + v % 2, 3, 3, 110)}
    for family, recipe in vo2_families.items():
        for variant in range(1, 7):
            sets, reps, work_min, recover_min, intensity = recipe(variant)
            steps = []
            for s in range(sets):
                if family == "ronnestad_30_15":
                    for r in range(reps):
                        steps.append(work(work_min, intensity, f"30 sec Work {r + 1}"))
                        if r < reps - 1: steps.append(recovery(recover_min, sport))
                elif family == "variable_vo2":
                    for r in range(reps):
                        steps.append(work(work_min + r % 3, intensity + r * 2, f"Work interval {r + 1}"))
                        if r < reps - 1: steps.append(recovery(recover_min, sport))
                elif family == "over_under_vo2":
                    steps.extend([work(2, 105, "Under"), work(2, 120, "Over")])
                else:
                    for r in range(reps):
                        steps.append(work(work_min, intensity, f"Work interval {r + 1}"))
                        if r < reps - 1: steps.append(recovery(recover_min, sport))
                if s < sets - 1: steps.append(recovery(recover_min, sport))
            workouts.append(build_workout(family, variant, "VO2max", family, sport, steps, ["high-intensity", "hard"], 12, 10))

    threshold_families = {"traditional": (3, 8, 5, 4, 98),"long_threshold": (2, 3, 12, 6, 95),"cruise_intervals": (3, 4, 8, 3, 96),"over_under": (3, 5, 2, 2, 95),"progressive_threshold": (3, 4, 6, 4, 92),"descending_threshold": (3, 4, 10, 4, 98),"threshold_ladder": (1, 4, 5, 3, 95),"broken_threshold": (2, 3, 10, 5, 97),"double_threshold": (2, 3, 10, 4, 94),"sustained_threshold": (1, 1, 30, 0, 92),"sweetspot_threshold": (3, 4, 10, 3, 90)}
    for family, (sets, reps, work_min, recover_min, intensity) in threshold_families.items():
        for variant in range(1, 7):
            count = reps + variant % 2
            steps = []
            for s in range(sets):
                if family == "threshold_ladder":
                    for i in range(variant + 2):
                        steps.append(work(4 + i, intensity + i, f"Ladder interval {i + 1}"))
                        if i < variant + 1: steps.append(recovery(recover_min, sport))
                elif family == "descending_threshold":
                    for i in range(count):
                        steps.append(work(max(5, work_min - i), intensity, f"Descending interval {i + 1}"))
                        if i < count - 1: steps.append(recovery(recover_min, sport))
                elif family == "over_under":
                    steps.extend([work(2, 88, "Under"), work(2, 102, "Over")])
                else:
                    for r in range(count):
                        steps.append(work(work_min + variant % 3, intensity, f"Threshold interval {r + 1}"))
                        if r < count - 1 and recover_min: steps.append(recovery(recover_min, sport))
                if s < sets - 1 and recover_min: steps.append(recovery(recover_min, sport))
            workouts.append(build_workout(family, variant, "Threshold", family, sport, steps, ["hard", "threshold"], 10, 10))

    tempo_families = {"steady_tempo": (2, 15, 82),"progressive_tempo": (3, 10, 78),"tempo_intervals": (4, 8, 84),"long_tempo_blocks": (2, 20, 80),"tempo_endurance": (2, 12, 80),"cadence_tempo": (4, 8, 82),"sweetspot_tempo": (3, 10, 88),"over_under_tempo": (4, 6, 84),"variable_tempo": (4, 7, 80),"tempo_ladder": (1, 5, 80)}
    for family, (sets, work_min, intensity) in tempo_families.items():
        for variant in range(1, 7):
            blocks = sets + variant % 2
            steps = []
            for i in range(blocks):
                current = intensity + i if family in {"progressive_tempo", "tempo_ladder"} else intensity
                if family == "over_under_tempo": steps.extend([work(work_min, current - 4, "Under"), work(work_min, current + 8, "Over")])
                elif family == "variable_tempo": steps.append(work(work_min + i % 3, current, "Tempo block"))
                else: steps.append(work(work_min + variant % 3, current, "Tempo block"))
                if i < blocks - 1: steps.append(recovery(3 if family != "tempo_endurance" else 5, sport))
            workouts.append(build_workout(family, variant, "Tempo", family, sport, steps, ["moderate", "aerobic"], 10, 10))

    endurance_families = {"steady_z2": (60, 70),"progressive_z2": (60, 68),"long_z2": (120, 68),"z2_tempo": (75, 70),"z2_cadence": (75, 68),"z2_surges": (90, 68),"aerobic_progression": (90, 65),"recovery_endurance": (45, 60)}
    for family, (base_min, intensity) in endurance_families.items():
        variants = 16 if family == "long_z2" else 8
        for variant in range(1, variants + 1):
            duration = 120 + variant * 10 if family == "long_z2" else base_min + variant * (15 if family == "steady_z2" else 8)
            if family == "z2_tempo": steps = [work(duration - 20, intensity, "Endurance block"), work(10 + variant % 3 * 5, 80, "Tempo finish")]
            elif family == "z2_cadence": steps = [work(10, intensity + 4 if i % 2 else intensity, "Cadence block") for i in range(max(3, duration // 20))]
            elif family == "z2_surges": steps = [work(15, intensity, "Endurance block"), work(0.5, 85, "Controlled surge")] * max(2, duration // 45)
            else: steps = [work(duration, intensity, "Endurance ride")]
            workouts.append(build_workout(family, variant, "Endurance", family, sport, steps, ["easy", "z2", "aerobic"], 8, 8))

    if sport == "Cycling":
        special = [
            ("openers", "Openers", [[work(10,55,"Warm-up"),work(3,90,"Opener"),recovery(3,sport),work(1,115,"Opener"),recovery(3,sport),work(.5,130,"Opener"),recovery(3,sport),work(5,55,"Cool-down")],[work(12,55,"Warm-up"),work(2,95,"Opener"),recovery(3,sport),work(1,120,"Opener"),recovery(3,sport),work(.5,135,"Opener"),recovery(5,sport),work(5,55,"Cool-down")]]),
            ("ftp_test", "Testing", [[work(15,55,"Warm-up"),work(5,100,"FTP test"),recovery(5,sport),work(20,100,"FTP test"),work(10,55,"Cool-down")],[work(15,55,"Warm-up"),work(5,105,"FTP test"),recovery(5,sport),work(20,105,"FTP test"),work(10,55,"Cool-down")]])
        ]
    else:
        special = [
            ("running_openers", "Openers", [[work(12,65,"Easy warm-up"),work(3,90,"Strides"),recovery(2,sport),work(1,115,"Fast stride"),recovery(2,sport),work(.5,125,"Fast stride"),recovery(3,sport),work(8,60,"Easy cool-down")],[work(15,65,"Easy warm-up"),work(2,95,"Strides"),recovery(2,sport),work(1,120,"Fast stride"),recovery(2,sport),work(.5,130,"Fast stride"),recovery(4,sport),work(8,60,"Easy cool-down")]]),
            ("running_threshold_test", "Testing", [[work(15,65,"Easy warm-up"),work(20,100,"Threshold test"),work(10,60,"Easy cool-down")],[work(15,65,"Easy warm-up"),work(30,100,"Threshold test"),work(10,60,"Easy cool-down")]])
        ]

    for family, category, variants in special:
        for variant, steps in enumerate(variants, 1):
            workouts.append(build_workout(family, variant, category, family, sport, steps, [category.lower(), family], 0, 0))
    return workouts