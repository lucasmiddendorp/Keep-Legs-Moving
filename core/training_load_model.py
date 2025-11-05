class LoadModel:
    def __init__(self, tau_fitness=42, tau_fatigue=7):
        self.tau_fitness = tau_fitness
        self.tau_fatigue = tau_fatigue
        self.fitness = []
        self.fatigue = []

    def update(self, tss):
        if not self.fitness:
            self.fitness.append(tss)
            self.fatigue.append(tss)
        else:
            self.fitness.append(self.fitness[-1] + (tss - self.fitness[-1]) / self.tau_fitness)
            self.fatigue.append(self.fatigue[-1] + (tss - self.fatigue[-1]) / self.tau_fatigue)

    def readiness(self):
        return self.fitness[-1] - self.fatigue[-1]
