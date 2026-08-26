from datetime import date
from pathlib import Path
import streamlit as st
from helpers.periodisation_view import open_periodisation_dialog
from helpers.style import apply_global_style
from helpers.workout_builder import plot_workout_summary
from helpers.training_plan_functions import (
    CATEGORIES,
    DAYS,
    CATEGORY_COLORS,
    load_workouts,
    get_workouts,
    workout_label,
    workout_to_plot_steps,
    generate_workout_fit,
    build_week,
    calculate_weekly_tss,
    calculate_target_weekly_tss,
    calculate_previous_week_tss,
)

from helpers.periodisation_view import open_periodisation_dialog
from helpers.dashboard_css import inject_card_css
from Strava.strava_user import get_training_goal

apply_global_style()
inject_card_css()

ROOT = Path(__file__).resolve().parent.parent
LIBRARY_PATH = ROOT / "training_planner" / "workout_library"

@st.cache_data
def get_library():
    return load_workouts(LIBRARY_PATH)

def get_workout_duration(workout):
    steps = workout.get("steps", [])
    if not steps:
        return 0
    total_seconds = sum(float(step.get("duration_seconds", 0) or 0) for step in steps)
    return round(total_seconds / 60)

def render_preview(workout, key, height=115):
    steps = workout_to_plot_steps(workout)
    if not steps:
        return
    fig = plot_workout_summary(steps, sport="Cycling")
    fig.update_layout(
        height=height,
        margin=dict(l=5, r=5, t=3, b=3),
        xaxis=dict(showticklabels=False, showgrid=False, title=None),
        yaxis=dict(showticklabels=False, showgrid=False, title=None),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=key)

