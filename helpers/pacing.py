import math
import numpy as np
import pandas as pd
import xml.etree.ElementTree as ET

G = 9.80665


class Pacing:

    def __init__(self, settings):
        self.settings = settings

    def haversine_m(self,lat1, lon1, lat2, lon2):
        radius = 6371000
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        return radius * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


    def bearing_deg(self, lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1
        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        return (math.degrees(math.atan2(x, y)) + 360) % 360


    def parse_gpx(self, uploaded_file):
        root = ET.fromstring(uploaded_file.getvalue())
        points = []

        for point in root.iter():
            tag = point.tag.split("}")[-1]
            if tag not in {"trkpt", "rtept"}:
                continue

            lat = float(point.attrib["lat"])
            lon = float(point.attrib["lon"])
            ele = np.nan
            for child in point:
                if child.tag.split("}")[-1] == "ele" and child.text:
                    ele = float(child.text)
                    break
            points.append({"lat": lat, "lon": lon, "ele": ele})

        # For curvature 
        lat0 = points[0]["lat"]
        lon0 = points[0]["lon"]

        for p in points:

            p["x"] = (
                (p["lon"] - lon0)
                * 111320
                * math.cos(math.radians(lat0))
            )

            p["y"] = (
                (p["lat"] - lat0)
                * 111320
            )
        df = pd.DataFrame(points)

        df["ele"] = (
            df["ele"]
            .rolling(21, center=True, min_periods=1)
            .mean()
        )

        return df

    def build_route_segments(self, points):
        rows = []
        for idx in range(len(points) - 1):
            start = points.iloc[idx]
            end = points.iloc[idx + 1]
            distance = self.haversine_m(start["lat"], start["lon"], end["lat"], end["lon"])
            if distance < 1:
                continue

            radius = self.curvature_radius(
                points.iloc[idx-1],
                points.iloc[idx],
                points.iloc[idx+1]
            )

            elevation_gain = end["ele"] - start["ele"]
            rows.append(
                {
                    "distance_m": distance,
                    "start_elevation_m": start["ele"],
                    "end_elevation_m": end["ele"],
                    "elevation_change_m": elevation_gain,
                    "grade": np.clip(elevation_gain / distance, -0.25, 0.25),
                    "bearing": self.bearing_deg(start["lat"], start["lon"], end["lat"], end["lon"]),
                    "corner_radius_m": radius
                }
            )

        segments = pd.DataFrame(rows)
        if segments.empty:
            return segments

        segments["distance_km"] = segments["distance_m"].cumsum() / 1000

        return segments


    def wheel_power_required(self, speed, grade, mass, cda, crr, rho, drivetrain_efficiency, wind_speed, wind_from_deg, bearing):
        slope_angle = math.atan(grade)
        headwind = wind_speed * math.cos(math.radians(wind_from_deg - bearing))
        apparent_air_speed = max(0.0, speed + headwind)
        gravity_power = mass * G * math.sin(slope_angle) * speed
        rolling_power = mass * G * math.cos(slope_angle) * crr * speed
        aero_power = 0.5 * rho * cda * apparent_air_speed**2 * speed
        wheel_power = gravity_power + rolling_power + aero_power
        return wheel_power / drivetrain_efficiency



    def solve_speed_for_power(self, target_power, grade, mass, cda, crr, rho, drivetrain_efficiency, wind_speed, wind_from_deg, bearing, max_speed):
        
        low = 0.1
        high = max_speed
        if self.wheel_power_required(high, grade, mass, cda, crr, rho, drivetrain_efficiency, wind_speed, wind_from_deg, bearing) <= target_power:
            return high

        for _ in range(45):
            mid = (low + high) / 2
            required = self.wheel_power_required(
                mid, grade, mass, cda, crr, rho, drivetrain_efficiency, wind_speed, wind_from_deg, bearing
            )
            if required > target_power:
                high = mid
            else:
                low = mid

        return low


    def normalized_power(self, power, duration_s):
        if len(power) == 0:
            return np.nan

        samples = []
        for watts, seconds in zip(power, duration_s):
            repeat = max(1, int(round(seconds / 5)))
            samples.extend([watts] * repeat)

        power_series = pd.Series(samples)
        rolling_30s = power_series.rolling(6, min_periods=1).mean()
        return (rolling_30s.pow(4).mean()) ** 0.25


    def estimate_course_pacing(self, segments, settings):
        modeled = segments.copy()

        total_mass = (
            settings.rider_weight
            + settings.bike_weight
            + settings.gear_weight
        )

        ftp = settings.ftp
        target_np = ftp * settings.target_if
        max_power = ftp * settings.max_ftp_fraction
        min_power = ftp * settings.min_ftp_fraction

        # ---------- LOAD SCORE (vectorized prep, minimal change) ----------
        load_scores = []

        ref_speed = settings.reference_speed_kmh / 3.6

        for _, segment in modeled.iterrows():
            reference_power = self.wheel_power_required(
                ref_speed,
                segment["grade"],
                total_mass,
                settings.cda_normal,
                settings.crr,
                settings.air_density,
                settings.drivetrain_efficiency,
                settings.wind_speed,
                settings.wind_from_deg,
                segment["bearing"],
            )
            load_scores.append(max(0.0, reference_power))

        load_scores = np.asarray(load_scores)

        denom = (
            np.nanpercentile(load_scores, 90)
            - np.nanmedian(load_scores)
            + 1e-9
        )

        if np.nanmax(load_scores) > 0:
            load_scores = (load_scores - np.nanmedian(load_scores)) / denom
        else:
            load_scores = np.zeros(len(modeled))

        power_shape = 1 + settings.pacing_aggression * np.clip(load_scores, -0.6, 1.2)

        power_shape = np.clip(
            power_shape,
            settings.min_ftp_fraction / settings.target_if,
            settings.max_ftp_fraction / settings.target_if,
        )

        # ---------- PRECOMPUTE ARRAYS (DO ONCE) ----------
        grades = modeled["grade"].to_numpy()
        bearings = modeled["bearing"].to_numpy()
        distances = modeled["distance_m"].to_numpy()
        radii = modeled["corner_radius_m"].to_numpy()

        n = len(modeled)
        best_diff = float("inf")
        best_powers = None
        best_speeds = None
        best_np = None

        low_scale = 0.5
        high_scale = 1.5

        for _ in range(20):  # reduce from 35 → 20 (huge time gain)

            scale = (low_scale + high_scale) / 2
            powers = np.clip(target_np * power_shape * scale, min_power, max_power)

            speeds = np.zeros(n)

            coast_mask = grades < -settings.coast_grade_threshold

            for i in range(n):
                speed = self.solve_speed_for_power(
                    powers[i],
                    grades[i],
                    total_mass,
                    settings.cda_normal,
                    settings.crr,
                    settings.air_density,
                    settings.drivetrain_efficiency,
                    settings.wind_speed,
                    settings.wind_from_deg,
                    bearings[i],
                    settings.max_speed_kmh / 3.6,
                )

                if speed * 3.6 > settings.aero_pos_speed:
                    speed = self.solve_speed_for_power(
                        powers[i],
                        grades[i],
                        total_mass,
                        settings.cda_aero,
                        settings.crr,
                        settings.air_density,
                        settings.drivetrain_efficiency,
                        settings.wind_speed,
                        settings.wind_from_deg,
                        bearings[i],
                        settings.max_speed_kmh / 3.6,
                    )

                if grades[i] < -0.02:
                    speed = min(speed, self.corner_speed_limit(radii[i]))
                if grades[i] < -settings.coast_grade_threshold:
                    speeds[i] = min(
                        self.corner_speed_limit(radii[i]),
                        settings.coast_speed_cap  # optional cap
                    )
                powers[coast_mask] = 0.0

                speeds[i] = speed

            duration_s = distances / np.maximum(speeds, 1e-9)
            current_np = self.normalized_power(powers, duration_s)

            diff = abs(current_np - target_np)

            # keep BEST result, not last result
            if diff < best_diff:
                best_diff = diff
                best_powers = powers.copy()
                best_speeds = speeds.copy()
                best_np = current_np

            # EARLY EXIT (THIS IS KEY)
            if diff < 0.5:   # tweak tolerance (watts normalized power error)
                break

            # binary search update
            if current_np > target_np:
                high_scale = scale
            else:
                low_scale = scale
        # ---------- OUTPUT ----------
        modeled["target_power_w"] = best_powers
        modeled["speed_kmh"] = best_speeds * 3.6
        modeled["segment_time_s"] = modeled["distance_m"] / np.maximum(best_speeds, 1e-9)
        modeled["elapsed_time_s"] = modeled["segment_time_s"].cumsum()

        modeled.attrs["target_np"] = target_np
        modeled.attrs["modeled_np"] = best_np

        return modeled


    def time_weighted_average(self, values, weights):
        values = np.asarray(values, dtype=float)
        weights = np.asarray(weights, dtype=float)
        valid = ~np.isnan(values) & ~np.isnan(weights) & (weights > 0)
        if not valid.any():
            return np.nan
        return np.average(values[valid], weights=weights[valid])

    def wind_component_kmh(self, row, settings):
        # unchanged but this is cheap already
        headwind_ms = settings.wind_speed * math.cos(
            math.radians(settings.wind_from_deg - row.bearing)
        )
        return headwind_ms * 3.6


    def pacing_cheat_sheet(self, modeled, settings):
        category_order = [
            "Flat/Roll\nHeadwind",
            "Flat/Roll\nTailwind",
            "Flat/Roll\nCrosswind",
            "Minor Hill\n(1-2%)",
            "Medium Hill\n(2-4%)",
            "Major Hill\n(4-6%)",
            "Extreme Hill\n(>6%)",
            "Minor\nDescent",
        ]

        cheat = modeled.copy()
        cheat["grade_percent"] = cheat["grade"] * 100
        cheat["headwind_kmh"] = cheat.apply(lambda row: self.wind_component_kmh(row, settings), axis=1)

        def category(row):
            grade = row["grade_percent"]
            if grade <= -1:
                return "Minor\nDescent"
            if grade >= 6:
                return "Extreme Hill\n(>6%)"
            if grade >= 4:
                return "Major Hill\n(4-6%)"
            if grade >= 2:
                return "Medium Hill\n(2-4%)"
            if grade >= 1:
                return "Minor Hill\n(1-2%)"
            if row["headwind_kmh"] >= 2:
                return "Flat/Roll\nHeadwind"
            if row["headwind_kmh"] <= -2:
                return "Flat/Roll\nTailwind"
            return "Flat/Roll\nCrosswind"

        cheat["category"] = cheat.apply(category, axis=1)
        rows = []
        for category_name in category_order:
            category_rows = cheat[cheat["category"] == category_name]
            watts = self.time_weighted_average(category_rows["target_power_w"], category_rows["segment_time_s"])
            rows.append(
                {
                    "CATEGORY": category_name,
                    "WATTS": "" if np.isnan(watts) else int(round(watts)),
                }
            )

        return pd.DataFrame(rows)


    def course_section_summary(self, modeled, min_distance_km=1.0):
        sections = modeled.copy()
        smoothing_window = max(3, min(21, len(sections) // 60))
        if smoothing_window % 2 == 0:
            smoothing_window += 1
        sections["smoothed_grade"] = sections["grade"].rolling(smoothing_window, min_periods=1, center=True).mean()

        def terrain_type(grade):
            if grade >= 0.015:
                return "Climb"
            if grade <= -0.015:
                return "Descent"
            return "Flat/Roll"

        sections["terrain"] = sections["smoothed_grade"].apply(terrain_type)
        sections["section_id"] = (sections["terrain"] != sections["terrain"].shift()).cumsum()

        rows = []
        for _, section in sections.groupby("section_id", sort=False):
            distance_km = section["distance_m"].sum() / 1000
            if distance_km < min_distance_km:
                continue

            start_km = section["distance_km"].iloc[0] - section["distance_m"].iloc[0] / 1000
            end_km = section["distance_km"].iloc[-1]
            time_s = section["segment_time_s"].sum()
            elevation_change_m = section["elevation_change_m"].sum()
            avg_grade = elevation_change_m / section["distance_m"].sum() * 100
            avg_watts = self.time_weighted_average(section["target_power_w"], section["segment_time_s"])
            avg_speed = distance_km / (time_s / 3600)

            rows.append(
                {
                    "Type": section["terrain"].iloc[0],
                    "Start km": round(start_km, 2),
                    "End km": round(end_km, 2),
                    "Distance km": round(distance_km, 2),
                    "Avg grade %": round(avg_grade, 1),
                    "Elevation change m": round(elevation_change_m, 0),
                    "Avg watts": int(round(avg_watts)),
                    "Avg speed km/h": round(avg_speed, 1),
                    "Time min": round(time_s / 60, 1),
                }
            )

        return pd.DataFrame(rows)


    def curvature_radius(self, p1, p2, p3):
        """
        Returns turn radius [m].
        Large value = straight road.
        """

        x1, y1 = p1["x"], p1["y"]
        x2, y2 = p2["x"], p2["y"]
        x3, y3 = p3["x"], p3["y"]

        a = math.hypot(x2 - x1, y2 - y1)
        b = math.hypot(x3 - x2, y3 - y2)
        c = math.hypot(x3 - x1, y3 - y1)

        area2 = abs(
            (x2 - x1) * (y3 - y1) -
            (y2 - y1) * (x3 - x1)
        )

        if area2 < 1e-12:
            return 1e6  # effectively straight line

        return (a * b * c) / (2 * area2)

    def corner_speed_limit(self, radius_m, max_lat_acc=3.0):
        """
        Safe cornering speed based on lateral acceleration limit.
        v = sqrt(a * r)
        """
        return math.sqrt(max_lat_acc * radius_m)
    
    def step_dynamics(self, v, power, dt, grade, mass, cda, crr, rho, eta, wind_ms):
        g = 9.80665

        slope = math.atan(grade)

        v_air = max(0.1, v + wind_ms)

        F_drive = (power * eta) / v

        F_aero = 0.5 * rho * cda * v_air**2

        F_roll = mass * g * crr * math.cos(slope)

        F_gravity = mass * g * math.sin(slope)

        F_net = F_drive - F_aero - F_roll - F_gravity

        a = F_net / mass

        v_new = max(0.1, v + a * dt)

        return v_new
    
    def simulate_segment(self, distance, v0, power, grade, settings, mass):
        dt = 1.0  # 1 second timestep
        x = 0.0
        v = v0

        while x < distance:
            v = self.step_dynamics(
                v=v,
                power=power,
                dt=dt,
                grade=grade,
                mass=mass,
                cda=settings["cda"],
                crr=settings["crr"],
                rho=settings["air_density"],
                eta=settings["drivetrain_efficiency"],
                wind_ms=settings["wind_speed"],
            )

            x += v * dt

        return v