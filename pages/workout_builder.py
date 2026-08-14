import re

import streamlit as st

from helpers.style import apply_global_style
from helpers.workout_builder import (
    get_zone,
    cycling_target_watts,
    running_target_pace,
    format_pace,
    plot_workout_summary,
)


apply_global_style()


# =========================================================
# Page title
# =========================================================

st.markdown(
    """
    <div class="dashboard-title">
        Workout Builder
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "Create structured workouts and export them as FIT files "
    "for Garmin, Wahoo and other compatible devices."
)


# =========================================================
# User / settings
# =========================================================

username = st.session_state.get("username")

if not username:
    st.error("Please log in first.")
    st.stop()


try:
    from helpers.user_settings import get_user_settings

    settings = get_user_settings(username)

except Exception:
    settings = {}


ftp = float(
    settings.get("ftp", 290) or 290
)


running_threshold = settings.get(
    "threshold_pace",
    settings.get(
        "running_threshold_pace",
        270,
    ),
)

try:
    running_threshold = float(
        running_threshold
    )
except Exception:
    running_threshold = 270


# =========================================================
# Sport selection
# =========================================================

sport = st.segmented_control(
    "Sport",
    ["Cycling", "Running"],
    default="Cycling",
)


if sport == "Cycling":

    st.info(
        f"Using cycling FTP: **{ftp:.0f} W**"
    )

else:

    st.info(
        "Using running threshold pace: "
        f"**{format_pace(running_threshold)}**"
    )


# =========================================================
# Workout name
# =========================================================

workout_name = st.text_input(
    "Workout name",
    value=(
        "Cycling Workout"
        if sport == "Cycling"
        else "Running Workout"
    ),
)


st.divider()


# =========================================================
# Layout
# =========================================================

builder_col, zones_col = st.columns(
    [3.2, 1],
    gap="large",
)


# =========================================================
# Training zones
# =========================================================

with zones_col:

    st.markdown("### Training zones")

    if sport == "Cycling":

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
            ("Speed", ">105%", "Anaerobic / Speed"),
        ]

    for zone, percentage, description in zones:

        st.markdown(
            f"""
            **{zone}** · {percentage}  
            <small>{description}</small>
            """,
            unsafe_allow_html=True,
        )

        st.divider()


# =========================================================
# Workout builder
# =========================================================

with builder_col:

    st.markdown("### Workout")


    # =====================================================
    # Initial workout structure
    # =====================================================

    if "workout" not in st.session_state:

        st.session_state.workout = {

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

                    "rest": {
                        "duration_type": "Time",
                        "duration_minutes": 3,
                        "duration_seconds": 0,
                        "duration_distance": 0,
                        "intensity": 55.0,
                    },
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


    workout = st.session_state.workout


    # =====================================================
    # Helper functions
    # =====================================================

    def make_rest():
        """Create a default rest section."""

        return {
            "duration_type": "Time",
            "duration_minutes": 3,
            "duration_seconds": 0,
            "duration_distance": 0,
            "intensity": 55.0,
        }


    def duration_seconds(step):
        """Return a step duration in seconds."""

        if step.get("duration_type") != "Time":
            return 0

        minutes = int(
            step.get(
                "duration_minutes",
                0,
            )
        )

        seconds = int(
            step.get(
                "duration_seconds",
                0,
            )
        )

        return minutes * 60 + seconds


    def format_duration(seconds):
        """Format seconds as M:SS or H:MM:SS."""

        seconds = int(seconds)

        minutes = seconds // 60
        remaining = seconds % 60

        if minutes >= 60:

            hours = minutes // 60
            minutes = minutes % 60

            return (
                f"{hours}:{minutes:02d}:"
                f"{remaining:02d}"
            )

        return (
            f"{minutes}:{remaining:02d}"
        )


    def edit_intensity(
        step,
        key_prefix,
        collapsed=False,
    ):
        """Render intensity and target information."""

        intensity = st.number_input(
            (
                "% FTP"
                if sport == "Cycling"
                else "% Threshold"
            ),
            min_value=1.0,
            max_value=250.0,
            value=float(
                step.get(
                    "intensity",
                    55.0,
                )
            ),
            step=1.0,
            key=f"{key_prefix}_intensity",
            label_visibility=(
                "collapsed"
                if collapsed
                else "visible"
            ),
        )

        step["intensity"] = intensity

        zone, zone_name = get_zone(
            sport,
            intensity,
        )

        if sport == "Cycling":

            target = cycling_target_watts(
                ftp,
                intensity,
            )

            target_text = f"{target} W"

        else:

            target_pace = running_target_pace(
                running_threshold,
                intensity,
            )

            target_text = format_pace(
                target_pace
            )

        st.caption(
            f"**{intensity:.0f}%** · "
            f"{zone} · {zone_name} · "
            f"**{target_text}**"
        )


    def edit_duration(
        step,
        key_prefix,
    ):
        """Render duration controls."""

        duration_type = st.selectbox(
            "Duration",
            ["Time", "Distance"],
            index=(
                0
                if step.get(
                    "duration_type",
                    "Time",
                ) == "Time"
                else 1
            ),
            key=f"{key_prefix}_type",
        )

        step["duration_type"] = duration_type

        if duration_type == "Time":

            d1, d2 = st.columns(2)

            with d1:

                step["duration_minutes"] = st.number_input(
                    "Minutes",
                    min_value=0,
                    max_value=999,
                    value=int(
                        step.get(
                            "duration_minutes",
                            0,
                        )
                    ),
                    step=1,
                    key=f"{key_prefix}_minutes",
                )

            with d2:

                step["duration_seconds"] = st.number_input(
                    "Seconds",
                    min_value=0,
                    max_value=59,
                    value=int(
                        step.get(
                            "duration_seconds",
                            0,
                        )
                    ),
                    step=1,
                    key=f"{key_prefix}_seconds",
                )

        else:

            step["duration_distance"] = st.number_input(
                "Distance (km)",
                min_value=0.1,
                value=float(
                    step.get(
                        "duration_distance",
                        1.0,
                    )
                ),
                step=0.1,
                key=f"{key_prefix}_distance",
            )


    def edit_interval_section(
        section,
        key_prefix,
        title,
        emoji,
    ):
        """Render Fast / Slow / Rest section."""

        st.markdown(
            f"**{emoji} {title}**"
        )

        c1, c2 = st.columns(
            [1.4, 1]
        )

        with c1:

            edit_duration(
                section,
                key_prefix,
            )

        with c2:

            edit_intensity(
                section,
                key_prefix,
            )


    # =====================================================
    # Warm-up
    # =====================================================

    st.markdown("#### Warm-up")

    with st.container(border=True):

        warmup = workout["warmup"]

        st.markdown("**Warm-up**")

        c1, c2 = st.columns(
            [1.4, 1]
        )

        with c1:

            edit_duration(
                warmup,
                "warmup",
            )

        with c2:

            edit_intensity(
                warmup,
                "warmup",
            )


    st.divider()


    # =====================================================
    # Intervals
    # =====================================================

    st.markdown("#### Intervals")

    st.caption(
        "Build your workout from repeated fast / slow blocks. "
        "Add a separate rest between different intervals."
    )


    # -----------------------------------------------------
    # Render intervals
    # -----------------------------------------------------

    for i, interval in enumerate(
        workout["intervals"]
    ):

        # Ensure rest exists for older session state
        interval.setdefault(
            "rest",
            make_rest(),
        )

        with st.container(
            border=True
        ):

            # =============================================
            # Header
            # =============================================

            title_col, repeat_col, delete_col = st.columns(
                [4, 1.3, 0.6]
            )

            with title_col:

                st.markdown(
                    f"**Interval {i + 1}**"
                )

                interval["name"] = st.text_input(
                    "Name",
                    value=interval.get(
                        "name",
                        f"Interval {i + 1}",
                    ),
                    key=f"interval_name_{i}",
                    label_visibility="collapsed",
                )

            with repeat_col:

                interval["repeat"] = st.number_input(
                    "Repeat",
                    min_value=1,
                    max_value=100,
                    value=int(
                        interval.get(
                            "repeat",
                            1,
                        )
                    ),
                    step=1,
                    key=f"interval_repeat_{i}",
                )

            with delete_col:

                if st.button(
                    "✕",
                    key=f"delete_interval_{i}",
                    help="Delete interval",
                ):

                    workout["intervals"].pop(i)

                    st.rerun()


            # =============================================
            # Fast
            # =============================================

            edit_interval_section(
                interval["fast"],
                f"interval_{i}_fast",
                "Fast",
                "🟠",
            )


            st.markdown(
                "<div style='height:8px'></div>",
                unsafe_allow_html=True,
            )


            # =============================================
            # Slow
            # =============================================

            edit_interval_section(
                interval["slow"],
                f"interval_{i}_slow",
                "Slow",
                "🔵",
            )


            # =============================================
            # Interval summary
            # =============================================

            fast_seconds = duration_seconds(
                interval["fast"]
            )

            slow_seconds = duration_seconds(
                interval["slow"]
            )

            repeat = int(
                interval.get(
                    "repeat",
                    1,
                )
            )

            cycle_seconds = (
                fast_seconds
                + slow_seconds
            )

            total_interval_seconds = (
                cycle_seconds
                * repeat
            )

            if cycle_seconds > 0:

                st.caption(
                    f"**{repeat} ×** "
                    f"({format_duration(fast_seconds)} fast + "
                    f"{format_duration(slow_seconds)} slow)"
                    f" · "
                    f"**{format_duration(total_interval_seconds)} total**"
                )


        # =================================================
        # Rest between intervals
        # =================================================

        if i < len(workout["intervals"]) - 1:

            rest = interval["rest"]

            st.markdown(
                """
                <div style="
                    text-align:center;
                    margin:12px 0 6px 0;
                    color:#6B7280;
                    font-size:11px;
                    font-weight:700;
                    letter-spacing:0.08em;
                ">
                    REST BETWEEN INTERVALS
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.container(
                border=True
            ):

                st.markdown(
                    "**Recovery**"
                )

                st.caption(
                    "Easy effort before the next interval."
                )

                c1, c2 = st.columns(
                    [1.4, 1]
                )

                with c1:

                    edit_duration(
                        rest,
                        f"interval_{i}_rest",
                    )

                with c2:

                    edit_intensity(
                        rest,
                        f"interval_{i}_rest",
                    )


    # -----------------------------------------------------
    # Add interval
    # -----------------------------------------------------

    st.markdown("")

    if st.button(
        "＋ Add interval",
        use_container_width=True,
    ):

        new_index = (
            len(workout["intervals"]) + 1
        )

        workout["intervals"].append(
            {
                "name": f"Interval {new_index}",

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
            }
        )

        st.rerun()


    st.divider()


    # =====================================================
    # Cool-down
    # =====================================================

    st.markdown("#### Cool-down")

    with st.container(border=True):

        cooldown = workout["cooldown"]

        st.markdown("**Cool-down**")

        c1, c2 = st.columns(
            [1.4, 1]
        )

        with c1:

            edit_duration(
                cooldown,
                "cooldown",
            )

        with c2:

            edit_intensity(
                cooldown,
                "cooldown",
            )


    # =====================================================
    # Flatten workout
    # =====================================================

    def flatten_workout(workout):
        """
        Convert the hierarchical workout into a flat list
        suitable for FIT generation.

        Structure:

            Warm-up

            Interval 1
                Fast
                Slow
                Fast
                Slow
                ...

            Rest

            Interval 2
                Fast
                Slow
                ...

            Cool-down
        """

        flat_steps = []

        # -------------------------------------------------
        # Warm-up
        # -------------------------------------------------

        warmup = workout["warmup"]

        flat_steps.append(
            {
                "name": "Warm-up",
                "duration_type": warmup.get(
                    "duration_type",
                    "Time",
                ),
                "duration_minutes": warmup.get(
                    "duration_minutes",
                    0,
                ),
                "duration_seconds": warmup.get(
                    "duration_seconds",
                    0,
                ),
                "duration_distance": warmup.get(
                    "duration_distance",
                    0,
                ),
                "intensity": warmup.get(
                    "intensity",
                    55,
                ),
                "repeat": 1,
            }
        )


        # -------------------------------------------------
        # Intervals
        # -------------------------------------------------

        intervals = workout["intervals"]

        for i, interval in enumerate(intervals):

            fast = interval["fast"]
            slow = interval["slow"]

            repeat = int(
                interval.get(
                    "repeat",
                    1,
                )
            )

            # ---------------------------------------------
            # Fast / slow repetitions
            # ---------------------------------------------

            for repetition in range(repeat):

                flat_steps.append(
                    {
                        "name": (
                            f"{interval['name']} - Fast"
                        ),
                        "duration_type": fast.get(
                            "duration_type",
                            "Time",
                        ),
                        "duration_minutes": fast.get(
                            "duration_minutes",
                            0,
                        ),
                        "duration_seconds": fast.get(
                            "duration_seconds",
                            0,
                        ),
                        "duration_distance": fast.get(
                            "duration_distance",
                            0,
                        ),
                        "intensity": fast.get(
                            "intensity",
                            100,
                        ),
                        "repeat": 1,
                    }
                )

                flat_steps.append(
                    {
                        "name": (
                            f"{interval['name']} - Slow"
                        ),
                        "duration_type": slow.get(
                            "duration_type",
                            "Time",
                        ),
                        "duration_minutes": slow.get(
                            "duration_minutes",
                            0,
                        ),
                        "duration_seconds": slow.get(
                            "duration_seconds",
                            0,
                        ),
                        "duration_distance": slow.get(
                            "duration_distance",
                            0,
                        ),
                        "intensity": slow.get(
                            "intensity",
                            55,
                        ),
                        "repeat": 1,
                    }
                )


            # ---------------------------------------------
            # Rest between intervals
            # ---------------------------------------------

            if i < len(intervals) - 1:

                rest = interval.get(
                    "rest",
                    make_rest(),
                )

                flat_steps.append(
                    {
                        "name": "Rest between intervals",
                        "duration_type": rest.get(
                            "duration_type",
                            "Time",
                        ),
                        "duration_minutes": rest.get(
                            "duration_minutes",
                            0,
                        ),
                        "duration_seconds": rest.get(
                            "duration_seconds",
                            0,
                        ),
                        "duration_distance": rest.get(
                            "duration_distance",
                            0,
                        ),
                        "intensity": rest.get(
                            "intensity",
                            55,
                        ),
                        "repeat": 1,
                    }
                )


        # -------------------------------------------------
        # Cool-down
        # -------------------------------------------------

        cooldown = workout["cooldown"]

        flat_steps.append(
            {
                "name": "Cool-down",
                "duration_type": cooldown.get(
                    "duration_type",
                    "Time",
                ),
                "duration_minutes": cooldown.get(
                    "duration_minutes",
                    0,
                ),
                "duration_seconds": cooldown.get(
                    "duration_seconds",
                    0,
                ),
                "duration_distance": cooldown.get(
                    "duration_distance",
                    0,
                ),
                "intensity": cooldown.get(
                    "intensity",
                    55,
                ),
                "repeat": 1,
            }
        )

        return flat_steps


    # =====================================================
    # Build flat workout
    # =====================================================

    steps = flatten_workout(
        workout
    )


    # =====================================================
    # Calculate summary
    # =====================================================

    total_seconds = sum(
        duration_seconds(step)
        for step in steps
    )

    total_distance = sum(
        float(
            step.get(
                "duration_distance",
                0,
            )
        )
        for step in steps
        if step.get(
            "duration_type"
        ) == "Distance"
    )


    # =====================================================
    # Summary
    # =====================================================

    st.markdown("### Summary")

    summary_cols = st.columns(3)

    with summary_cols[0]:

        st.metric(
            "Intervals",
            len(
                workout["intervals"]
            ),
        )

    with summary_cols[1]:

        st.metric(
            "Duration",
            format_duration(
                total_seconds
            ),
        )

    with summary_cols[2]:

        if total_distance > 0:

            st.metric(
                "Distance",
                f"{total_distance:.1f} km",
            )

        else:

            st.metric(
                "Distance",
                "—",
            )


    # =====================================================
    # Visualization
    # =====================================================

    st.markdown(
        "### Workout Preview"
    )

    # -----------------------------------------------------
    # Convert FIT steps to plot format
    # -----------------------------------------------------

    plot_steps = []

    for step in steps:

        duration = duration_seconds(
            step
        )

        if duration <= 0:
            continue

        intensity = float(
            step.get(
                "intensity",
                55,
            )
        )

        # Make the visual block slightly wider
        # around the target intensity.
        target_low = intensity
        target_high = intensity

        plot_steps.append(
            {
                "name": step.get(
                    "name",
                    "Step",
                ),
                "duration": duration,
                "target_low": target_low,
                "target_high": target_high,
                "type": "step",
            }
        )

    fig = plot_workout_summary(
        plot_steps,
        sport=sport,
    )

    st.plotly_chart(
        fig,
        width="stretch",
        config={
            "displayModeBar": False,
        },
    )


# =========================================================
# FIT generation
# =========================================================

st.divider()

st.markdown("### Export")

st.write(
    "Generate a FIT workout file that can be transferred "
    "to a compatible Garmin, Wahoo or other device."
)


if st.button(
    "⚡ Generate FIT Workout",
    type="primary",
    use_container_width=True,
):

    try:

        from helpers.fit_generator import (
            generate_fit_workout,
        )

        fit_bytes = generate_fit_workout(
            sport=sport,
            name=workout_name,
            steps=steps,
            ftp=ftp,
            threshold_pace=running_threshold,
        )

        st.session_state[
            "generated_fit"
        ] = fit_bytes

        safe_name = re.sub(
            r"[^a-zA-Z0-9_-]+",
            "_",
            workout_name,
        )

        st.session_state[
            "generated_fit_name"
        ] = f"{safe_name}.fit"

        st.success(
            "FIT workout generated successfully."
        )

    except Exception as e:

        st.error(
            "Could not generate the FIT file."
        )

        st.exception(e)


# =========================================================
# Download
# =========================================================

if "generated_fit" in st.session_state:

    st.download_button(
        "⬇️ Download .FIT",
        data=st.session_state[
            "generated_fit"
        ],
        file_name=st.session_state.get(
            "generated_fit_name",
            "workout.fit",
        ),
        mime="application/octet-stream",
        type="primary",
        use_container_width=True,
    )