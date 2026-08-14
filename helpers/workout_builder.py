from dataclasses import dataclass
from typing import Optional


# =========================================================
# Training zones
# =========================================================

CYCLING_ZONES = [
    (0, 55, "Z1", "Recovery"),
    (55, 76, "Z2", "Endurance"),
    (76, 91, "Z3", "Tempo"),
    (91, 106, "Z4", "Threshold"),
    (106, 121, "Z5", "VO₂max"),
    (121, 151, "Z6", "Anaerobic"),
    (151, 999, "Z7", "Neuromuscular"),
]

RUNNING_ZONES = [
    (0, 76, "Easy", "Recovery / Easy"),
    (76, 86, "Aerobic", "Endurance"),
    (86, 96, "Tempo", "Tempo"),
    (96, 101, "Threshold", "Threshold"),
    (101, 106, "VO₂max", "VO₂max"),
    (106, 999, "Speed", "Anaerobic / Speed"),
]


@dataclass
class WorkoutStep:
    name: str
    duration_type: str
    duration: float
    intensity: float
    repeat: int = 1


def get_zone(sport: str, intensity: float):
    zones = (
        CYCLING_ZONES
        if sport == "Cycling"
        else RUNNING_ZONES
    )

    for low, high, zone, name in zones:
        if low <= intensity < high:
            return zone, name

    return "", ""


# =========================================================
# Cycling
# =========================================================

def cycling_target_watts(
    ftp: float,
    intensity: float,
) -> int:

    return round(
        ftp * intensity / 100
    )


# =========================================================
# Running
# =========================================================

def pace_to_speed_kmh(pace_seconds_per_km):
    if pace_seconds_per_km <= 0:
        return 0

    return 3600 / pace_seconds_per_km


def speed_to_pace(speed_kmh):

    if speed_kmh <= 0:
        return 0

    return 3600 / speed_kmh


def running_target_pace(
    threshold_pace_seconds,
    intensity,
):
    """
    Running intensity is based on speed.

    100% = threshold pace
    110% = 10% faster
    90% = 10% slower
    """

    threshold_speed = pace_to_speed_kmh(
        threshold_pace_seconds
    )

    target_speed = (
        threshold_speed
        * intensity
        / 100
    )

    return speed_to_pace(
        target_speed
    )


