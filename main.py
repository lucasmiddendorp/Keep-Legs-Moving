from datetime import datetime
from data.user_data import UserProfile
from data.activity_loader import ActivityLoader
from data.power_metrics import calc_np, calc_if, calc_tss
from core.training_load_model import TrainingLoadModel
from core.workout_planner import WorkoutPlanner

def main():
    # Create user
    user = UserProfile(
        name="LucasMiddendorp",
        ftp=250,
        weight=70,
        max_hr=190,
        training_days=[1, 3, 5, 6],
        goal_date="2025-03-01",
        goal_type="GranFondo"
    )

    # Initialize systems
    loader = ActivityLoader()
    load_model = TrainingLoadModel()
    planner = WorkoutPlanner(user, load_model)

    # Load past activities (could be from Strava or local files)
    activities = loader.load_recent_activities("data/activities/")

    # Update fitness/fatigue from past rides
    for act in activities:
        np_value = calc_np(act["power"])
        tss = calc_tss(act["duration_s"], np_value, user.ftp)
        load_model.update(tss)

    # Generate adaptive plan
    availability = [True, False, True, False, True, True, False]
    plan = planner.plan_week(start_date=datetime.today(), availability=availability)

    print("\n🚴 Weekly Training Plan for", user.name)
    for day, workout in plan:
        print(f"{day.date()} → {workout}")

if __name__ == "__main__":
    main()
