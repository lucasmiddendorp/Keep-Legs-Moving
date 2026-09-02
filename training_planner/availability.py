"""
Availability Module

Manages training availability logic and day weights.
Replaces the functional helpers/availability.py
"""

from datetime import datetime
from typing import Dict, List, Any, Optional


class Availability:
    """Manages training availability logic and day weights."""
    
    DAY_ORDER = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    
    def __init__(self, availability_data: Dict):
        """Initialize with availability data dictionary."""
        self.data = availability_data or {}
    
    @staticmethod
    def _hours_from_window(start: str, end: str) -> float:
        """Calculate training hours from time window."""
        if not start or not end:
            return 0.0
        
        try:
            start_dt = datetime.strptime(start, "%H:%M")
            end_dt = datetime.strptime(end, "%H:%M")
        except Exception:
            return 0.0
        
        delta = (end_dt - start_dt).total_seconds() / 3600.0
        return max(0.0, delta)
    
    @staticmethod
    def _extract_day_hours(day_data: Any) -> float:
        """Extract training hours from mixed availability formats."""
        if isinstance(day_data, bool):
            return 1.0 if day_data else 0.0
        
        if not isinstance(day_data, dict):
            return 0.0
        
        if "hours" in day_data:
            return max(0.0, float(day_data.get("hours", 0) or 0))
        
        if not day_data.get("available", False):
            return 0.0
        
        return Availability._hours_from_window(
            day_data.get("start"), 
            day_data.get("end")
        )
    
    def get_day_weights(self) -> Dict[str, float]:
        """Return day->weight mapping for available days."""
        weights = {}
        
        for day in self.DAY_ORDER:
            hours = self._extract_day_hours(self.data.get(day, {}))
            if hours > 0:
                # Keep at least a small positive weight to avoid zero-day allocation
                weights[day] = max(0.5, hours)
        
        return weights
    
    def get_available_days(self) -> List[str]:
        """Return available days ordered Monday..Sunday."""
        return list(self.get_day_weights().keys())
    
    def get_hours(self, day: str) -> float:
        """Get hours available for a specific day."""
        return self._extract_day_hours(self.data.get(day, {}))
    
    def has_available_day(self) -> bool:
        """Check if at least one day is available."""
        return len(self.get_available_days()) > 0
