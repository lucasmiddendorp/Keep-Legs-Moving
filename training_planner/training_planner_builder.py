"""
Training Planner Builder Module

High-level orchestrator for building training plans using a fluent interface.
Combines Availability, DistributionCalculator, RecoveryAnalyzer, and WorkoutSelector.
"""

from datetime import date, datetime, timedelta
from itertools import combinations
from typing import Dict, List, Optional, Any

from .availability import Availability
from .distribution import DistributionCalculator
from .recovery import RecoveryAnalyzer
from .workout_selection import WorkoutSelector
from helpers.metrics import TRAINING_ZONES, get_training_zone


class TrainingPlanBuilder:
    """High-level interface for building training plans using fluent pattern."""
    
    def __init__(self):
        """Initialize the plan builder."""
        self.availability = None
        self.distribution_calc = None
        self.recovery_analyzer = None
        self.workout_selector = None
    
    def set_availability(self, availability_data: Dict) -> "TrainingPlanBuilder":
        """Set availability data.
        
        Args:
            availability_data: Dictionary with day names as keys and hours/availability data
        
        Returns:
            self for method chaining
        
        Example:
            builder.set_availability({
                "Monday": {"hours": 1.5},
                "Tuesday": {"available": True, "start": "06:00", "end": "07:30"},
                "Wednesday": True,
            })
        """
        self.availability = Availability(availability_data)
        return self
    
    def set_goal_and_phase(
        self, 
        goal: Optional[str] = None, 
        phase: Optional[str] = None
    ) -> "TrainingPlanBuilder":
        """Set training goal and phase.
        
        Args:
            goal: Training goal (e.g., "time_trial", "gran_fondo", "criterium")
            phase: Training phase (e.g., "early", "middle", "late", "taper")
        
        Returns:
            self for method chaining
        
        Example:
            builder.set_goal_and_phase(goal="time_trial", phase="middle")
        """
        self.distribution_calc = DistributionCalculator(goal, phase)
        return self
    
    def set_recovery_profile(
        self, 
        activities: Any = None, 
    ) -> "TrainingPlanBuilder":
        """Set recovery profile from activities.
        
        Args:
            activities: pandas DataFrame or list of activity records
            athlete_level: Optional level (beginner, intermediate, advanced, elite)
        
        Returns:
            self for method chaining
        
        Example:
            builder.set_recovery_profile(activities=df)
        """
        self.recovery_analyzer = RecoveryAnalyzer(activities)
        return self
    
    def set_workouts(self, workouts: List[Dict]) -> "TrainingPlanBuilder":
        """Set workout library.
        
        Args:
            workouts: List of workout dictionaries
        
        Returns:
            self for method chaining
        
        Example:
            builder.set_workouts(workouts_list)
        """
        self.workout_selector = WorkoutSelector(workouts)
        return self
    
    def get_availability(self) -> Optional[Availability]:
        """Get availability instance.
        
        Returns:
            Availability instance or None if not set
        """
        return self.availability
    
    def get_distribution(self) -> Dict[str, float]:
        """Get training distribution.
        
        Returns:
            Dictionary with categories as keys and percentages (0-1) as values
        """
        return self.distribution_calc.calculate() if self.distribution_calc else {}
    
    def get_recovery_profile(self) -> Dict[str, Any]:
        """Get recovery profile.
        
        Returns:
            Dictionary with recovery metrics
        """
        return self.recovery_analyzer.get_profile() if self.recovery_analyzer else {}
    
    def select_workout(
        self,
        category: str,
        target_tss: Optional[float] = None,
        target_min: Optional[float] = None,
        exclude_ids: Optional[set] = None,
        ) -> Optional[Dict]:
        """Select a workout by category, target duration, or target TSS."""
        if not self.workout_selector:
            return None
        return self.workout_selector.select(
            category,
            target_tss=target_tss,
            target_min=target_min,
            exclude_ids=exclude_ids,
        )
    
    def validate_recovery(
        self,
        schedule: List[Dict],
        max_hard_sessions: int = 2,
        min_gap_days: int = 1
    ) -> bool:
        """Validate recovery compliance for a schedule.
        
        Args:
            schedule: List of daily schedule items
            max_hard_sessions: Maximum hard sessions allowed
            min_gap_days: Minimum gap between hard sessions
        
        Returns:
            True if schedule is valid, False otherwise
        """
        if not self.recovery_analyzer:
            return True
        return self.recovery_analyzer.validate_recovery(
            schedule, 
            max_hard_sessions, 
            min_gap_days
        )

    @staticmethod
    def _parse_date(value: Any) -> Optional[date]:
        """Return a date from an ISO date value."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value)).date()
        except ValueError:
            return None

    @staticmethod
    def _phase_for_week(weeks_remaining: int) -> str:
        """Return the planning phase for the remaining time to the goal."""
        if weeks_remaining <= 2:
            return "taper"
        if weeks_remaining <= 5:
            return "late"
        if weeks_remaining <= 10:
            return "middle"
        return "early"

    def _estimate_weekly_training_minutes(
        self,
        week_target_tss: float,
        distribution: Dict[str, float],
    ) -> float:
        """Return a compatibility total from category-specific time targets."""
        return sum(
            self._category_tss_to_minutes(category, week_target_tss * share)
            for category, share in distribution.items()
        )

    def _category_tss_per_minute(self, category: str) -> float:
        """Estimate category load rate from the available workout library."""
        rates = []
        for workout in self.workout_selector.workouts:
            workout_category = self.workout_selector._get_workout_category(workout)
            if workout_category.lower() != category.lower():
                continue
            duration = self._get_workout_zone_minutes(workout).get(category, 0.0)
            if duration > 0:
                rates.append(self.workout_selector._get_workout_tss(workout) / duration)
        if rates:
            rates.sort()
            return rates[len(rates) // 2]
        zone = TRAINING_ZONES.get(category)
        if not zone:
            return 1.0
        lower = zone["min"]
        upper = zone["max"] if zone["max"] != float("inf") else lower + 0.10
        representative_intensity = (lower + upper) / 2
        return max(0.01, 100 * representative_intensity ** 2 / 60)

    def _category_tss_to_minutes(self, category: str, target_tss: float) -> float:
        """Convert a category TSS target using that category's load rate."""
        return float(target_tss) / self._category_tss_per_minute(category)

    def _select_spaced_days(self, candidates: List[str], session_count: int) -> set:
        """Select available days while avoiding clustered training or rest days."""
        if session_count >= len(candidates):
            return set(candidates)
        candidate_set = set(candidates)
        best_days = None
        best_score = None
        for combination in combinations(candidates, session_count):
            selected = set(combination)
            runs = []
            current_run = 0
            for day in self.availability.DAY_ORDER:
                if day in candidate_set and day in selected:
                    current_run += 1
                else:
                    if current_run:
                        runs.append(current_run)
                        current_run = 0
            if current_run:
                runs.append(current_run)
            training_cluster_penalty = sum(run * run for run in runs)
            rest_cluster_penalty = 0
            current_run = 0
            for day in self.availability.DAY_ORDER:
                if day in candidate_set and day not in selected:
                    current_run += 1
                else:
                    if current_run:
                        rest_cluster_penalty += current_run * current_run
                        current_run = 0
            if current_run:
                rest_cluster_penalty += current_run * current_run
            hours = sum(self.availability.get_hours(day) for day in selected)
            score = (
                training_cluster_penalty + rest_cluster_penalty,
                -hours,
            )
            if best_score is None or score < best_score:
                best_score = score
                best_days = selected
        return best_days or set()

    @staticmethod
    def _get_workout_zone_minutes(workout: Optional[Dict]) -> Dict[str, float]:
        """Return step time by the canonical training-zone definitions."""
        zone_minutes = {zone: 0.0 for zone in TRAINING_ZONES}
        for step in (workout or {}).get("steps", []):
            intensity = float(step.get("intensity", 0) or 0) / 100
            duration = float(step.get("duration_seconds", 0) or 0)
            repeat = int(step.get("repeat", 1) or 1)
            zone = get_training_zone(intensity)
            zone_minutes[zone] += duration * repeat / 60
        return zone_minutes

    @staticmethod
    def _workout_total_minutes(workout: Optional[Dict]) -> float:
        """Return total workout time, including repeated steps."""
        return sum(
            float(step.get("duration_seconds", 0) or 0)
            * int(step.get("repeat", 1) or 1)
            / 60
            for step in (workout or {}).get("steps", [])
        )

    @staticmethod
    def _debug_workout_name(workout: Optional[Dict]) -> str:
        if not workout:
            return "None"
        return str(workout.get("id") or workout.get("name") or "Unnamed workout")

    def build_long_term_plan(
        self,
        baseline_tss: float,
        progression: float = 8.0,
        start_date: Optional[date] = None,
        goal_date: Any = None,
        sessions_per_week: Optional[int] = None,
        completed_session_dates: Optional[List[Any]] = None,
        ) -> List[Dict]:
        """Build a long-term plan by matching quality-session time first, then filling remaining TSS with endurance."""
        if not self.availability or not self.distribution_calc or not self.workout_selector:
            raise ValueError("Availability, goal, and workouts must be configured.")
        start = start_date or date.today()
        start -= timedelta(days=start.weekday())
        goal_day = self._parse_date(goal_date)
        end = goal_day if goal_day and goal_day >= start else start + timedelta(days=27)
        available_days = self.availability.get_available_days()
        if not available_days:
            return []
        session_count = sessions_per_week or len(available_days)
        session_count = max(1, min(session_count, len(available_days)))
        day_weights = self.availability.get_day_weights()
        ordered_days = sorted(
            available_days,
            key=lambda day: (
                -day_weights[day],
                self.availability.DAY_ORDER.index(day),
            ),
        )
        completed_dates = {
            completed_date
            for value in completed_session_dates or []
            if (completed_date := self._parse_date(value)) is not None
        }
        plan = []
        week_start = start
        week_number = 1
        while week_start <= end:
            is_current_week = week_start == start
            completed_this_week = {
                completed_date
                for completed_date in completed_dates
                if week_start <= completed_date < week_start + timedelta(days=7)
            }
            remaining_sessions = session_count
            if is_current_week:
                remaining_sessions = max(0, session_count - len(completed_this_week))
            selectable_days = [
                day
                for day in ordered_days
                if week_start + timedelta(days=self.availability.DAY_ORDER.index(day)) not in completed_this_week
                and (
                    not is_current_week
                    or week_start + timedelta(days=self.availability.DAY_ORDER.index(day)) >= date.today()
                )
            ]
            selected_days = self._select_spaced_days(
                selectable_days,
                remaining_sessions,
            )
            weeks_remaining = max(1, ((end - week_start).days + 6) // 7)
            phase = self._phase_for_week(weeks_remaining)
            raw_distribution = DistributionCalculator(
                self.distribution_calc.goal,
                phase,
            ).calculate()
            distribution = raw_distribution.copy()
            quality_category = None
            if session_count <= 3:
                quality_category = max(
                    ("Tempo", "Threshold"),
                    key=lambda category: float(raw_distribution.get(category, 0) or 0),
                )
                quality_share = sum(
                    float(raw_distribution.get(category, 0) or 0)
                    for category in ("Tempo", "Threshold")
                )
                distribution["Tempo"] = quality_share if quality_category == "Tempo" else 0.0
                distribution["Threshold"] = quality_share if quality_category == "Threshold" else 0.0
            deload = week_number % 4 == 0 and phase != "taper"
            week_target_tss = float(baseline_tss) * (
                0.7 if deload else 1 + progression / 100 * week_number
            )
            if phase == "taper":
                week_target_tss *= 0.75
            category_names = (
                "Recovery",
                "Endurance",
                "Tempo",
                "Threshold",
                "VO2max",
                "Anaerobic",
            )
            category_tss_targets = {
                category: week_target_tss * float(distribution.get(category, 0) or 0)
                for category in category_names
            }
            category_minutes = {
                category: self._category_tss_to_minutes(
                    category,
                    category_tss_targets[category],
                )
                for category in category_names
            }
            remaining_category_minutes = category_minutes.copy()
            intensity_budget = {
                "zone_minutes": {
                    **category_minutes,
                    "VO2max": category_minutes["VO2max"] + category_minutes["Anaerobic"],
                    "Anaerobic": 0.0,
                },
            }
            vo2_share = float(distribution.get("VO2max", 0) or 0)
            threshold_share = (
                float(distribution.get("Threshold", 0) or 0)
                + float(distribution.get("Tempo", 0) or 0)
            )
            total_quality_share = vo2_share + threshold_share
            estimated_weekly_minutes = sum(category_minutes.values())
            vo2_target_minutes = remaining_category_minutes["VO2max"]
            vo2_workout = None
            tempo_workout = None
            threshold_workout = None
            vo2_tss = 0.0
            tempo_tss = 0.0
            threshold_tss = 0.0
            if vo2_target_minutes > 0:
                vo2_workout = self.select_workout(
                    "VO2max",
                    target_tss=None,
                    target_min=vo2_target_minutes,
                )
                if vo2_workout:
                    vo2_workout = dict(vo2_workout)
                    vo2_workout.pop("_level", None)
                    vo2_tss = self.workout_selector._get_workout_tss(vo2_workout)
                    vo2_workout["target_tss"] = round(vo2_tss, 0)
                    vo2_workout["estimated_tss"] = round(vo2_tss, 0)
            threshold_category = (
                quality_category
                if quality_category
                else "Threshold" if float(distribution.get("Threshold", 0) or 0) > 0 else None
            )
            if remaining_category_minutes["Tempo"] > 0 and (
                session_count > 3 or threshold_category == "Tempo"
            ):
                tempo_workout = self.select_workout(
                    "Tempo",
                    target_tss=None,
                    target_min=remaining_category_minutes["Tempo"],
                )
                if tempo_workout:
                    tempo_workout = dict(tempo_workout)
                    tempo_workout.pop("_level", None)
                    tempo_tss = self.workout_selector._get_workout_tss(tempo_workout)
                    tempo_workout["target_tss"] = round(tempo_tss, 0)
                    tempo_workout["estimated_tss"] = round(tempo_tss, 0)
            remaining_threshold_minutes = remaining_category_minutes["Threshold"]
            for selected_workout in (vo2_workout, tempo_workout):
                remaining_threshold_minutes -= self._get_workout_zone_minutes(
                    selected_workout
                ).get("Threshold", 0.0)
            remaining_threshold_minutes = max(0.0, remaining_threshold_minutes)
            if threshold_category and remaining_threshold_minutes > 0:
                threshold_workout = self.select_workout(
                    "Threshold",
                    target_tss=None,
                    target_min=remaining_threshold_minutes,
                )
                if threshold_workout:
                    threshold_workout = dict(threshold_workout)
                    threshold_workout.pop("_level", None)
                    threshold_tss = self.workout_selector._get_workout_tss(threshold_workout)
                    threshold_workout["target_tss"] = round(threshold_tss, 0)
                    threshold_workout["estimated_tss"] = round(threshold_tss, 0)

            print("=" * 60)
            print(f"WEEK {week_number} PLANNING DEBUG")
            print("=" * 60)
            print("\nBASELINE / TARGET")
            print(f"baseline_tss:              {baseline_tss:.2f}")
            print(f"progression:               {progression:.2f}%")
            print(f"deload:                    {deload}")
            print(f"phase:                     {phase}")
            print(f"weekly_target_tss:         {week_target_tss:.2f}")
            print("\nDISTRIBUTION")
            print(f"raw distribution:          {raw_distribution!r}")
            print(f"effective distribution:    {distribution!r}")
            for category in category_names:
                print(f"    {category}:              {float(distribution.get(category, 0) or 0) * 100:.2f}%")
            print("\nTSS ALLOCATION BY CATEGORY")
            for category in category_names:
                share = float(distribution.get(category, 0) or 0)
                print(f"{category} TSS target:       {week_target_tss:.2f} x {share:.4f} = {category_tss_targets[category]:.2f}")
            print("\nTIME TARGETS BY CATEGORY")
            for category in category_names:
                rate = self._category_tss_per_minute(category)
                print(f"{category}:                  {category_minutes[category]:.2f} min ({category_tss_targets[category]:.2f} TSS / {rate:.2f} TSS/min)")
            print("\nQUALITY WORKOUT SELECTION")
            print("VO2max target:")
            print(f"    target TSS:             {category_tss_targets['VO2max']:.2f}")
            print(f"    target minutes:         {category_minutes['VO2max']:.2f}")
            print(f"    selected workout:       {self._debug_workout_name(vo2_workout)}")
            print(f"    total duration:         {self._workout_total_minutes(vo2_workout):.2f} min")
            print(f"    VO2max duration:        {self._get_workout_zone_minutes(vo2_workout)['VO2max']:.2f} min")
            print(f"    actual TSS:             {vo2_tss:.2f}")
            print("Tempo target:")
            print(f"    target TSS:             {category_tss_targets['Tempo']:.2f}")
            print(f"    target minutes:         {category_minutes['Tempo']:.2f}")
            print(f"    selected workout:       {self._debug_workout_name(tempo_workout)}")
            print(f"    total duration:         {self._workout_total_minutes(tempo_workout):.2f} min")
            print(f"    Tempo duration:         {self._get_workout_zone_minutes(tempo_workout)['Tempo']:.2f} min")
            print(f"    actual TSS:             {tempo_tss:.2f}")
            print("Threshold target:")
            print(f"    target TSS:             {category_tss_targets['Threshold']:.2f}")
            print(f"    target minutes:         {category_minutes['Threshold']:.2f}")
            print(f"    selected workout:       {self._debug_workout_name(threshold_workout)}")
            print(f"    total duration:         {self._workout_total_minutes(threshold_workout):.2f} min")
            threshold_zone_minutes = self._get_workout_zone_minutes(threshold_workout)
            print(f"    Threshold duration:     {threshold_zone_minutes.get('Threshold', 0):.2f} min")
            print(f"    actual TSS:             {threshold_tss:.2f}")
            remaining_tss = max(
                0.0,
                week_target_tss - vo2_tss - tempo_tss - threshold_tss,
            )
            print("\nREMAINING LOAD")
            print(f"weekly target TSS:         {week_target_tss:.2f}")
            print(f"VO2max actual TSS:         {vo2_tss:.2f}")
            print(f"Tempo actual TSS:          {tempo_tss:.2f}")
            print(f"Threshold actual TSS:      {threshold_tss:.2f}")
            print(f"remaining TSS:             {remaining_tss:.2f}")
            quality_workouts = []
            if vo2_workout:
                quality_workouts.append(("VO2max", vo2_workout))
            if tempo_workout:
                quality_workouts.append(("Tempo", tempo_workout))
            if threshold_workout:
                quality_workouts.append((
                    "Threshold",
                    threshold_workout,
                ))
            quality_days = [
                day
                for day in self.availability.DAY_ORDER
                if day in selected_days and day in {"Tuesday", "Thursday"}
            ]
            quality_days.extend(
                day
                for day in self.availability.DAY_ORDER
                if day in selected_days and day not in quality_days
            )
            quality_assignments = {}
            for index, (category, workout) in enumerate(quality_workouts):
                if index < len(quality_days):
                    quality_assignments[quality_days[index]] = (
                        category,
                        workout,
                    )
            endurance_days = [
                day
                for day in selected_days
                if day not in quality_assignments
            ]
            endurance_tss_per_day = (
                category_tss_targets["Endurance"] / len(endurance_days)
                if endurance_days
                else 0.0
            )
            remaining_endurance_minutes = remaining_category_minutes["Endurance"]
            endurance_minutes_per_day = (
                remaining_endurance_minutes / len(endurance_days)
                if endurance_days
                else 0.0
            )
            print("\nENDURANCE SELECTION")
            print(f"Endurance TSS target:          {category_tss_targets['Endurance']:.2f}")
            print(f"Endurance minutes to distribute: {remaining_endurance_minutes:.2f}")
            print(f"Number of endurance days:     {len(endurance_days)}")
            print(f"Target minutes per endurance day: {endurance_minutes_per_day:.2f}")
            selected_endurance = []
            used_endurance_ids = set()
            for offset, day_name in enumerate(self.availability.DAY_ORDER):
                current_day = week_start + timedelta(days=offset)
                if current_day > end:
                    break
                if day_name not in selected_days:
                    plan.append({
                        "date": current_day.isoformat(),
                        "day": day_name,
                        "rest": True,
                        "week_number": week_number,
                        "week_target_tss": round(week_target_tss, 0),
                        "deload": deload,
                        "intensity_budget": intensity_budget,
                    })
                    continue
                if day_name in quality_assignments:
                    category, workout = quality_assignments[day_name]
                    actual_tss = float(workout.get("target_tss", 0) or 0)
                    plan.append({
                        "date": current_day.isoformat(),
                        "day": day_name,
                        "category": category,
                        "target_tss": round(actual_tss, 0),
                        "actual_tss": round(actual_tss, 0),
                        "workout": workout,
                        "rest": False,
                        "week_number": week_number,
                        "week_target_tss": round(week_target_tss, 0),
                        "deload": deload,
                        "intensity_budget": intensity_budget,
                    })
                    continue
                workout = self.select_workout(
                    "Endurance",
                    target_tss=None,
                    target_min=endurance_minutes_per_day,
                    exclude_ids=used_endurance_ids,
                )
                if workout:
                    workout = dict(workout)
                    workout.pop("_level", None)
                    actual_tss = self.workout_selector._get_workout_tss(workout)
                    workout["target_tss"] = round(actual_tss, 0)
                    workout["estimated_tss"] = round(actual_tss, 0)
                    used_endurance_ids.add(workout.get("id"))
                else:
                    actual_tss = 0.0
                selected_endurance.append((day_name, workout, actual_tss))
                plan.append({
                    "date": current_day.isoformat(),
                    "day": day_name,
                    "category": "Endurance",
                    "target_tss": round(endurance_tss_per_day, 0),
                    "actual_tss": round(actual_tss, 0),
                    "workout": workout,
                    "rest": False,
                    "week_number": week_number,
                    "week_target_tss": round(week_target_tss, 0),
                    "deload": deload,
                    "intensity_budget": intensity_budget,
                })
            print("Selected endurance workouts:")
            for day_name, workout, actual_tss in selected_endurance:
                if day_name not in endurance_days:
                    continue
                print(f"    {day_name}:")
                print(f"        workout:             {self._debug_workout_name(workout)}")
                print(f"        duration:            {self._workout_total_minutes(workout):.2f} min")
                print(f"        actual TSS:          {actual_tss:.2f}")
            selected_workouts = [
                (
                    category,
                    workout,
                    float(workout.get("target_tss", 0) or 0),
                )
                for category, workout in quality_assignments.values()
            ]
            selected_workouts.extend(
                ("Endurance", workout, actual_tss)
                for _, workout, actual_tss in selected_endurance
                if workout
            )
            actual_planned_tss = sum(item[2] for item in selected_workouts)
            selected_zone_minutes = {category: 0.0 for category in category_names}
            selected_category_tss = {category: 0.0 for category in category_names}
            for category, workout, actual_tss in selected_workouts:
                selected_category_tss[category] += actual_tss
                for zone, minutes in self._get_workout_zone_minutes(workout).items():
                    selected_zone_minutes[zone] += minutes
            print("\nFINAL WEEK")
            print(f"Target TSS:                 {week_target_tss:.2f}")
            print(f"Actual planned TSS:        {actual_planned_tss:.2f}")
            print(f"Unmet TSS:                  {max(0.0, week_target_tss - actual_planned_tss):.2f}")
            print("\nZONE MINUTES FROM SELECTED WORKOUTS")
            for category in category_names:
                print(f"{category}:                  {selected_zone_minutes[category]:.2f} min")
            print("\nTARGET RECONCILIATION")
            print("---------------------")
            print(f"Weekly TSS target:             {week_target_tss:.2f}")
            print("Category TSS targets:")
            for category in category_names:
                print(f"    {category}:                  {category_tss_targets[category]:.2f}")
            print(f"Category TSS total:             {sum(category_tss_targets.values()):.2f}")
            print("\nSelected workout TSS:")
            for category in category_names:
                print(f"    {category}:                  {selected_category_tss[category]:.2f}")
            print(f"Selected workout TSS total:     {actual_planned_tss:.2f}")
            print(f"Difference from weekly target: {actual_planned_tss - week_target_tss:.2f}")
            week_start += timedelta(weeks=1)
            week_number += 1
        # print(plan[:7])
        return plan