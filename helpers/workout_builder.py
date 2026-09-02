import json
from pathlib import Path
import streamlit as st
import plotly.graph_objects as go
from helpers.metrics import TRAINING_ZONES
import numpy as np
# =========================================================
# Basic workout calculations
# =========================================================

def duration_seconds(step):
    if step.get("duration_type") != "Time":
        return 0
    return int(step.get("duration_minutes", 0) or 0) * 60 + int(step.get("duration_seconds", 0) or 0)

def format_duration(seconds):
    seconds = int(seconds)
    minutes = seconds // 60
    remaining = seconds % 60
    if minutes >= 60:
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours}:{minutes:02d}:{remaining:02d}"
    return f"{minutes}:{remaining:02d}"

def make_rest():
    return {
        "duration_type": "Time",
        "duration_minutes": 3,
        "duration_seconds": 0,
        "duration_distance": 0,
        "intensity": 55.0,
    }

# =========================================================
# Training zones
# =========================================================

def get_zone(sport, intensity):
    from helpers.metrics import get_training_zone
    intensity = float(intensity)
    zone = get_training_zone(intensity)
    if sport == "Running":
        running_names = {"Recovery": "Easy", "Endurance": "Aerobic", "Tempo": "Tempo", "Threshold": "Threshold", "VO2max": "VO₂max", "Anaerobic": "Speed"}
        display_name = running_names.get(zone, zone)
        return zone, display_name
    cycling_codes = {"Recovery": "Z1", "Endurance": "Z2", "Tempo": "Z3", "Threshold": "Z4", "VO2max": "Z5", "Anaerobic": "Z6"}
    code = cycling_codes.get(zone, "Z7")
    return code, zone

def cycling_target_watts(ftp, intensity):
    return round(float(ftp) * float(intensity) / 100)

def running_target_pace(threshold_seconds, intensity):
    return float(threshold_seconds) / (float(intensity) / 100)

def format_pace(seconds):
    seconds = max(1, int(round(seconds)))
    minutes = seconds // 60
    remaining = seconds % 60
    return f"{minutes}:{remaining:02d}/km"

# =========================================================
# Workout structure
# =========================================================

def create_default_workout():
    return {
        "warmup": {
            "name": "Warm-up",
            "duration_type": "Time",
            "duration_minutes": 10,
            "duration_seconds": 0,
            "duration_distance": 0,
            "intensity": 55.0,
        },
        "intervals": [
            {
                "name": "Interval 1",
                "fast": {
                    "duration_type": "Time",
                    "duration_minutes": 0,
                    "duration_seconds": 36,
                    "duration_distance": 0,
                    "intensity": 120.0,
                },
                "slow": {
                    "duration_type": "Time",
                    "duration_minutes": 0,
                    "duration_seconds": 15,
                    "duration_distance": 0,
                    "intensity": 55.0,
                },
                "repeat": 13,
                "rest": make_rest(),
            }
        ],
        "cooldown": {
            "name": "Cool-down",
            "duration_type": "Time",
            "duration_minutes": 10,
            "duration_seconds": 0,
            "duration_distance": 0,
            "intensity": 55.0,
        },
    }

# =========================================================
# Workout editing controls
# =========================================================

def edit_duration(step, key_prefix):
    type_col, value_col = st.columns([0.85, 2.15])
    with type_col:
        duration_type = st.selectbox(
            "Duration",
            ["Time", "Distance"],
            index=0 if step.get("duration_type", "Time") == "Time" else 1,
            key=f"{key_prefix}_type",
            label_visibility="collapsed",
        )
    step["duration_type"] = duration_type
    with value_col:
        if duration_type == "Time":
            min_col, sec_col = st.columns(2)
            with min_col:
                step["duration_minutes"] = st.number_input(
                    "Min",
                    min_value=0,
                    max_value=999,
                    value=int(step.get("duration_minutes", 0) or 0),
                    step=1,
                    key=f"{key_prefix}_minutes",
                )
            with sec_col:
                step["duration_seconds"] = st.number_input(
                    "Sec",
                    min_value=0,
                    max_value=59,
                    value=int(step.get("duration_seconds", 0) or 0),
                    step=1,
                    key=f"{key_prefix}_seconds",
                )
        else:
            step["duration_distance"] = st.number_input(
                "km",
                min_value=0.1,
                value=float(step.get("duration_distance", 1.0) or 1.0),
                step=0.1,
                key=f"{key_prefix}_distance",
            )

