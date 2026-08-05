from datetime import timedelta


TRAINING_GOALS = {

    "General Fitness": {
        "description":
            "Build a sustainable fitness base with balanced endurance, strength, and moderate intensity sessions. "
            "Ideal for staying healthy and improving overall cycling ability.",

        "weeks": 52,

        "distribution": {
            "Endurance": 0.45,
            "Tempo": 0.20,
            "Threshold": 0.15,
            "VO2 Max": 0.10,
            "Recovery": 0.10,
        },
    },


    "Gran Fondo": {
        "description":
            "Prepare for long cycling events by increasing endurance, climbing ability, and pacing skills. "
            "Includes long rides, tempo blocks, and race-specific efforts.",

        "weeks": 16,

        "distribution": {
            "Endurance": 0.45,
            "Tempo": 0.20,
            "Threshold": 0.20,
            "VO2 Max": 0.10,
            "Recovery": 0.05,
        },
    },


    "FTP Improvement": {
        "description":
            "Increase your sustainable power output by targeting threshold development. "
            "Training includes sweet spot, tempo, and threshold intervals to raise your FTP.",

        "weeks": 12,

        "distribution": {
            "Endurance": 0.25,
            "Tempo": 0.30,
            "Threshold": 0.30,
            "VO2 Max": 0.10,
            "Recovery": 0.05,
        },
    },


    "VO2 Max": {
        "description":
            "Improve your ability to produce high power for short durations. "
            "Training focuses on hard intervals above FTP to increase oxygen uptake and maximum aerobic power.",

        "weeks": 8,

        "distribution": {
            "Endurance": 0.20,
            "Tempo": 0.15,
            "Threshold": 0.20,
            "VO2 Max": 0.40,
            "Recovery": 0.05,
        },
    },


    "Time Trial": {
        "description":
            "Develop the ability to maintain high power for a prolonged effort. "
            "Training combines threshold intervals, aerodynamic pacing, and race-specific intensity.",

        "weeks": 14,

        "distribution": {
            "Endurance": 0.30,
            "Tempo": 0.25,
            "Threshold": 0.30,
            "VO2 Max": 0.10,
            "Recovery": 0.05,
        },
    },


    "Fully-Polarized": {
        "description":
            "Improve cycling performance with a mix of low-intensity endurance and high-intensity intervals. ",

        "weeks": 12,

        "distribution": {
            "Endurance": 0.35,
            "Tempo": 0.35,
            "Threshold": 0.0,
            "VO2 Max": 0.20,
            "Recovery": 0.05,
        },
    },


    "Road Race": {
        "description":
            "Prepare for competition by combining endurance, intensity, recovery, and race-specific sessions. "
            "The plan gradually builds fitness while managing fatigue before the event.",

        "weeks": 16,

        "distribution": {
            "Endurance": 0.30,
            "Tempo": 0.15,
            "Threshold": 0.25,
            "VO2 Max": 0.25,
            "Recovery": 0.05,
        },
    },
}


def get_goal(name):
    return TRAINING_GOALS[name]


def get_goal_description(name):
    return TRAINING_GOALS[name]["description"]


def get_goal_distribution(name):
    return TRAINING_GOALS[name]["distribution"]


def get_goal_duration(name):
    return TRAINING_GOALS[name]["weeks"]


def weeks_to_goal(goal_date, today):
    return max((goal_date - today).days / 7, 0)