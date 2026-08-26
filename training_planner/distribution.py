"""Determine weekly category distribution based on goal."""


def calculate_distribution(goal=None):
    """Return a normalized category distribution for the selected goal."""
    base = {
        "VO2max": 0.15,
        "Threshold": 0.25,
        "Tempo": 0.20,
        "Endurance": 0.40,
    }

    goal_text = str(goal or "").strip().lower()

    if not goal_text:
        return base

    if "endurance" in goal_text or "gran fondo" in goal_text or "long" in goal_text:
        return {
            "VO2max": 0.10,
            "Threshold": 0.20,
            "Tempo": 0.20,
            "Endurance": 0.50,
        }

    if "time trial" in goal_text or "tt" == goal_text:
        return {
            "VO2max": 0.10,
            "Threshold": 0.35,
            "Tempo": 0.25,
            "Endurance": 0.30,
        }

    if "race" in goal_text or "criterium" in goal_text or "crit" in goal_text:
        return {
            "VO2max": 0.22,
            "Threshold": 0.28,
            "Tempo": 0.20,
            "Endurance": 0.30,
        }

    return base