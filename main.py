# main.py
from data.user_data import UserProfile
from core.training_load_model import LoadModel
from core.workout_planner import WorkoutPlanner

user = UserProfile(ftp=250, weight=70, max_hr=190,
                   training_days=[1,3,5,6], goal_date='2025-03-01', goal_type='GranFondo')

load_model = LoadModel()
planner = WorkoutPlanner(user, load_model)

availability = [True, False, True, False, True, True, False]
plan = planner.plan_week(start_date=datetime.today(), availability=availability)

for day, workout in plan:
    print(day.date(), workout)
