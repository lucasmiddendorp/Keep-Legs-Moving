"""Generate the structured running workout library and metadata index."""
import argparse
import json
import shutil
from pathlib import Path
from .running_workout_definitions import generate_running_workouts
from .workout_validator import validate_definition, validate_unique

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "running"

def generate_library(sample=False):
    workouts = generate_running_workouts()
    if sample:
        workouts = [workouts[index] for index in (0, 12, 24, 36) if index < len(workouts)]
    validate_unique(workouts)
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    index = []
    counts = {}
    for workout in workouts:
        validate_definition(workout)
        category = workout.category.lower()
        category_dir = OUTPUT / category
        category_dir.mkdir(parents=True, exist_ok=True)
        metadata = workout.to_dict()
        metadata["sport"] = "Running"
        metadata["fit_filename"] = f"{category}/{workout.id}.fit"
        (category_dir / f"{workout.id}.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        index.append(metadata)
        counts[workout.category] = counts.get(workout.category, 0) + 1
    (OUTPUT / "workout_index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"Generated {len(workouts)} running workouts: {counts}")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true")
    generate_library(sample=parser.parse_args().sample)