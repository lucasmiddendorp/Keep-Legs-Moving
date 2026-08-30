"""Generate the structured workout library and metadata index."""
import argparse
import json
import shutil
from pathlib import Path
from .workout_definitions import generate_workouts
from .workout_validator import validate_definition, validate_unique

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT

def generate_library(sample=False):
    workouts = generate_workouts()
    if sample:
        workouts = [workouts[index] for index in (0, 72, 138, 204) if index < len(workouts)]
    validate_unique(workouts)
    if OUTPUT.exists():
        for sport in ("cycling", "running"):
            sport_dir = OUTPUT / sport
            if sport_dir.exists():
                shutil.rmtree(sport_dir)
        index_path = OUTPUT / "workout_index.json"
        if index_path.exists():
            index_path.unlink()
    index = []
    counts = {}
    for workout in workouts:
        validate_definition(workout)
        sport = getattr(workout, "sport", "Cycling").lower()
        category = workout.category.lower()
        category_dir = OUTPUT / sport / category
        category_dir.mkdir(parents=True, exist_ok=True)
        metadata = workout.to_dict()
        metadata["sport"] = sport
        metadata["fit_filename"] = f"{sport}/{category}/{workout.id}.fit"
        json_path = category_dir / f"{workout.id}.json"
        json_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        index.append(metadata)
        counts.setdefault(sport, {})
        counts[sport][workout.category] = counts[sport].get(workout.category, 0) + 1
    (OUTPUT / "workout_index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"Generated {len(workouts)} workouts: {counts}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true")
    generate_library(sample=parser.parse_args().sample)