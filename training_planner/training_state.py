def evaluate_training_state(athlete):

    history = athlete.history

    if not history:
        return {
            "state": "Normal",
            "ctl_change": 0,
            "atl_change": 0,
            "tsb": athlete.tsb
        }

    history = sorted(
        history,
        key=lambda x: x["date"]
    )

    recent = history[-7:]

    first = recent[0]
    last = recent[-1]

    ctl_change = (
        last["CTL"]
        -
        first["CTL"]
    )

    atl_change = (
        last["ATL"]
        -
        first["ATL"]
    )

    tsb = last["TSB"]

    if tsb < -30:
        state = "Recovery"

    elif atl_change > ctl_change + 10:
        state = "Fatigued"

    elif tsb > 10:
        state = "Fresh"

    else:
        state = "Normal"

    return {
        "state": state,
        "ctl_change": ctl_change,
        "atl_change": atl_change,
        "tsb": tsb
    }