def edit_intensity(step, key_prefix, sport, ftp, running_threshold_seconds):
    intensity = st.number_input(
        "% FTP" if sport == "Cycling" else "% Threshold",
        min_value=1.0,
        max_value=250.0,
        value=float(step.get("intensity", 55.0) or 55.0),
        step=1.0,
        key=f"{key_prefix}_intensity",
    )
    step["intensity"] = intensity
    zone, zone_name = get_zone(sport, intensity)
    if sport == "Cycling":
        target_text = f"{cycling_target_watts(ftp, intensity)} W"
    else:
        target_text = format_pace(running_target_pace(running_threshold_seconds, intensity))
    st.caption(f"**{intensity:.0f}%** · {zone} · {zone_name} · **{target_text}**")

def edit_interval_section(section, key_prefix, title, emoji, sport, ftp, running_threshold_seconds):
    st.markdown(f"**{emoji} {title}**")
    c1, c2 = st.columns([1.45, 1])
    with c1:
        edit_duration(section, key_prefix)
    with c2:
        edit_intensity(section, key_prefix, sport, ftp, running_threshold_seconds)

# =========================================================
# Flatten workout
# =========================================================

def flatten_workout(workout):
    flat_steps = []
    warmup = workout["warmup"]
    flat_steps.append({
        "name": "Warm-up",
        "duration_type": warmup.get("duration_type", "Time"),
        "duration_minutes": warmup.get("duration_minutes", 0),
        "duration_seconds": warmup.get("duration_seconds", 0),
        "duration_distance": warmup.get("duration_distance", 0),
        "intensity": warmup.get("intensity", 55),
        "repeat": 1,
    })
    intervals = workout["intervals"]
    for i, interval in enumerate(intervals):
        fast = interval["fast"]
        slow = interval["slow"]
        repeat = int(interval.get("repeat", 1))
        for _ in range(repeat):
            flat_steps.append({
                "name": f"{interval['name']} - Fast",
                "duration_type": fast.get("duration_type", "Time"),
                "duration_minutes": fast.get("duration_minutes", 0),
                "duration_seconds": fast.get("duration_seconds", 0),
                "duration_distance": fast.get("duration_distance", 0),
                "intensity": fast.get("intensity", 100),
                "repeat": 1,
            })
            flat_steps.append({
                "name": f"{interval['name']} - Slow",
                "duration_type": slow.get("duration_type", "Time"),
                "duration_minutes": slow.get("duration_minutes", 0),
                "duration_seconds": slow.get("duration_seconds", 0),
                "duration_distance": slow.get("duration_distance", 0),
                "intensity": slow.get("intensity", 55),
                "repeat": 1,
            })
        if i < len(intervals) - 1:
            rest = interval.get("rest", make_rest())
            flat_steps.append({
                "name": "Rest between intervals",
                "duration_type": rest.get("duration_type", "Time"),
                "duration_minutes": rest.get("duration_minutes", 0),
                "duration_seconds": rest.get("duration_seconds", 0),
                "duration_distance": rest.get("duration_distance", 0),
                "intensity": rest.get("intensity", 55),
                "repeat": 1,
            })
    cooldown = workout["cooldown"]
    flat_steps.append({
        "name": "Cool-down",
        "duration_type": cooldown.get("duration_type", "Time"),
        "duration_minutes": cooldown.get("duration_minutes", 0),
        "duration_seconds": cooldown.get("duration_seconds", 0),
        "duration_distance": cooldown.get("duration_distance", 0),
        "intensity": cooldown.get("intensity", 55),
        "repeat": 1,
    })
    return flat_steps

# =========================================================
# Workout TSS
# =========================================================

def calculate_workout_tss(steps, ftp):
    total_tss = 0.0
    for step in steps:
        duration = duration_seconds(step)
        if duration <= 0:
            continue
        intensity = float(step.get("intensity", 55)) / 100
        hours = duration / 3600
        total_tss += hours * intensity ** 2 * 100
    return total_tss

