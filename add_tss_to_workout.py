from pathlib import Path
import json

OUTPUT_ROOT = Path(__file__).resolve().parent / "training_planner" / "workout_library"
WARMUP_MIN = 10
COOLDOWN_MIN = 10
WARMUP_INTENSITY = 55
COOLDOWN_INTENSITY = 55
TARGETS = [20, 40, 60, 80, 100]

def step_tss(minutes, intensity):
    return 100 * (minutes / 60) * (intensity / 100) ** 2

def calculate_tss(steps):
    return round(sum(step_tss(step["duration_seconds"] / 60, step["intensity"]) for step in steps))

def make_step(name, minutes, intensity):
    return {"name": name, "duration_type": "Time", "intensity": intensity, "duration_minutes": int(minutes), "duration_seconds": int(minutes * 60), "duration_distance": 0}

def warmup():
    return make_step("Warm-up", WARMUP_MIN, WARMUP_INTENSITY)

def cooldown():
    return make_step("Cool-down", COOLDOWN_MIN, COOLDOWN_INTENSITY)

def save_workout(category, name, steps):
    tss = calculate_tss(steps)
    total_minutes = round(sum(step["duration_seconds"] for step in steps) / 60)
    filename = f"{category}_{total_minutes}min"
    if name:
        filename += f"_{name}"
    filename += f"_TSS{tss}.json"
    path = OUTPUT_ROOT / category / filename
    if path.exists():
        print(f"Already exists: {filename}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    workout = {
        "name": filename.replace(".json", ""),
        "category": category,
        "target_tss": tss,
        "steps": steps,
    }
    path.write_text(json.dumps(workout, indent=2), encoding="utf-8")
    print(f"Created {filename}")

def find_best_blocks(make_blocks, target):
    best = None
    for blocks in range(1, 15):
        steps = make_blocks(blocks)
        full_steps = [warmup(), *steps, cooldown()]
        tss = calculate_tss(full_steps)
        difference = abs(tss - target)
        if best is None or difference < best[0]:
            best = (difference, blocks, steps, tss)
    return best

def find_best_duration(make_workout, target, min_minutes=10, max_minutes=300):
    best = None
    for minutes in range(min_minutes, max_minutes + 1):
        steps = make_workout(minutes)
        tss = calculate_tss(steps)
        difference = abs(tss - target)
        if best is None or difference < best[0]:
            best = (difference, minutes, steps, tss)
    return best

def create_endurance_workouts():
    intensity = 68
    endurance_targets = [20, 40, 60, 80, 100, 120, 140, 160, 180, 200]
    for target in endurance_targets:
        _, minutes, steps, tss = find_best_duration(
            lambda minutes: [
                warmup(),
                make_step("Endurance", minutes, intensity),
                cooldown(),
            ],
            target,
        )
        save_workout("Endurance", "", steps)

def create_tempo_10min():
    intensity = 85
    recovery = 55
    def make_blocks(blocks):
        steps = []
        for i in range(blocks):
            steps.append(make_step("Tempo", 10, intensity))
            if i < blocks - 1:
                steps.append(make_step("Recovery", 5, recovery))
        return steps
    for target in TARGETS:
        _, blocks, steps, tss = find_best_blocks(make_blocks, target)
        save_workout("Tempo", f"{blocks}x10", [warmup(), *steps, cooldown()])

def create_sweetspot_workouts():
    def make_blocks(blocks):
        steps = []
        for _ in range(blocks):
            steps.extend([make_step("Sweetspot", 5, 93), make_step("Sweetspot", 5, 89)])
        return steps
    for target in TARGETS:
        _, blocks, steps, tss = find_best_blocks(make_blocks, target)
        save_workout("Tempo", f"{blocks}xSweetspot", [warmup(), *steps, cooldown()])

def create_threshold_10min():
    intensity = 100
    recovery = 55
    def make_blocks(blocks):
        steps = []
        for i in range(blocks):
            steps.append(make_step("Threshold", 10, intensity))
            if i < blocks - 1:
                steps.append(make_step("Recovery", 5, recovery))
        return steps
    for target in TARGETS:
        _, blocks, steps, tss = find_best_blocks(make_blocks, target)
        save_workout("Threshold", f"{blocks}x10", [warmup(), *steps, cooldown()])

def create_threshold_overs_unders():
    def make_blocks(blocks):
        steps = []
        for _ in range(blocks):
            steps.extend([make_step("Over", 5, 105), make_step("Under", 5, 95)])
        return steps
    for target in TARGETS:
        _, blocks, steps, tss = find_best_blocks(make_blocks, target)
        save_workout("Threshold", f"{blocks}xOU", [warmup(), *steps, cooldown()])


# ============================================================
# VO2max
# ============================================================
def create_vo2max_workouts():
    def norwegian_blocks(blocks):
        steps = []
        for i in range(blocks):
            steps.append(make_step("VO₂ Max", 4, 120))
            if i < blocks - 1:
                steps.append(make_step("Recovery", 3, 55))
        return steps

    def ronnestad_blocks(sets):
        steps = []
        for s in range(sets):
            for i in range(13):
                steps.append(make_step("VO₂ Max", 0.5, 120))
                steps.append(make_step("Recovery", 0.25, 55))
            if s < sets - 1:
                steps.append(make_step("Recovery", 3, 55))
        return steps

    for target in TARGETS:
        best = None
        for blocks in range(2, 6):
            workout_steps = [warmup(), *norwegian_blocks(blocks), cooldown()]
            tss = calculate_tss(workout_steps)
            difference = abs(tss - target)
            if best is None or difference < best[0]:
                best = (difference, blocks, workout_steps, tss)
        _, blocks, steps, tss = best
        save_workout("VO2max", f"{blocks}x4min_Norwegian", steps)

    for target in TARGETS:
        best = None
        for sets in range(1, 4):
            workout_steps = [warmup(), *ronnestad_blocks(sets), cooldown()]
            tss = calculate_tss(workout_steps)
            difference = abs(tss - target)
            if best is None or difference < best[0]:
                best = (difference, sets, workout_steps, tss)
        _, sets, steps, tss = best
        save_workout("VO2max", f"{sets}xRonnestad", steps)

if __name__ == "__main__":
    create_endurance_workouts()
    create_tempo_10min()
    create_sweetspot_workouts()
    create_threshold_10min()
    create_threshold_overs_unders()
    create_vo2max_workouts()
    print("\nWorkout library created.")