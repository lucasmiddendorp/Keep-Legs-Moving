from dataclasses import dataclass, field
from datetime import date


@dataclass
class Athlete:

    ftp: int

    ctl: float

    atl: float

    tsb: float

    level: str = 'Advanced'

    history: list = field(default_factory=list)
    availability: dict = field(default_factory=dict)


@dataclass
class Goal:
    name: str
    race_date: date
    priority: str = "A"


@dataclass
class Workout:

    name: str

    category: str

    intervals: list

    duration_min: int = 0

    tss: float = 0

    intensity_factor: float = 0

@dataclass
class TrainingDay:
    date: date
    phase: str
    workout: Workout | None = None
    completed: bool = False