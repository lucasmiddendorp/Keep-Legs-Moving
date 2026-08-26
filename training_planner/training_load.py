"""Calculate day-level TSS targets from a weekly budget."""


def calculate_daily_tss(weekly_tss, day_weights):
    """
    Split weekly TSS across days proportionally.

    Args:
        weekly_tss: Numeric weekly target.
        day_weights: Mapping day_name -> weight (for example available hours).
    """
    if weekly_tss <= 0 or not day_weights:
        return {}

    valid_weights = {
        day: max(0.0, float(weight or 0.0))
        for day, weight in day_weights.items()
        if float(weight or 0.0) > 0
    }

    total_weight = sum(valid_weights.values())
    if total_weight <= 0:
        return {}

    return {
        day: float(weekly_tss) * (weight / total_weight)
        for day, weight in valid_weights.items()
    }