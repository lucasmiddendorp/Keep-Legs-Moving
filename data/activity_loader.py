"""
activity_loader.py
Handles importing of cycling activities from Strava or local files.
"""

import os
import pandas as pd

class ActivityLoader:
    """Loads and parses cycling activities."""

    def __init__(self):
        self.activities = []

    def load_recent_activities(self, folder_path):
        """
        Loads ride data from .csv or .fit/.tcx/.gpx (to be extended).
        Returns a list of dicts with power/time data.
        """
        activities = []

        for file in os.listdir(folder_path):
            if file.endswith(".csv"):
                df = pd.read_csv(os.path.join(folder_path, file))
                if "power" in df.columns:
                    activity = {
                        "filename": file,
                        "duration_s": len(df) * 1,  # assuming 1 Hz sampling rate
                        "power": df["power"].values.tolist(),
                        "date": file.split(".")[0]
                    }
                    activities.append(activity)

        self.activities = activities
        return activities

    def load_from_strava(self, client, n=5):
        """
        Example placeholder for Strava API.
        Would use stravalib to fetch last N rides.
        """
        client = client  # placeholder for actual Stra
        print(f"Fetching {n} activities from Strava...")
        return []  # placeholder for future Strava integration
