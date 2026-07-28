from fitparse import FitFile
import gpxpy
import gpxpy.gpx

import tempfile

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET
from datetime import datetime

from helpers.Wahoozip_reader import parse_fit_file, wahoo_activity_id
from helpers.pacing import Pacing


class PacingComparison:

    def __init__(self, settings):
        self.settings = settings
        self.pacing = Pacing(settings)

    # =========================================================
    # 1. FIT → GPX
    # =========================================================

    def _ensure_file_path(self, file_or_path):
        """
        Converts Streamlit UploadedFile → real filesystem path
        OR passes through normal file paths unchanged
        """

        # already a path
        if isinstance(file_or_path, str):
            return file_or_path

        # Streamlit UploadedFile
        if hasattr(file_or_path, "read"):
            suffix = ".fit"

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(file_or_path.getvalue())
            tmp.close()

            return tmp.name

    def semicircles_to_deg(self, val):
        return val * (180.0 / 2**31)


    def fit_to_gpx(self, fit_path):
        # 1. Parse FIT directly from path
        fitfile = FitFile(fit_path)

        points = []

        for record in fitfile.get_messages("record"):
            data = {f.name: f.value for f in record}

            if "position_lat" in data and "position_long" in data:
                lat = self.semicircles_to_deg(data["position_lat"])
                lon = self.semicircles_to_deg(data["position_long"])
                points.append((lat, lon))

        # 2. Build GPX
        gpx = ET.Element("gpx", version="1.1", creator="fit2gpx")
        trk = ET.SubElement(gpx, "trk")
        seg = ET.SubElement(trk, "trkseg")

        for lat, lon in points:
            ET.SubElement(seg, "trkpt", lat=str(lat), lon=str(lon))

        return ET.tostring(gpx, encoding="utf-8", xml_declaration=True).decode()

    # =========================================================
    # 2. FULL PIPELINE
    # =========================================================
    def run_from_fit(self, fit_file_path):
        """
        Full pipeline:
        FIT → GPX → segments → pacing → outputs
        """

        # Step 1: FIT → DataFrame (reuse parser)
        activity, power_df = parse_fit_file(fit_file_path)

        if isinstance(activity, dict):
            df = activity
        else:
            df = activity.copy()

        # Step 2: GPX-style processing (reuse your logic)
        df = self._normalize_track(df)

        # Step 3: segments
        segments = self.pacing.build_route_segments(df)

        # Step 4: pacing simulation
        modeled = self.pacing.estimate_course_pacing(segments, self.settings)

        return {
            "points": df,
            "segments": segments,
            "modeled": modeled,
        }

    # =========================================================
    # 3. TRACK NORMALIZATION
    # =========================================================
    def _normalize_track(self, df):
        """
        Ensures consistent format + adds x/y for curvature.
        """

        df = df.copy()

        if "ele" not in df.columns:
            df["ele"] = 0.0

        df = df.dropna(subset=["lat", "lon"])

        lat0 = df["lat"].iloc[0]
        lon0 = df["lon"].iloc[0]

        df["x"] = (df["lon"] - lon0) * 111320 * np.cos(np.radians(lat0))
        df["y"] = (df["lat"] - lat0) * 111320

        df["ele"] = df["ele"].rolling(21, center=True, min_periods=1).mean()

        return df

    # =========================================================
    # 4. FIGURES
    # =========================================================
    def plot_route(self, points):
        plt.figure()
        plt.plot(points["x"], points["y"])
        plt.title("Route shape (XY projection)")
        plt.xlabel("X (m)")
        plt.ylabel("Y (m)")
        plt.show()

    def plot_elevation(self, modeled):
        plt.figure()
        plt.plot(modeled["distance_km"], modeled["end_elevation_m"])
        plt.title("Elevation profile")
        plt.xlabel("Distance (km)")
        plt.ylabel("Elevation (m)")
        plt.show()

    def plot_power(self, modeled):
        plt.figure()
        plt.plot(modeled["distance_km"], modeled["target_power_w"])
        plt.title("Pacing power plan")
        plt.xlabel("Distance (km)")
        plt.ylabel("Power (W)")
        plt.show()

    def plot_speed(self, modeled):
        plt.figure()
        plt.plot(modeled["distance_km"], modeled["speed_kmh"])
        plt.title("Predicted speed profile")
        plt.xlabel("Distance (km)")
        plt.ylabel("Speed (km/h)")
        plt.show()

    # =========================================================
    # 5. SUMMARY REPORT (for app.py)
    # =========================================================
    def summary(self, result):
        modeled = result["modeled"]

        total_time_min = modeled["segment_time_s"].sum() / 60
        distance_km = modeled["distance_m"].sum() / 1000

        return {
            "distance_km": round(distance_km, 2),
            "time_min": round(total_time_min, 1),
            "avg_power_w": int(modeled["target_power_w"].mean()),
            "np_w": float(modeled.attrs.get("modeled_np", np.nan)),
        }

    # =========================================================
    # 6. MASTER FUNCTION FOR APP
    # =========================================================
    def run_all(self, fit_file_path):
        """
        Single entrypoint for app.py
        """
        fit_file_path = self._ensure_file_path(fit_file_path)

        # optional GPX export
        gpx = self.fit_to_gpx(fit_file_path)

        result = self.run_from_fit(fit_file_path)

        summary = self.summary(result)

        return {
            "gpx": gpx,
            "summary": summary,
            "points": result["points"],
            "segments": result["segments"],
            "modeled": result["modeled"],
        }