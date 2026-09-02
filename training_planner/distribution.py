"""
Distribution Module

Calculates training category distribution based on goal and phase.
Replaces the functional helpers/distribution.py
"""

from typing import Dict, Optional


class DistributionCalculator:
    """Calculates training category distribution based on goal and phase."""
    
    BASE_DISTRIBUTION = {
        "VO2max": 0.15,
        "Threshold": 0.25,
        "Tempo": 0.20,
        "Endurance": 0.40,
    }
    
    GOAL_DISTRIBUTIONS = {
        "endurance": {
            "VO2max": 0.10,
            "Threshold": 0.20,
            "Tempo": 0.20,
            "Endurance": 0.50,
        },
        "gran_fondo": {
            "VO2max": 0.10,
            "Threshold": 0.20,
            "Tempo": 0.20,
            "Endurance": 0.50,
        },
        "time_trial": {
            "VO2max": 0.10,
            "Threshold": 0.35,
            "Tempo": 0.25,
            "Endurance": 0.30,
        },
        "tt": {
            "VO2max": 0.10,
            "Threshold": 0.35,
            "Tempo": 0.25,
            "Endurance": 0.30,
        },
        "race": {
            "VO2max": 0.22,
            "Threshold": 0.28,
            "Tempo": 0.20,
            "Endurance": 0.30,
        },
        "criterium": {
            "VO2max": 0.22,
            "Threshold": 0.28,
            "Tempo": 0.20,
            "Endurance": 0.30,
        },
        "crit": {
            "VO2max": 0.22,
            "Threshold": 0.28,
            "Tempo": 0.20,
            "Endurance": 0.30,
        },
    }
    
    PHASE_DISTRIBUTIONS = {
        "early": {"VO2max": 0.05, "Threshold": 0.20, "Tempo": 0.30, "Endurance": 0.45},
        "middle": {"VO2max": 0.10, "Threshold": 0.30, "Tempo": 0.25, "Endurance": 0.35},
        "late": {"VO2max": 0.20, "Threshold": 0.30, "Tempo": 0.20, "Endurance": 0.30},
        "taper": {"VO2max": 0.05, "Threshold": 0.15, "Tempo": 0.25, "Endurance": 0.55},
    }
    
    def __init__(self, goal: Optional[str] = None, phase: Optional[str] = None):
        """Initialize with goal and phase.
        
        Args:
            goal: Training goal (e.g., "time_trial", "gran_fondo", "criterium")
            phase: Training phase (e.g., "early", "middle", "late", "taper")
        """
        self.goal = goal
        self.phase = phase
    
    def _normalize_goal(self, goal_text: str) -> str:
        """Normalize goal text for lookup."""
        return goal_text.strip().lower().replace("_", " ").replace("-", " ")
    
    def _get_goal_distribution(self) -> Dict[str, float]:
        """Get distribution for the training goal."""
        if not self.goal:
            return self.BASE_DISTRIBUTION.copy()
        
        normalized = self._normalize_goal(str(self.goal))
        
        # Check for matches
        for key, dist in self.GOAL_DISTRIBUTIONS.items():
            if key in normalized or normalized in key:
                return dist.copy()
        
        return self.BASE_DISTRIBUTION.copy()
    
    def calculate(self) -> Dict[str, float]:
        """Return normalized category distribution for goal and phase.
        
        Returns:
            Dictionary with categories as keys and percentages (0-1) as values.
            Total always sums to 1.0
        """
        goal_distribution = self._get_goal_distribution()
        
        if not self.phase or self.phase not in self.PHASE_DISTRIBUTIONS:
            return goal_distribution
        
        phase_distribution = self.PHASE_DISTRIBUTIONS[self.phase]
        
        # Blend goal (45%) and phase (55%) distributions
        combined = {
            category: (
                goal_distribution[category] * 0.45 
                + phase_distribution[category] * 0.55
            )
            for category in goal_distribution
        }
        
        # Normalize
        total = sum(combined.values())
        return {category: value / total for category, value in combined.items()}
