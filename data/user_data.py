"""
user_data.py
Defines the UserProfile class, which stores cyclist attributes,
training preferences, and goals.
"""

from datetime import date


class UserProfile:
    """Stores user profile information for training personalization."""

    def __init__(self, name, ftp, weight, max_hr, training_days, goal_date, goal_type):
        self.name = name
        self.ftp = ftp                # Functional Threshold Power (W)
        self.weight = weight          # Rider weight (kg)
        self.max_hr = max_hr          # Maximum heart rate
        self.training_days = training_days  # List of training days (0 = Mon, 6 = Sun)
        self.goal_date = date.fromisoformat(goal_date)
        self.goal_type = goal_type    # e.g., 'GranFondo', 'TT', 'Climbing'

    def __repr__(self):
        return f"<UserProfile {self.name}: FTP={self.ftp}W, Goal={self.goal_type}>"
