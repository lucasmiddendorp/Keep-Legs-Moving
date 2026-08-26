from pathlib import Path
import json

OUTPUT_DIR = Path(__file__).resolve().parent / "training_planner" / "workout_library" / "Endurance"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGETS = [20, 40, 60, 80, 100]
INTENSITY = 68

def calculate_duration(target_tss, intensity):
    return target_tss / ((intensity / 100) ** 2)

for target_tss in TARGETS:
    total_minutes = calculate_duration(target_tss, INTENSITY)
    minutes = int(total_minutes)
    seconds = round((total_minutes - minutes) * 60)

    if seconds == 60:
        minutes += 1
        seconds = 0

    steps = [
        {
            "name": "Warm-up",
            "duration_type": "Time",
            "intensity": 55,
            "duration_minutes": 10,
            "duration_seconds": 600,
            "duration_distance": 0,
        },
        {
            "name": "Endurance",
            "duration_type": "Time",
            "intensity": INTENSITY,
            "duration_minutes": minutes,
            "duration_seconds": minutes * 60 + seconds,
            "duration_distance": 0,
        },
        {
            "name": "Cool-down",
            "duration_type": "Time",
            "intensity": 55,
            "duration_minutes": 10,
            "duration_seconds": 600,
            "duration_distance": 0,
        },
    ]

    workout = {
        "name": f"Endurance {target_tss} TSS",
        "category": "Endurance",
        "target_tss": target_tss,
        "steps": steps,
    }

    filename = f"{target_tss}_endurance.json"
    path = OUTPUT_DIR / filename

    path.write_text(
        json.dumps(workout, indent=2),
        encoding="utf-8",
    )

    print(f"Created {filename}")

print("Done.")