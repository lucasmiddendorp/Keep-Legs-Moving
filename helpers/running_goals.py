# =========================================================
# Running goal definitions
# =========================================================
RUNNING_GOALS = {
    "General Fitness": {
        "key": "general_fitness",
        "name": "General Fitness",
        "typical_long_run": (45, 90),
        "priority": {
            "endurance": 0.30,
            "tempo": 0.20,
            "threshold": 0.15,
            "vo2max": 0.10,
            "speed": 0.05,
            "recovery": 0.20,
        },
        "max_hard_sessions": 2,
    },
    "5K": {
        "key": "5k",
        "name": "5K",
        "typical_long_run": (60, 90),
        "priority": {
            "endurance": 0.20,
            "tempo": 0.20,
            "threshold": 0.25,
            "vo2max": 0.25,
            "speed": 0.10,
        },
        "max_hard_sessions": 2,
    },
    "10K": {
        "key": "10k",
        "name": "10K",
        "typical_long_run": (75, 110),
        "priority": {
            "endurance": 0.30,
            "tempo": 0.20,
            "threshold": 0.25,
            "vo2max": 0.20,
            "speed": 0.05,
        },
        "max_hard_sessions": 2,
    },
    "Half Marathon": {
        "key": "half_marathon",
        "name": "Half Marathon",
        "typical_long_run": (90, 150),
        "priority": {
            "endurance": 0.40,
            "tempo": 0.20,
            "threshold": 0.25,
            "vo2max": 0.10,
            "speed": 0.05,
        },
        "max_hard_sessions": 2,
    },
    "Marathon": {
        "key": "marathon",
        "name": "Marathon",
        "typical_long_run": (120, 210),
        "priority": {
            "endurance": 0.55,
            "tempo": 0.15,
            "threshold": 0.15,
            "vo2max": 0.10,
            "speed": 0.05,
        },
        "max_hard_sessions": 2,
    },
}