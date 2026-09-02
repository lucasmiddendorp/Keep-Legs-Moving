"""Workout Selection Module
Selects workouts based on category, quality-zone duration, or TSS target.
"""

from typing import Dict, List, Optional

from helpers.metrics import TRAINING_ZONES


class WorkoutSelector:
    """Select workouts from a library based on category, zone duration, or TSS."""

    def __init__(self, workouts: List[Dict]):
        self.workouts = workouts or []

    @staticmethod
    def _normalize_category(value) -> str:
        """Normalize category names for reliable matching."""
        return (
            str(value or "")
            .strip()
            .casefold()
            .replace("-", "")
            .replace("_", "")
            .replace(" ", "")
        )

    @classmethod
    def _get_workout_category(cls, workout: Dict) -> str:
        return (
            workout.get("category")
            or workout.get("_category")
            or ""
        )

    @staticmethod
    def _get_workout_duration(workout: Dict) -> float:
        """Return total workout duration in seconds."""

        if workout.get("duration_seconds") is not None:
            return float(workout.get("duration_seconds") or 0)

        if workout.get("duration_minutes") is not None:
            return float(workout.get("duration_minutes") or 0) * 60

        steps = workout.get("steps") or []

        return sum(
            float(step.get("duration_seconds", 0) or 0)
            * int(step.get("repeat", 1) or 1)
            for step in steps
        )

    @staticmethod
    def _get_workout_tss(workout: Dict) -> float:
        """Return workout TSS, calculated from steps when available."""

        steps = workout.get("steps") or []

        if steps:
            total_seconds = 0.0
            weighted_load = 0.0

            for step in steps:
                duration = float(
                    step.get("duration_seconds", 0) or 0
                )
                repeat = int(
                    step.get("repeat", 1) or 1
                )
                intensity = float(
                    step.get("intensity", 0) or 0
                ) / 100

                total_seconds += duration * repeat
                weighted_load += (
                    duration
                    * repeat
                    * intensity ** 2
                )

            if total_seconds > 0:
                return weighted_load / 3600 * 100

        return float(
            workout.get(
                "target_tss",
                workout.get("estimated_tss", 0),
            ) or 0
        )

    @staticmethod
    def _intensity_to_zone(intensity: float) -> str:
        """Convert FTP intensity percentage to a training zone."""

        ratio = float(intensity) / 100

        for zone, limits in TRAINING_ZONES.items():
            if limits["min"] <= ratio < limits["max"]:
                return zone

        return "Anaerobic"

    @classmethod
    def _get_workout_zone_minutes(
        cls,
        workout: Dict,
    ) -> Dict[str, float]:
        """Return minutes spent in every training zone."""

        zone_minutes = {
            zone: 0.0
            for zone in TRAINING_ZONES
        }

        for step in workout.get("steps") or []:
            duration = float(
                step.get("duration_seconds", 0) or 0
            )
            repeat = int(
                step.get("repeat", 1) or 1
            )
            intensity = float(
                step.get("intensity", 0) or 0
            )

            if duration <= 0:
                continue

            zone = cls._intensity_to_zone(intensity)

            zone_minutes[zone] += (
                duration * repeat / 60
            )

        return zone_minutes

    @classmethod
    def get_workout_zone_minutes(
        cls,
        workout: Dict,
    ) -> Dict[str, float]:
        """
        Public method returning the complete zone contribution
        of a workout.

        This is used by the training-plan builder to account for
        workouts that contribute to multiple quality zones.
        """
        return cls._get_workout_zone_minutes(workout)
    
    @classmethod
    def _subtract_workout_zone_minutes(
        cls,
        category_minutes: Dict[str, float],
        workout: Optional[Dict],
    ) -> Dict[str, float]:
        """Subtract the training-zone contribution of a workout from remaining targets."""
        if not workout:
            return category_minutes

        zone_minutes = cls._get_workout_zone_minutes(workout)

        for zone, minutes in zone_minutes.items():
            if zone in category_minutes:
                category_minutes[zone] = max(
                    0.0,
                    category_minutes[zone] - minutes,
                )

        return category_minutes
    
    @classmethod
    def _get_workout_quality_minutes(
        cls,
        workout: Dict,
        category: str,
    ) -> float:
        """Return minutes spent in the requested training category."""

        zone_minutes = cls._get_workout_zone_minutes(workout)

        normalized = cls._normalize_category(category)

        aliases = {
            "vo2max": "VO2max",
            "vo2": "VO2max",
            "threshold": "Threshold",
            "tempo": "Tempo",
            "endurance": "Endurance",
            "recovery": "Recovery",
            "anaerobic": "Anaerobic",
        }

        zone_name = aliases.get(
            normalized,
            category,
        )

        return float(
            zone_minutes.get(zone_name, 0.0)
        )

    def select(
        self,
        category: str,
        target_tss: Optional[float] = None,
        target_min: Optional[float] = None,
        exclude_ids: Optional[set] = None,
    ) -> Optional[Dict]:
        """
        Select the workout closest to the requested target.

        Selection is based on the workout's declared category,
        while target_min is matched against the actual time spent
        in the requested training zone.
        """

        normalized_category = self._normalize_category(category)

        options = [
            workout
            for workout in self.workouts
            if self._normalize_category(
                self._get_workout_category(workout)
            ) == normalized_category
            and (
                not exclude_ids
                or workout.get("id") not in exclude_ids
            )
        ]

        if not options:
            return None

        if target_min is not None:
            target_min = float(target_min)

            return min(
                options,
                key=lambda workout: abs(
                    self._get_workout_quality_minutes(
                        workout,
                        category,
                    )
                    - target_min
                ),
            )

        if target_tss is not None:
            target_tss = float(target_tss)

            return min(
                options,
                key=lambda workout: abs(
                    self._get_workout_tss(workout)
                    - target_tss
                ),
            )

        return options[0]