# =========================================================
# Workout preview
# =========================================================
def plot_workout_summary(steps, sport, ftp=None, threshold_pace=None):
    import numpy as np
    import plotly.graph_objects as go
    from helpers.metrics import TRAINING_ZONES
    fig = go.Figure()
    zone_colors = {
        "Recovery": "#FFFFFF",
        "Endurance": "#3B82F6",
        "Tempo": "#22C55E",
        "Threshold": "#F97316",
        "VO2max": "#EF4444",
        "Anaerobic": "#991B1B",
    }
    def get_zone(intensity):
        intensity_ratio = float(intensity) / 100
        for zone, limits in TRAINING_ZONES.items():
            if limits["min"] <= intensity_ratio < limits["max"]:
                return zone
        return "Anaerobic"
    def pace_to_seconds(pace):
        if isinstance(pace, (int, float)):
            return float(pace) * 60
        minutes, seconds = str(pace).split(":")
        return float(minutes) * 60 + float(seconds)
    def seconds_to_pace(seconds):
        minutes = int(seconds // 60)
        secs = int(round(seconds % 60))
        if secs == 60:
            minutes += 1
            secs = 0
        return f"{minutes}:{secs:02d}"
    current_time = 0
    bars = {zone: {"x": [], "y": [], "width": []} for zone in zone_colors}
    if sport == "Running":
        if threshold_pace is None:
            threshold_pace = 5.0
        threshold_minutes = pace_to_seconds(threshold_pace) / 60
        slow_pace = threshold_minutes / 0.50
        fast_pace = threshold_minutes / 1.40
    for step in steps:
        duration = float(step.get("duration", 0) or 0)
        if duration <= 0:
            duration = (
                float(step.get("duration_minutes", 0) or 0) * 60
                + float(step.get("duration_seconds", 0) or 0)
            )
        if duration <= 0:
            continue
        if "target_low" in step:
            target_low = float(step.get("target_low", 55) or 55)
            target_high = float(step.get("target_high", target_low) or target_low)
        else:
            intensity = float(step.get("intensity", 55) or 55)
            target_low = intensity
            target_high = intensity
        if target_low == target_high:
            center = target_low
            target_low = max(0, center - 3)
            target_high = center + 3
        center_intensity = (target_low + target_high) / 2
        zone = get_zone(center_intensity)
        if sport == "Cycling":
            y_value = (center_intensity / 100) * float(ftp or 300)
        else:
            pace_minutes = threshold_minutes / (center_intensity / 100)
            y_value = slow_pace - pace_minutes
        bars[zone]["x"].append((current_time + duration / 2) / 60)
        bars[zone]["y"].append(y_value)
        bars[zone]["width"].append(duration / 60)
        current_time += duration
    for zone, values in bars.items():
        if values["x"]:
            fig.add_bar(
                x=values["x"],
                y=values["y"],
                width=values["width"],
                marker_color=zone_colors[zone],
                marker_line_color="#CBD5E1" if zone == "Recovery" else zone_colors[zone],
                marker_line_width=1,
                opacity=0.75,
                hoverinfo="skip",
            )
    if sport == "Cycling":
        y_axis = dict(
            title="Power (W)",
            showgrid=True,
            zeroline=False,
            range=[0, float(ftp or 300) * 1.3],
        )
    else:
        y_title = "Pace (min/km)"
        tick_paces = np.arange(
            np.ceil(fast_pace * 2) / 2,
            slow_pace + 0.01,
            0.5,
        )
        tickvals = [slow_pace - pace for pace in tick_paces]
        ticktext = [seconds_to_pace(pace * 60) for pace in tick_paces]
        y_axis = dict(
            title=y_title,
            showgrid=True,
            zeroline=False,
            range=[0, slow_pace - fast_pace],
            tickvals=tickvals,
            ticktext=ticktext,
        )
    fig.update_layout(
        height=260,
        margin=dict(l=55, r=10, t=10, b=35),
        xaxis=dict(
            title="Time (minutes)",
            showgrid=False,
            zeroline=False,
        ),
        yaxis=y_axis,
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
        hovermode=False,
        barmode="overlay",
    )
    return fig

# =========================================================
# Save workout to library
# =========================================================

def save_workout_to_library(workout, sport, category):
    root = Path(__file__).resolve().parent.parent
    library_path = root / "workouts" / sport.lower()
    library_path.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in workout["name"]).strip()
    filename = f"{safe_name}.json"
    path = library_path / filename
    counter = 2
    while path.exists():
        path = library_path / f"{safe_name}_{counter}.json"
        counter += 1
    workout["_category"] = category
    workout["_sport"] = sport
    workout["_file"] = path.name
    steps = flatten_workout(workout)
    workout["estimated_tss"] = calculate_workout_tss(steps, workout.get("_ftp", 290))
    workout["target_tss"] = workout["estimated_tss"]
    workout["duration_seconds"] = sum(duration_seconds(step) for step in steps)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(workout, f, indent=2)
    return path

