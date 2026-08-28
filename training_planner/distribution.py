"""Determine weekly category distribution based on goal."""


def calculate_distribution(goal=None, phase=None):
    """Return a normalized category distribution for a goal and training phase."""
    base = {
        "VO2max": 0.15,
        "Threshold": 0.25,
        "Tempo": 0.20,
        "Endurance": 0.40,
    }

    goal_text = str(goal or "").strip().lower().replace("_", " ")

    if not goal_text:
        goal_distribution = base
    elif "endurance" in goal_text or "gran fondo" in goal_text or "long" in goal_text:
        goal_distribution = {
            "VO2max": 0.10,
            "Threshold": 0.20,
            "Tempo": 0.20,
            "Endurance": 0.50,
        }
    elif "time trial" in goal_text or "tt" == goal_text:
        goal_distribution = {
            "VO2max": 0.10,
            "Threshold": 0.35,
            "Tempo": 0.25,
            "Endurance": 0.30,
        }
    elif "race" in goal_text or "criterium" in goal_text or "crit" in goal_text:
        goal_distribution = {
            "VO2max": 0.22,
            "Threshold": 0.28,
            "Tempo": 0.20,
            "Endurance": 0.30,
        }
    else:
        goal_distribution = base

    phase_distribution = {
        "early": {"VO2max": 0.05, "Threshold": 0.20, "Tempo": 0.30, "Endurance": 0.45},
        "middle": {"VO2max": 0.10, "Threshold": 0.30, "Tempo": 0.25, "Endurance": 0.35},
        "late": {"VO2max": 0.20, "Threshold": 0.30, "Tempo": 0.20, "Endurance": 0.30},
        "taper": {"VO2max": 0.05, "Threshold": 0.15, "Tempo": 0.25, "Endurance": 0.55},
    }.get(phase)

    if phase_distribution:
        combined = {
            category: goal_distribution[category] * 0.45 + phase_distribution[category] * 0.55
            for category in goal_distribution
        }
        total = sum(combined.values())
        return {category: value / total for category, value in combined.items()}

    return goal_distribution