@st.dialog("Choose workout")
def edit_workout_dialog(day, plan, workouts):
    category = plan.get("category", "Endurance")
    target_tss = float(plan.get("target_tss", 0) or 0)
    color = CATEGORY_COLORS.get(category, "#64748B")
    options = [workout for workout in workouts if workout.get("_category") == category]
    if not options:
        st.warning(f"No {category} workouts are available.")
        return
    options = sorted(
        options,
        key=lambda workout: abs(float(workout.get("target_tss", 0) or 0) - target_tss),
    )
    st.markdown(
        f'<div style="font-size:13px;color:#64748B;margin-bottom:14px;">'
        f'{day} · {category} · planned target {target_tss:.0f} TSS'
        f'</div>',
        unsafe_allow_html=True,
    )
    current = plan.get("workout")
    for index, workout in enumerate(options):
        actual_tss = float(workout.get("target_tss", 0) or 0)
        duration = get_workout_duration(workout)
        difference = actual_tss - target_tss
        selected = current and workout.get("_file") == current.get("_file")
        border = color if selected else "rgba(148,163,184,.18)"
        background = f"{color}12" if selected else "rgba(148,163,184,.04)"
        st.markdown(
            f'<div style="border:1px solid {border};border-radius:12px;padding:10px 12px 6px;margin-top:8px;background:{background};">'
            f'<div style="font-size:13px;font-weight:700;">{workout.get("name","Workout")}</div>'
            f'<div style="font-size:11px;color:#64748B;margin-top:3px;">{duration} min · {actual_tss:.0f} TSS · {difference:+.0f} vs target</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        render_preview(workout, f"dialog_preview_{day}_{index}", height=85)
        button_label = "Selected" if selected else "Select"
        if st.button(
            button_label,
            key=f"select_workout_{day}_{index}",
            use_container_width=True,
            disabled=selected,
        ):
            plan["workout"] = workout
            st.session_state.training_plan[day] = plan
            st.rerun()

username = st.session_state.get("username")
if not username:
    st.error("Please log in first.")
    st.stop()

training_goal = get_training_goal(username)

if isinstance(training_goal, dict):
    goal = training_goal.get("name", "general_fitness")
else:
    goal = training_goal or "general_fitness"

goal_labels = {
    "general_fitness": "General Fitness",
    "gran_fondo": "Gran Fondo",
    "criterium": "Criterium",
}

goal_label = goal_labels.get(
    goal,
    str(goal).replace("_", " ").title(),
)

header_col, edit_col = st.columns([8, 1], vertical_alignment="center")

with header_col:
    st.markdown(
        f'<div class="dashboard-title">Training Plan '
        f'<span style="font-size:18px;color:#94A3B8;font-weight:400;">'
        f'for {goal_label}'
        f'</span></div>',
        unsafe_allow_html=True,
    )

with edit_col:
    if st.button("Edit", key="edit_training_goal"):
        st.session_state["settings_section"] = "Training Goal"
        st.switch_page("pages/settings.py")

workouts = get_library()

weekly_tss = calculate_target_weekly_tss(username)
previous_week_tss = calculate_previous_week_tss(username)

if previous_week_tss > 0:
    change = ((weekly_tss / previous_week_tss) - 1) * 100
    st.caption(
        f"Last week: {previous_week_tss:.0f} TSS · "
        f"This week: {weekly_tss:.0f} TSS · "
        f"{change:+.0f}%"
    )
else:
    st.caption("Build your week and choose the workout that fits you best.")

if "training_plan" not in st.session_state:
    st.session_state.training_plan = {day: None for day in DAYS}

rebuild_requested = st.button(
    "Regenerate plan",
    use_container_width=True,
)

if rebuild_requested:
    st.session_state.training_plan = {day: None for day in DAYS}

planned = build_week(
    weekly_tss,
    username,
    workouts=workouts,
)

if not planned:
    st.info(
        "No training days available yet. Set your weekly availability in Settings to generate a plan."
    )

for item in planned:
    day = item["day"]
    if st.session_state.training_plan[day] is None:
        st.session_state.training_plan[day] = {
            "day": day,
            "category": item.get("category", "Endurance"),
            "target_tss": float(item.get("target_tss", 0) or 0),
            "workout": item.get("workout"),
        }
    else:
        st.session_state.training_plan[day]["target_tss"] = float(
            item.get("target_tss", 0) or 0
        )

st.markdown(
    """<style>
.plan-card{border:1px solid rgba(148,163,184,.18);border-radius:14px;padding:12px 10px 10px;min-height:135px;transition:.2s ease;background:rgba(255,255,255,.02)}
.plan-card:hover{transform:translateY(-4px);box-shadow:0 12px 28px rgba(0,0,0,.10)}
.plan-day{font-size:11px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.05em}
.plan-category{font-size:11px;margin-top:7px;font-weight:600}
.plan-name{font-size:13px;font-weight:700;line-height:1.25;margin-top:5px}
.plan-tss{font-size:11px;color:#64748B;margin-top:5px}
.plan-actions{margin-top:8px}
</style>""",
    unsafe_allow_html=True,
)
title_col, button_col = st.columns([5, 2], vertical_alignment="center")

with title_col:
    st.markdown("### Upcoming 7 days")

with button_col:
    if st.button("Periodisation", use_container_width=True):
        open_periodisation_dialog(username)

today_index = date.today().weekday()
upcoming_days = DAYS[today_index:] + DAYS[:today_index]

cols = st.columns(7, gap="small")

for col, day in zip(cols, upcoming_days):
    with col:
        plan = st.session_state.training_plan.get(day)

        if not plan:
            st.markdown(
                f'<div class="plan-card">'
                f'<div class="plan-day">{day[:3]}</div>'
                f'<div style="margin-top:15px;color:#94A3B8;font-size:12px;">Rest</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            continue

        workout = plan.get("workout")
        category = plan.get("category", "Endurance")
        color = CATEGORY_COLORS.get(category, "#64748B")

        if not workout:
            st.markdown(
                f'<div class="plan-card" style="border-top:3px solid {color};">'
                f'<div class="plan-day">{day[:3]}</div>'
                f'<div style="font-size:18px;font-weight:800;color:{color};margin-top:18px;">{category}</div>'
                f'<div class="plan-name">No workout available</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            if st.button("Edit", key=f"edit_{day}", use_container_width=True):
                edit_workout_dialog(day, plan, workouts)

            continue

        actual_tss = float(workout.get("target_tss", 0) or 0)

        workout_duration = get_workout_duration(workout)
        hours = workout_duration // 60
        minutes = workout_duration % 60

        if hours > 0:
            duration_text = f"{hours}h {minutes:02d}min" if minutes else f"{hours}h"
        else:
            duration_text = f"{minutes}min"

        st.markdown(
            f'<div class="plan-card" style="border-top:3px solid {color};">'
            f'<div class="plan-day">{day[:3]}</div>'
            f'<div style="font-size:18px;font-weight:800;color:{color};margin-top:16px;">{category}</div>'
            f'<div style="font-size:14px;font-weight:600;margin-top:6px;">{duration_text}</div>'
            f'<div class="plan-tss">{actual_tss:.0f} TSS</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        render_preview(workout, f"preview_{day}")

        action_col1, action_col2 = st.columns(2)

        with action_col1:
            try:
                fit_bytes, filename = generate_workout_fit(workout)

                st.download_button(
                    "↓ FIT",
                    data=fit_bytes,
                    file_name=filename,
                    mime="application/octet-stream",
                    use_container_width=True,
                    key=f"fit_{day}",
                )
            except Exception:
                st.caption("FIT unavailable")

        with action_col2:
            if st.button(
                "Edit",
                key=f"edit_{day}",
                use_container_width=True,
            ):
                edit_workout_dialog(day, plan, workouts)

total_tss = calculate_weekly_tss(
    st.session_state.training_plan
)

target_gap = total_tss - float(weekly_tss)
target_hit = (
    0
    if weekly_tss <= 0
    else total_tss / float(weekly_tss) * 100
)

st.divider()

c1, c2, c3 = st.columns(3)

with c1:
    st.metric(
        "Planned TSS",
        f"{total_tss:.0f}",
        delta=f"{target_gap:+.0f} vs target",
    )

with c2:
    st.metric(
        "Target TSS",
        f"{weekly_tss:.0f}",
    )

with c3:
    st.metric(
        "Target hit",
        f"{target_hit:.0f}%",
    )