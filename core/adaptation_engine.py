class AdaptationEngine:
    def __init__(self, load_model):
        self.load_model = load_model

    def adapt(self, last_tss, missed_sessions):
        self.load_model.update(last_tss)
        readiness = self.load_model.readiness()

        # Adjust next training day intensity
        if readiness < 0 or missed_sessions > 1:
            return 'Reduce intensity'
        elif readiness > 20:
            return 'Increase intensity'
        else:
            return 'Keep steady'
