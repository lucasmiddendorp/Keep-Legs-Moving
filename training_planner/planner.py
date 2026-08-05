from datetime import date, timedelta
from training_planner.models import Athlete
from training_planner.goals import get_goal
from training_planner.phases import determine_phase
from training_planner.workout_selector import select_category, select_workout

LEVEL_SETTINGS = {
    "Beginner": {
        "max_hard_sessions_week": 2,
        "max_tss_day": 100
    },
    "Advanced": {
        "max_hard_sessions_week": 3,
        "max_tss_day": 150
    },
    "Professional": {
        "max_hard_sessions_week": 5,
        "max_tss_day": 220
    }
}

HARD_SESSIONS = [
    "VO2 Max",
    "Threshold"
]

class TrainingPlanner:
    def __init__(self, athlete, goal):
        self.athlete = athlete
        if hasattr(goal, "name"):
            self.goal_name = goal.name
            self.race_date = goal.race_date
        else:
            self.goal_name = goal
            self.race_date = None
        self.goal_settings = get_goal(self.goal_name)
        self.level_settings = LEVEL_SETTINGS.get(
            athlete.level,
            LEVEL_SETTINGS["Advanced"]
        )

    def get_available_hours(self, workout_date):
        weekday = workout_date.strftime("%A")
        availability = self.athlete.availability
        if str(workout_date) in availability.get("exceptions", {}):
            exception = availability["exceptions"][str(workout_date)]
            if exception["available"]:
                return exception["hours"]
            return 0
        weekly = availability.get("weekly", {})
        if weekday in weekly and weekly[weekday]["available"]:
            return weekly[weekday]["hours"]
        return 0

    def update_training_state(self, ctl, atl, tss):
        ctl = ctl + (tss - ctl) / 42
        atl = atl + (tss - atl) / 7
        tsb = ctl - atl
        return ctl, atl, tsb

    def generate_plan_until_goal(self):
        plan = []
        current_date = date.today()
        ctl = self.athlete.ctl
        atl = self.athlete.atl
        tsb = self.athlete.tsb
        recent_categories = []
        hard_sessions_week = 0
        week_start = current_date
        while current_date <= self.race_date:
            days_to_goal = (self.race_date - current_date).days
            phase = determine_phase(days_to_goal)
            available_hours = self.get_available_hours(current_date)
            if available_hours == 0:
                workout = {
                    "name": "Rest",
                    "category": "Recovery",
                    "duration": 0,
                    "if": 0,
                    "tss": 0
                }
            else:
                simulated_athlete = Athlete(
                    ftp=self.athlete.ftp,
                    ctl=ctl,
                    atl=atl,
                    tsb=tsb,
                    history=self.athlete.history,
                    availability=self.athlete.availability,
                    level=self.athlete.level
                )
                category = select_category(
                    simulated_athlete,
                    phase,
                    self.goal_settings["distribution"]
                )
                if recent_categories and recent_categories[-1] in HARD_SESSIONS and category in HARD_SESSIONS:
                    category = "Endurance"
                if hard_sessions_week >= self.level_settings["max_hard_sessions_week"] and category in HARD_SESSIONS:
                    category = "Endurance"
                workout = select_workout(
                    category,
                    simulated_athlete,
                    available_hours
                )
                if workout["tss"] > self.level_settings["max_tss_day"]:
                    category = "Endurance"
                    workout = select_workout(
                        category,
                        simulated_athlete,
                        available_hours
                    )
            workout_category = workout.get("category", "Recovery")
            plan.append({
                "date": str(current_date),
                "phase": phase,
                "category": workout_category,
                "name": workout["name"],
                "duration": workout["duration"],
                "if": workout["if"],
                "tss": workout["tss"]
            })
            ctl, atl, tsb = self.update_training_state(
                ctl,
                atl,
                workout["tss"]
            )
            recent_categories.append(workout_category)
            if workout_category in HARD_SESSIONS:
                hard_sessions_week += 1
            if (current_date - week_start).days >= 7:
                hard_sessions_week = 0
                week_start = current_date
            current_date += timedelta(days=1)
        return plan