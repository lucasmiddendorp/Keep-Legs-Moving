def determine_phase(days_to_goal):

    if days_to_goal > 84:
        return "Base"

    if days_to_goal > 35:
        return "Build"

    if days_to_goal > 10:
        return "Peak"

    return "Taper"


TARGET_TSB = {
    "Base": (-5, -15),
    "Build": (-10, -30),
    "Peak": (-5, 5),
    "Taper": (5, 20),
}


TARGET_CTL_RAMP = {
    "Base": 0.3,
    "Build": 0.8,
    "Peak": 0.2,
    "Taper": -0.2,
}