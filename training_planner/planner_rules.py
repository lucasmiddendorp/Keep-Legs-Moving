# helpers/planning_rules.py

from datetime import date, datetime

SESSION_PRIORITY = ["Endurance", "VO2max", "Tempo", "Threshold", "Endurance", "VO2max"]

GOAL_DISTRIBUTION = {
    "General Fitness": {
        "Endurance": 0.30,
        "VO2max": 0.20,
        "Tempo": 0.25,
        "Threshold": 0.25,
    },
    "Gran Fondo": {
        "Endurance": 0.45,
        "VO2max": 0.15,
        "Tempo": 0.20,
        "Threshold": 0.20,
    },
    "Race": {
        "Endurance": 0.20,
        "VO2max": 0.40,
        "Tempo": 0.15,
        "Threshold": 0.25,
    },
}

VO2MAX_MAX_TSS = 60


def _parse_goal_date(goal_date):
    if not goal_date:
        return None
    try:
        return datetime.fromisoformat(str(goal_date)).date()
    except Exception:
        return None


def get_training_phase(goal_date):
    goal_day = _parse_goal_date(goal_date)
    if goal_day is None:
        return "default"

    days_out = (goal_day - date.today()).days
    if days_out <= 14:
        return "taper"
    if days_out <= 42:
        return "late"
    if days_out <= 84:
        return "middle"
    return "early"


PHASE_SESSION_PRIORITY = {
    "default": SESSION_PRIORITY,
    "early": ["Endurance", "Tempo", "Endurance", "Threshold", "Endurance", "VO2max"],
    "middle": ["Endurance", "Tempo", "Threshold", "Endurance", "VO2max", "Threshold"],
    "late": ["Endurance", "VO2max", "Threshold", "VO2max", "Tempo", "Threshold"],
    "taper": ["Endurance", "VO2max", "Tempo", "Endurance", "Threshold", "Endurance"],
}


PHASE_DISTRIBUTION = {
    "early": {"Endurance": 0.45, "Tempo": 0.30, "Threshold": 0.20, "VO2max": 0.05},
    "middle": {"Endurance": 0.35, "Tempo": 0.25, "Threshold": 0.30, "VO2max": 0.10},
    "late": {"Endurance": 0.25, "Tempo": 0.20, "Threshold": 0.25, "VO2max": 0.30},
    "taper": {"Endurance": 0.40, "Tempo": 0.20, "Threshold": 0.20, "VO2max": 0.20},
}

def get_session_categories(training_days, phase="default"):
    """Return categories for this week."""
    training_days = max(1, int(training_days or 1))
    priority = PHASE_SESSION_PRIORITY.get(phase, SESSION_PRIORITY)

    categories = []
    while len(categories) < training_days:
        categories.extend(priority)

    categories = categories[:training_days]

    # Rule: if there are more than 4 sessions, include an extra endurance session.
    if training_days > 4 and categories.count("Endurance") < 2:
        categories[-1] = "Endurance"

    return categories

def get_goal_distribution(goal):
    """Return the TSS distribution for the selected training goal."""
    return GOAL_DISTRIBUTION.get(goal, GOAL_DISTRIBUTION["General Fitness"])


def normalize_distribution_for_categories(goal, categories, phase="default"):
    """Normalize distribution for used categories."""
    if phase in PHASE_DISTRIBUTION:
        distribution = PHASE_DISTRIBUTION[phase]
    else:
        distribution = get_goal_distribution(goal)
    active = {
        category: float(distribution.get(category, 0.0))
        for category in set(categories)
    }

    total = sum(active.values())
    if total <= 0:
        size = max(1, len(active))
        return {category: 1.0 / size for category in active}

    return {
        category: value / total
        for category, value in active.items()
    }

def get_category_tss(weekly_tss, category, goal):
    """Calculate the target TSS for a category based on the selected goal."""
    distribution = get_goal_distribution(goal)
    return weekly_tss * distribution.get(category, 0)

def get_vo2max_budget(weekly_tss, goal):
    """Limit VO2max TSS so high weekly volume does not force an excessive VO2max workout."""
    target = get_category_tss(weekly_tss, "VO2max", goal)
    return min(target, VO2MAX_MAX_TSS)

def get_required_categories(training_days):
    """Return the mandatory training categories."""
    categories = get_session_categories(training_days)
    return [category for category in ["Endurance", "VO2max"] if category in categories]

def get_category_priority(category):
    """Return the priority of a training category."""
    return SESSION_PRIORITY.index(category) if category in SESSION_PRIORITY else len(SESSION_PRIORITY)