def format_pace(seconds):

    if seconds is None or seconds <= 0:
        return "--:--"

    minutes = int(seconds // 60)
    secs = int(round(seconds % 60))

    if secs >= 60:
        minutes += 1
        secs = 0

    return f"{minutes}:{secs:02d}/km"


import plotly.graph_objects as go
def plot_workout_summary(workout, sport="cycling"):
    """
    Clean visual workout timeline.

    Each workout step is represented as a colored block:
        x = time
        y = intensity

    Blocks always start at y=0, so the height of the block
    represents workout intensity.

    Expected input:
    [
        {
            "name": "Warm-up",
            "duration": 600,
            "target_low": 70,
            "target_high": 70,
            "type": "step",
        },
        ...
    ]
    """

    import plotly.graph_objects as go

    # =========================================================
    # Empty workout
    # =========================================================

    if not workout:
        return go.Figure()

    sport = str(sport).lower()

    # =========================================================
    # Training zones
    # =========================================================

    zones = [
        ("Recovery", 0, 55),
        ("Endurance", 55, 75),
        ("Tempo", 75, 90),
        ("Threshold", 90, 105),
        ("VO₂ Max", 105, 120),
        ("Anaerobic", 120, 140),
        ("Anaerobic+", 140, 180),
    ]

    def get_zone(value):

        for name, low, high in zones:

            if low <= value < high:
                return name

        return "Anaerobic+"

    # =========================================================
    # Zone colors
    # =========================================================

    zone_colors = {
        "Recovery": "#CBD5E1",
        "Endurance": "#60A5FA",
        "Tempo": "#34D399",
        "Threshold": "#FBBF24",
        "VO₂ Max": "#F97316",
        "Anaerobic": "#EF4444",
        "Anaerobic+": "#DC2626",
    }

    # =========================================================
    # Create figure
    # =========================================================

    fig = go.Figure()

    elapsed = 0.0
    max_intensity = 0.0

    # =========================================================
    # Create blocks
    # =========================================================

    for step in workout:

        # -----------------------------------------------------
        # Duration
        # -----------------------------------------------------

        try:
            duration = float(
                step.get("duration", 0)
            )
        except (TypeError, ValueError):

            duration = 0

        if duration <= 0:
            continue

        # -----------------------------------------------------
        # Intensity
        # -----------------------------------------------------

        try:
            low = float(
                step.get(
                    "target_low",
                    step.get("target", 50),
                )
            )
        except (TypeError, ValueError):

            low = 50.0

        try:
            high = float(
                step.get(
                    "target_high",
                    step.get("target", low),
                )
            )
        except (TypeError, ValueError):

            high = low

        # -----------------------------------------------------
        # For a single target, use the target as block height.
        #
        # This means:
        #
        # 55%  → block reaches 55
        # 70%  → block reaches 70
        # 120% → block reaches 120
        # -----------------------------------------------------

        intensity_low = max(0, low)
        intensity_high = max(
            intensity_low,
            high,
        )

        # If low == high, the block still has full height.
        y0 = 0
        y1 = intensity_high

        start = elapsed
        end = elapsed + duration

        max_intensity = max(
            max_intensity,
            intensity_high,
        )

        # -----------------------------------------------------
        # Determine zone
        # -----------------------------------------------------

        zone = get_zone(
            (low + high) / 2
        )

        color = zone_colors.get(
            zone,
            "#94A3B8",
        )

        # -----------------------------------------------------
        # Add block
        # -----------------------------------------------------

        fig.add_shape(
            type="rect",

            x0=start,
            x1=end,

            y0=y0,
            y1=y1,

            fillcolor=color,

            line=dict(
                color=color,
                width=0,
            ),

            opacity=0.92,

            layer="above",
        )

        elapsed = end

    # =========================================================
    # Very subtle zone background
    # =========================================================

    # These are deliberately extremely subtle.
    # The workout blocks remain the main visual element.

    for zone_name, low, high in zones:

        fig.add_hrect(
            y0=low,
            y1=high,

            fillcolor=zone_colors[
                zone_name
            ],

            opacity=0.025,

            line_width=0,

            layer="below",
        )

    # =========================================================
    # Vertical separators between blocks
    # =========================================================

    elapsed = 0.0

    for i, step in enumerate(workout):

        try:
            duration = float(
                step.get("duration", 0)
            )
        except (TypeError, ValueError):

            duration = 0

        if duration <= 0:
            continue

        elapsed += duration

        if i < len(workout) - 1:

            fig.add_vline(
                x=elapsed,

                line_width=1,

                line_color=(
                    "rgba(100,116,139,0.12)"
                ),

                layer="above",
            )

    # =========================================================
    # X-axis time formatting
    # =========================================================

    total_seconds = elapsed

    if total_seconds <= 1800:

        tick_interval = 300

    elif total_seconds <= 3600:

        tick_interval = 300

    else:

        tick_interval = 600

    tick_values = list(
        range(
            0,
            int(total_seconds) + 1,
            tick_interval,
        )
    )

    # Always show the end of the workout
    if (
        not tick_values
        or tick_values[-1] != int(total_seconds)
    ):

        tick_values.append(
            int(total_seconds)
        )

    def format_time(seconds):

        seconds = int(seconds)

        minutes = seconds // 60
        remaining = seconds % 60

        if minutes >= 60:

            hours = minutes // 60
            minutes = minutes % 60

            return (
                f"{hours}:{minutes:02d}"
            )

        return (
            f"{minutes}:{remaining:02d}"
        )

    tick_labels = [
        format_time(value)
        for value in tick_values
    ]

    # =========================================================
    # Y-axis title
    # =========================================================

    if sport in {"running", "run"}:

        y_title = "% Threshold Pace"

    else:

        y_title = "% FTP"

    # =========================================================
    # Layout
    # =========================================================

    fig.update_layout(

        # Make it wide and relatively short.
        # This makes it feel like a workout timeline
        # rather than a conventional chart.
        height=320,

        margin=dict(
            l=45,
            r=10,
            t=10,
            b=40,
        ),

        plot_bgcolor="rgba(0,0,0,0)",

        paper_bgcolor="rgba(0,0,0,0)",

        showlegend=False,

        hovermode=False,

        # -----------------------------------------------------
        # X axis
        # -----------------------------------------------------

        xaxis=dict(

            title=None,

            range=[
                0,
                max(
                    total_seconds,
                    1,
                ),
            ],

            tickmode="array",

            tickvals=tick_values,

            ticktext=tick_labels,

            showgrid=False,

            zeroline=False,

            showline=False,

            fixedrange=True,

            ticks="",
        ),

        # -----------------------------------------------------
        # Y axis
        # -----------------------------------------------------

        yaxis=dict(

            title=y_title,

            range=[
                0,
                max(
                    130,
                    max_intensity * 1.05,
                ),
            ],

            showgrid=False,

            zeroline=False,

            showline=False,

            fixedrange=True,

            ticks="",

            tickfont=dict(
                size=10,
            ),

            title_font=dict(
                size=11,
            ),
        ),
    )

    # =========================================================
    # Make Plotly use all available width
    # =========================================================

    fig.update_xaxes(
        automargin=True,
    )

    fig.update_yaxes(
        automargin=True,
    )

    return fig