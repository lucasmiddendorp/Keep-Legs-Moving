from pathlib import Path
import json
import re
from datetime import date, datetime
import pandas as pd
import Strava.strava_config as strava_config

from Strava.strava_user import get_training_goal, get_user_settings
from helpers.availability import load_availability
from helpers.metrics import calculate_training_load
from helpers.fit_generator import generate_fit_workout
from training_planner.planner import create_training_plan

CATEGORIES = {"VO2max": "VO2max", "Threshold": "Threshold", "Tempo": "Tempo", "Endurance": "Endurance"}
LEVELS = {"A": 20, "B": 40, "C": 60, "D": 80, "E": 100}
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

CATEGORY_COLORS = {
    "VO2max": "#EF4444",
    "Threshold": "#F59E0B",
    "Tempo": "#10B981",
    "Endurance": "#3B82F6",
}

def load_workouts(library_path):
    """Load all workout JSON files from the workout library."""
    workouts = []
    for file in Path(library_path).rglob("*.json"):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            data["_file"] = str(file)
            data["_category"] = data.get("category", file.parent.name)
            data["_level"] = data.get("level", file.name[0].upper())
            workouts.append(data)
        except Exception:
            continue
    return workouts

def get_workouts(workouts, category, level):
    """Return workouts matching category and difficulty."""
    return [
        workout
        for workout in workouts
        if workout.get("_category") == category
        and str(workout.get("_level", "")).upper() == str(level).upper()
    ]

def workout_label(workout):
    """Create a compact workout selector label."""
    return f"{workout['name']} · {workout.get('target_tss', '—')} TSS"

def workout_to_plot_steps(workout):
    """Convert JSON workout steps into the format used by the workout plot."""
    steps = []
    for step in workout.get("steps", []):
        duration = float(step.get("duration_seconds", 0) or 0)
        if duration <= 0:
            continue
        intensity = float(step.get("intensity", 55) or 55)
        steps.append({
            "name": step.get("name", "Step"),
            "duration": duration,
            "target_low": intensity,
            "target_high": intensity,
            "type": "step",
        })
    return steps

def workout_to_fit_steps(workout):
    """Convert a JSON workout into the step format required by the FIT generator."""
    steps = []
    for step in workout.get("steps", []):
        duration = float(step.get("duration_seconds", 0) or 0)
        if duration <= 0:
            continue
        steps.append({
            "name": step.get("name", "Step"),
            "duration_type": step.get("duration_type", "Time"),
            "duration_minutes": int(duration // 60),
            "duration_seconds": int(duration % 60),
            "duration_distance": float(step.get("duration_distance", 0) or 0),
            "intensity": float(step.get("intensity", 55) or 55),
            "repeat": 1,
        })
    return steps

def generate_workout_fit(workout, sport="Cycling", ftp=290, threshold_pace=6.0):
    """Generate a FIT file from a library workout."""
    steps = workout_to_fit_steps(workout)
    if not steps:
        raise ValueError(f"Workout '{workout.get('name', 'Workout')}' contains no valid steps.")
    fit_bytes = generate_fit_workout(
        sport=sport,
        name=workout.get("name", "Workout"),
        steps=steps,
        ftp=ftp,
        threshold_pace=threshold_pace,
    )
    filename = re.sub(r"[^a-zA-Z0-9_-]+", "_", workout.get("name", "workout"))
    return fit_bytes, f"{filename}.fit"


def _parse_goal_date(goal_date):
    if not goal_date:
        return None

    try:
        return datetime.fromisoformat(str(goal_date)).date()
    except Exception:
        return None


def _planning_week_number(goal_date):
    """Return 1..4 planning-cycle week number."""
    goal_day = _parse_goal_date(goal_date)
    if goal_day:
        days_to_goal = (goal_day - date.today()).days
        if days_to_goal >= 0:
            # Count backwards from goal week in a 4-week cycle.
            return ((days_to_goal // 7) % 4) + 1

    return (date.today().isocalendar().week % 4) + 1


def calculate_target_weekly_tss(username):
    """Calculate a realistic weekly target from recent training load and progression."""
    settings = get_user_settings(username)

    progression = float(settings.get("training_progression", 8) or 8)
    atl_tc = int(settings.get("atl_tc", 7) or 7)

    daily = calculate_training_load(
        username,
        strava_config.CTL_TIME_CONSTANT,
        atl_tc,
        activity_type="All",
    )

    if daily is None or daily.empty:
        baseline_weekly = 260.0
    else:
        ctl = max(0.0, float(daily["CTL"].iloc[-1] or 0.0))
        baseline_weekly = max(140.0, ctl * 7.0)

    goal = get_training_goal(username)
    goal_date = goal.get("goal_date") if isinstance(goal, dict) else None
    week_number = _planning_week_number(goal_date)

    if week_number % 4 == 0:
        target = baseline_weekly * 0.7
    else:
        target = baseline_weekly * (1 + progression / 100.0)

    parsed_goal = _parse_goal_date(goal_date)
    if parsed_goal:
        days_to_goal = (parsed_goal - date.today()).days
        if 0 <= days_to_goal <= 7:
            target *= 0.75
        elif 8 <= days_to_goal <= 14:
            target *= 0.85

    return round(max(100.0, min(1200.0, target)), 0)
def calculate_previous_week_tss(username):
    """Calculate completed TSS for the previous calendar week."""
    settings = get_user_settings(username)
    atl_tc = int(settings.get("atl_tc", 7) or 7)
    daily = calculate_training_load(
        username,
        strava_config.CTL_TIME_CONSTANT,
        atl_tc,
        activity_type="All",
    )
    if daily is None or daily.empty:
        return 0.0
    df = daily.copy()
    df.index = pd.to_datetime(df.index, errors="coerce")
    df = df[~df.index.isna()]
    today = pd.Timestamp.today().normalize()
    current_week_start = today - pd.Timedelta(days=today.weekday())
    previous_week_start = current_week_start - pd.Timedelta(days=7)
    previous_week_end = current_week_start - pd.Timedelta(days=1)
    previous_week = df[
        (df.index >= previous_week_start)
        & (df.index <= previous_week_end)
    ]
    if previous_week.empty:
        return 0.0
    tss_column = next(
        (
            column
            for column in ["TSS", "tss", "Stress", "stress"]
            if column in previous_week.columns
        ),
        None,
    )
    if tss_column is None:
        return 0.0
    return round(float(previous_week[tss_column].fillna(0).sum()), 0)

def build_week(target, username, workouts=None):
    """Build a weekly structure using availability, progression, and goal context."""
    settings = get_user_settings(username)
    goal = get_training_goal(username)

    progression = float(settings.get("training_progression", 8) or 8)
    athlete_level = settings.get("athlete_level", "Amateur")
    goal_name = goal.get("name") if isinstance(goal, dict) else None
    goal_date = goal.get("goal_date") if isinstance(goal, dict) else None
    week_number = _planning_week_number(goal_date)

    availability = load_availability(username).get("weekly", {})

    schedule = create_training_plan(
        weekly_tss=target,
        progression=progression,
        availability=availability,
        goal=goal_name,
        goal_date=goal_date,
        workouts=workouts,
        week_number=week_number,
        athlete_level=athlete_level,
    )

    return schedule

def calculate_weekly_tss(training_plan):
    """Calculate the total TSS of the current weekly plan."""
    return sum(
        float(
            (
                plan.get("workout", {}).get("target_tss")
                if plan.get("workout")
                else plan.get("target_tss", 0)
            )
            or 0
        )
        for plan in training_plan.values()
        if plan
    )