# =========================================================
# Workout builder dialog
# =========================================================

@st.dialog("Create workout", width="large")
def workout_builder_dialog(sport="Cycling", save_callback=None):
    username = st.session_state.get("username")
    if not username:
        st.error("Please log in first.")
        return
    try:
        from Strava.strava_user import get_user_settings
        settings = get_user_settings(username)
    except Exception:
        settings = {}
    ftp = float(settings.get("ftp", 290) or 290)
    running_threshold = float(settings.get("threshold_pace", 6.0) or 6.0)
    running_threshold_seconds = running_threshold * 60
    if "library_workout" not in st.session_state:
        st.session_state.library_workout = create_default_workout()
    workout = st.session_state.library_workout

    # =====================================================
    # Compact dialog styling
    # =====================================================

    st.markdown("""
    <style>
    [data-testid="stDialog"] [data-testid="stVerticalBlock"] {
        gap: 0.15rem;
    }
    [data-testid="stDialog"] .block-container {
        padding-top: 0.25rem;
        padding-bottom: 0.25rem;
    }
    [data-testid="stDialog"] h3 {
        margin: 0 0 0.15rem 0;
        font-size: 20px;
    }
    [data-testid="stDialog"] hr {
        margin: 0.3rem 0;
    }
    [data-testid="stDialog"] [data-testid="stCaptionContainer"] {
        margin-top: -2px;
        margin-bottom: 2px;
    }
    [data-testid="stDialog"] [data-testid="stNumberInput"],
    [data-testid="stDialog"] [data-testid="stSelectbox"],
    [data-testid="stDialog"] [data-testid="stTextInput"] {
        margin-bottom: 0;
    }
    [data-testid="stDialog"] [data-testid="stWidgetLabel"] {
        font-size: 10px;
        margin-bottom: 1px;
    }
    [data-testid="stDialog"] input {
        min-height: 32px;
        height: 32px;
    }
    [data-testid="stDialog"] button {
        min-height: 32px;
    }
    .builder-section {
        font-size: 10px;
        font-weight: 700;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin: 6px 0 2px 0;
    }
    .builder-card {
        border: 1px solid #E5E7EB;
        border-radius: 9px;
        padding: 7px 9px;
        margin-bottom: 5px;
        background: #FFFFFF;
    }
    .interval-title {
        font-size: 12px;
        font-weight: 700;
        color: #17212B;
    }
    </style>
    """, unsafe_allow_html=True)

    # =====================================================
    # Header
    # =====================================================

    st.markdown("### Create workout")
    st.caption("Build a structured workout and add it to your library.")
    header_left, header_middle, header_right = st.columns([2.2, 1, 1])
    with header_left:
        workout_name = st.text_input(
            "Workout name",
            value=st.session_state.get("library_workout_name", f"{sport} Workout"),
            key="library_workout_name",
        )
    with header_middle:
        selected_sport = st.selectbox(
            "Sport",
            ["Cycling", "Running"],
            index=0 if sport == "Cycling" else 1,
            key="library_builder_sport",
        )
    with header_right:
        workout_type = st.selectbox(
            "Workout type",
            ["Endurance", "Recovery", "Tempo", "Threshold", "VO₂max", "Intervals", "Race", "Other"],
            key="library_builder_type",
        )

    if selected_sport == "Cycling":
        st.caption(f"FTP **{ftp:.0f} W**")
    else:
        st.caption(f"Threshold pace **{format_pace(running_threshold_seconds)}**")

    # =====================================================
    # Local editing helpers
    # =====================================================

    def edit_duration_compact(step, key_prefix):
        type_col, input_col = st.columns([0.75, 2.25])
        with type_col:
            duration_type = st.selectbox(
                "Duration",
                ["Time", "Distance"],
                index=0 if step.get("duration_type", "Time") == "Time" else 1,
                key=f"{key_prefix}_type",
            )
        step["duration_type"] = duration_type
        with input_col:
            if duration_type == "Time":
                min_col, sec_col = st.columns(2)
                with min_col:
                    step["duration_minutes"] = st.number_input(
                        "Min",
                        min_value=0,
                        max_value=999,
                        value=int(step.get("duration_minutes", 0) or 0),
                        step=1,
                        key=f"{key_prefix}_minutes",
                    )
                with sec_col:
                    step["duration_seconds"] = st.number_input(
                        "Sec",
                        min_value=0,
                        max_value=59,
                        value=int(step.get("duration_seconds", 0) or 0),
                        step=1,
                        key=f"{key_prefix}_seconds",
                    )
            else:
                step["duration_distance"] = st.number_input(
                    "km",
                    min_value=0.1,
                    value=float(step.get("duration_distance", 1.0) or 1.0),
                    step=0.1,
                    key=f"{key_prefix}_distance",
                )

    def edit_intensity_compact(step, key_prefix):
        intensity = st.number_input(
            "% FTP" if selected_sport == "Cycling" else "% Threshold",
            min_value=1.0,
            max_value=250.0,
            value=float(step.get("intensity", 55.0) or 55.0),
            step=1.0,
            key=f"{key_prefix}_intensity",
        )
        step["intensity"] = intensity
        zone, zone_name = get_zone(selected_sport, intensity)
        if selected_sport == "Cycling":
            target_text = f"{cycling_target_watts(ftp, intensity)} W"
        else:
            target_text = format_pace(
                running_target_pace(running_threshold_seconds, intensity)
            )
        st.caption(f"**{intensity:.0f}%** · {zone} · {zone_name} · **{target_text}**")

    # =====================================================
    # Training zones
    # =====================================================

    with st.expander("Training zones", expanded=False):
        if selected_sport == "Cycling":
            zones = [
                ("Z1", "<55%", "Recovery"),
                ("Z2", "55–75%", "Endurance"),
                ("Z3", "76–90%", "Tempo"),
                ("Z4", "91–105%", "Threshold"),
                ("Z5", "106–120%", "VO₂max"),
                ("Z6", "121–150%", "Anaerobic"),
                ("Z7", ">150%", "Neuromuscular"),
            ]
        else:
            zones = [
                ("Easy", "<76%", "Recovery / Easy"),
                ("Aerobic", "76–85%", "Endurance"),
                ("Tempo", "86–95%", "Tempo"),
                ("Threshold", "96–100%", "Threshold"),
                ("VO₂max", "101–105%", "VO₂max"),
                ("Speed", ">105%", "Speed"),
            ]
        zone_cols = st.columns(4)
        for i, (zone, percentage, description) in enumerate(zones):
            with zone_cols[i % 4]:
                st.caption(f"**{zone}** {percentage}")
                st.caption(description)

    # =====================================================
    # Warm-up
    # =====================================================

    st.markdown('<div class="builder-section">Warm-up</div>', unsafe_allow_html=True)
    with st.container(border=True):
        c1, c2 = st.columns([1.45, 1])
        with c1:
            edit_duration_compact(workout["warmup"], "library_warmup")
        with c2:
            edit_intensity_compact(workout["warmup"], "library_warmup")

    # =====================================================
    # Intervals
    # =====================================================

    st.markdown('<div class="builder-section">Intervals</div>', unsafe_allow_html=True)

    for i, interval in enumerate(workout["intervals"]):
        interval.setdefault("rest", make_rest())

        with st.container(border=True):
            header_col, repeat_col, delete_col = st.columns([4, 1, 0.5])

            with header_col:
                interval["name"] = st.text_input(
                    "Interval name",
                    value=interval.get("name", f"Interval {i + 1}"),
                    key=f"library_interval_name_{i}",
                    label_visibility="collapsed",
                )

            with repeat_col:
                interval["repeat"] = st.number_input(
                    "Repeat",
                    min_value=1,
                    max_value=100,
                    value=int(interval.get("repeat", 1)),
                    step=1,
                    key=f"library_interval_repeat_{i}",
                )

            with delete_col:
                if len(workout["intervals"]) > 1:
                    if st.button(
                        "✕",
                        key=f"library_delete_interval_{i}",
                        help="Delete interval",
                    ):
                        workout["intervals"].pop(i)
                        st.rerun()

            fast_col, slow_col = st.columns(2)

            with fast_col:
                st.markdown("**🟠 Fast**")
                edit_duration_compact(
                    interval["fast"],
                    f"library_interval_{i}_fast",
                )
                edit_intensity_compact(
                    interval["fast"],
                    f"library_interval_{i}_fast",
                )

            with slow_col:
                st.markdown("**🔵 Slow**")
                edit_duration_compact(
                    interval["slow"],
                    f"library_interval_{i}_slow",
                )
                edit_intensity_compact(
                    interval["slow"],
                    f"library_interval_{i}_slow",
                )

            fast_seconds = duration_seconds(interval["fast"])
            slow_seconds = duration_seconds(interval["slow"])
            repeat = int(interval.get("repeat", 1))
            total_interval_seconds = (fast_seconds + slow_seconds) * repeat

            if total_interval_seconds > 0:
                st.caption(
                    f"{repeat} × ({format_duration(fast_seconds)} fast + "
                    f"{format_duration(slow_seconds)} slow) · "
                    f"**{format_duration(total_interval_seconds)}**"
                )

        if i < len(workout["intervals"]) - 1:
            rest = interval["rest"]

            with st.container(border=True):
                st.markdown("**Recovery between intervals**")
                c1, c2 = st.columns([1.45, 1])

                with c1:
                    edit_duration_compact(
                        rest,
                        f"library_interval_{i}_rest",
                    )

                with c2:
                    edit_intensity_compact(
                        rest,
                        f"library_interval_{i}_rest",
                    )

    # =====================================================
    # Add interval
    # =====================================================

    if st.button(
        "＋ Add interval",
        use_container_width=True,
        key="library_add_interval",
    ):
        index = len(workout["intervals"]) + 1

        workout["intervals"].append({
            "name": f"Interval {index}",
            "fast": {
                "duration_type": "Time",
                "duration_minutes": 1,
                "duration_seconds": 0,
                "duration_distance": 0,
                "intensity": 110.0,
            },
            "slow": {
                "duration_type": "Time",
                "duration_minutes": 1,
                "duration_seconds": 0,
                "duration_distance": 0,
                "intensity": 55.0,
            },
            "repeat": 5,
            "rest": make_rest(),
        })

        st.rerun()

    # =====================================================
    # Cool-down
    # =====================================================

    st.markdown('<div class="builder-section">Cool-down</div>', unsafe_allow_html=True)

    with st.container(border=True):
        c1, c2 = st.columns([1.45, 1])

        with c1:
            edit_duration_compact(
                workout["cooldown"],
                "library_cooldown",
            )

        with c2:
            edit_intensity_compact(
                workout["cooldown"],
                "library_cooldown",
            )

    # =====================================================
    # Summary
    # =====================================================

    steps = flatten_workout(workout)
    total_seconds = sum(duration_seconds(step) for step in steps)
    workout_tss = calculate_workout_tss(steps, ftp)

    st.markdown('<div class="builder-section">Summary</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Duration", format_duration(total_seconds))

    with c2:
        st.metric("Intervals", len(workout["intervals"]))

    with c3:
        st.metric("TSS", f"{workout_tss:.0f}")

    # =====================================================
    # Workout preview
    # =====================================================

    with st.expander("Workout preview", expanded=True):
        plot_steps = []

        for step in steps:
            duration = duration_seconds(step)

            if duration <= 0:
                continue

            intensity = float(step.get("intensity", 55))

            plot_steps.append({
                "name": step.get("name", "Step"),
                "duration": duration,
                "target_low": intensity,
                "target_high": intensity,
                "type": "step",
            })

        if plot_steps:
            fig = plot_workout_summary(
                plot_steps,
                sport=selected_sport,
            )

            fig.update_layout(
                height=170,
                margin=dict(l=5, r=5, t=5, b=5),
            )

            st.plotly_chart(
                fig,
                width="stretch",
                config={"displayModeBar": False},
                key="library_builder_preview",
            )

    # =====================================================
    # Save workout
    # =====================================================

    if st.button(
        "＋ Add workout to library",
        type="primary",
        use_container_width=True,
        key="save_library_workout",
    ):
        if not workout_name.strip():
            st.error("Please enter a workout name.")
            return

        workout_data = {
            "name": workout_name.strip(),
            "_category": workout_type,
            "sport": selected_sport,
            "steps": steps,
            "target_tss": workout_tss,
            "estimated_tss": workout_tss,
        }

        if save_callback:
            save_callback(workout_data)
        else:
            st.session_state["new_library_workout"] = workout_data

        st.session_state.pop("library_workout", None)
        st.session_state.pop("library_workout_name", None)

        st.success("Workout added to your library.")
        st.rerun()