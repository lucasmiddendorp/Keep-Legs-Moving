"""Generate the original structured FIT workout library and metadata index."""

import argparse
import json
import shutil
from pathlib import Path

from .fit_exporter import export_workout
from .workout_definitions import generate_workouts
from .workout_validator import validate_definition, validate_fit, validate_unique

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT


def generate_library(sample=False):
    workouts = generate_workouts()
    if sample:
        workouts = [workouts[index] for index in (0, 72, 138, 204)]
    validate_unique(workouts)
    if OUTPUT.exists():
        for category in ("vo2max", "threshold", "tempo", "endurance"):
            category_dir = OUTPUT / category
            if category_dir.exists():
                shutil.rmtree(category_dir)
        index_path = OUTPUT / "workout_index.json"
        if index_path.exists():
            index_path.unlink()
    for workout in workouts:
        validate_definition(workout)
        category = workout.category.lower()
        category_dir = OUTPUT / category
        category_dir.mkdir(parents=True, exist_ok=True)
        fit_name = f"{workout.id}.fit"
        fit_payload = export_workout(workout)
        validate_fit(fit_payload)
        (category_dir / fit_name).write_bytes(fit_payload)
        metadata = workout.to_dict()
        metadata["fit_filename"] = f"{category}/{fit_name}"
        (category_dir / f"{workout.id}.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )
    index = []
    for workout in workouts:
        item = workout.to_dict()
        item["fit_filename"] = f"{workout.category.lower()}/{workout.id}.fit"
        index.append(item)
    (OUTPUT / "workout_index.json").write_text(
        json.dumps(index, indent=2), encoding="utf-8"
    )
    counts = {}
    for workout in workouts:
        counts[workout.category] = counts.get(workout.category, 0) + 1
    print(f"Generated {len(workouts)} workouts: {counts}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true")
    generate_library(sample=parser.parse_args().sample)
