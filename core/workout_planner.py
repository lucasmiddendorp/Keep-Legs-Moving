from datetime import datetime, timedelta

class WorkoutPlanner:
    def __init__(self, user, load_model):
        self.user = user
        self.load_model = load_model

    def plan_week(self, start_date, availability):
        workouts = []
        for i, available in enumerate(availability):
            if not available:
                continue

            readiness = self.load_model.readiness()
            intensity = self._choose_intensity(readiness)

            workout = self._generate_workout(intensity)
            workouts.append((start_date + timedelta(days=i), workout))
        return workouts

    def _choose_intensity(self, readiness):
        if readiness < 0:
            return 'Recovery'
        elif readiness < 10:
            return 'Endurance'
        elif readiness < 25:
            return 'Threshold'
        else:
            return 'VO2max'

    def _generate_workout(self, intensity):
        library = {
            'Recovery': [('Zone1', 0.6, 0.7, 60)],
            'Endurance': [('Zone2', 0.7, 0.8, 90)],
            'Threshold': [('SST', 0.9, 0.95, 50)],
            'VO2max': [('VO2', 1.1, 1.2, 40)]
        }
        return library[intensity]
