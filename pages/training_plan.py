import os
from datetime import date, timedelta
import pandas as pd
from pathlib import Path
import streamlit as st
from helpers.style import apply_global_style
from helpers.workout_builder import plot_workout_summary
from helpers.training_plan_functions import (
    DAYS,
    CATEGORY_COLORS,
    load_workouts,
    workout_to_plot_steps,
    generate_workout_fit,
    calculate_target_weekly_tss,
    calculate_previous_week_tss,
)

from helpers.dashboard_css import inject_card_css
from Strava.strava_user import get_training_goal, get_user_settings
from helpers.availability import load_availability
from helpers.database import load_training_plan, save_training_plan
from helpers.user_cache import get_user_cache_paths
from training_planner.periodization import (
    calculate_athlete_state,
    calculate_event_demand,
    generate_long_term_plan,
    reoptimize_future_plan,
)

apply_global_style()
inject_card_css()

ROOT = Path(__file__).resolve().parent.parent
LIBRARY_PATH = ROOT / "workouts"

@st.cache_data
def get_library(library_version=1):
    return load_workouts(LIBRARY_PATH)

def get_workout_duration(workout):
    steps = (workout or {}).get("steps", [])
    if not steps:
        return 0
    total_seconds = sum(float(step.get("duration_seconds", 0) or 0) for step in steps)
    return round(total_seconds / 60)


def get_workout_zone_minutes(workout):
    zones = {"Zone 1+2": 0.0, "Zone 3": 0.0, "Zone 4": 0.0, "Zone 5+": 0.0}
    for step in (workout or {}).get("steps", []):
        intensity = float(step.get("intensity", 0) or 0)
        minutes = float(step.get("duration_seconds", 0) or 0) / 60
        if intensity < 76:
            zones["Zone 1+2"] += minutes
        elif 76 <= intensity < 91:
            zones["Zone 3"] += minutes
        elif intensity <= 105:
            zones["Zone 4"] += minutes
        else:
            zones["Zone 5+"] += minutes
    return zones


def format_minutes(minutes):
    total_minutes = max(0, round(float(minutes or 0)))
    hours, remaining_minutes = divmod(total_minutes, 60)
    if hours:
        return f"{hours}h {remaining_minutes:02d}min"
    return f"{remaining_minutes}min"


def clean_activity_type(value):
    return str(value or "Activity").replace("root='", "").replace("'", "")


def get_completed_week_zones(activities, week_start, today, ftp):
    zones = {"Zone 1+2": 0.0, "Zone 3": 0.0, "Zone 4": 0.0, "Zone 5+": 0.0}
    if activities is None or activities.empty or "date" not in activities:
        return zones
    frame = activities.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date
    frame = frame[(frame["date"] >= week_start) & (frame["date"] < today)]
    for _, activity in frame.iterrows():
        activity_type = str(activity.get("type", ""))
        power = activity.get("weighted_average_watts")
        if power is None or pd.isna(power):
            power = activity.get("average_watts")
        has_power = "ride" in activity_type.lower() and ftp > 0 and power is not None and not pd.isna(power)
        if has_power:
            intensity = float(power) / ftp
            if intensity < 0.76:
                zone = "Zone 1+2"
            elif intensity < 0.91:
                zone = "Zone 3"
            else:
                zone = "Zone 4" if intensity <= 1.05 else "Zone 5+"
            zones[zone] += float(activity.get("moving_time", 0) or 0) / 60
        else:
            for zone, columns in (("Zone 1+2", ("time_z1_hr", "time_z2_hr")), ("Zone 3", ("time_z3_hr",)), ("Zone 4", ("time_z4_hr",)), ("Zone 5+", ("time_z5_hr",))):
                for column in columns:
                    value = activity.get(column, 0)
                    zones[zone] += 0 if pd.isna(value) else float(value) / 60
    return zones

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


@st.dialog("Workout details")
def workout_details_dialog(workout):
    category = workout.get("_category", workout.get("category", "Workout"))
    duration = get_workout_duration(workout)
    target_tss = float(workout.get("target_tss", workout.get("estimated_tss", 0)) or 0)
    target_if = float(workout.get("target_if", 0) or 0)
    st.subheader(workout.get("name", "Workout"))
    st.caption(f"{category} · {format_minutes(duration)} · IF {target_if:.2f} · {target_tss:.0f} TSS")
    render_preview(workout, f"details_preview_{workout.get('id', workout.get('_file', 'workout'))}", height=260)
    try:
        fit_bytes, filename = generate_workout_fit(workout)
        st.download_button(
            "Download FIT",
            data=fit_bytes,
            file_name=filename,
            mime="application/octet-stream",
            use_container_width=True,
            key=f"details_fit_{workout.get('id', workout.get('_file', 'workout'))}",
        )
    except Exception:
        st.warning("FIT file unavailable for this workout.")


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
            plan_date = plan.get("date")
            for index, stored_plan in enumerate(st.session_state.training_plan_horizon):
                if stored_plan.get("date") == plan_date:
                    st.session_state.training_plan_horizon[index] = plan
                    break
            st.rerun()

username = st.session_state.get("username")
if not username:
    st.error("Please log in first.")
    st.stop()

training_goal = get_training_goal(username)

if not isinstance(training_goal, dict) or not training_goal.get("name"):
    st.markdown('<div class="dashboard-title">Training Plan</div>', unsafe_allow_html=True)
    st.info("Select a training goal before creating your training plan.")
    if st.button("Select training goal", type="primary"):
        st.session_state["settings_section"] = "Training Goal"
        st.switch_page("pages/settings.py")
    st.stop()

if isinstance(training_goal, dict):
    goal = training_goal["name"]
else:
    goal = training_goal

goal_labels = {
    "general_fitness": "General Fitness",
    "gran_fondo": "Gran Fondo",
    "criterium": "Criterium",
}

goal_label = goal_labels.get(
    goal,
    str(goal).replace("_", " ").title(),
)

weekly_availability = load_availability(username).get("weekly", {})
has_available_day = any(
    float(day.get("hours", 0) or 0) > 0
    or (day.get("available") and day.get("start") and day.get("end"))
    for day in weekly_availability.values()
    if isinstance(day, dict)
)

if not has_available_day:
    st.markdown('<div class="dashboard-title">Training Plan</div>', unsafe_allow_html=True)
    st.info("Set your weekly availability before creating a training plan.")
    if st.button("Select weekly availability", type="primary"):
        st.switch_page("pages/settings_availability.py")
    st.stop()

availability_summary = " · ".join(
    f"{day[:3]} {float(data.get('hours', 0) or 0):g}h"
    for day, data in weekly_availability.items()
    if isinstance(data, dict) and float(data.get("hours", 0) or 0) > 0
)
st.caption(f"Weekly availability: {availability_summary}")

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

workouts = get_library(library_version=2)
plan_version = 14
goal_date = training_goal.get("goal_date")

weekly_tss = calculate_target_weekly_tss(username)
previous_week_tss = calculate_previous_week_tss(username)
planning_settings = get_user_settings(username)
plan_inputs_signature = repr((
    goal,
    goal_date,
    training_goal.get("event_distance_km"),
    training_goal.get("event_climb_m"),
    training_goal.get("event_type"),
    planning_settings.get("ftp"),
    planning_settings.get("athlete_level"),
    planning_settings.get("training_progression"),
    sorted(
        (day, data.get("hours"), data.get("available"))
        for day, data in weekly_availability.items()
        if isinstance(data, dict)
    ),
))

if previous_week_tss > 0:
    change = ((weekly_tss / previous_week_tss) - 1) * 100
    st.caption(
        f"Last week: {previous_week_tss:.0f} TSS · "
        f"This week: {weekly_tss:.0f} TSS · "
        f"{change:+.0f}%"
    )
else:
    st.caption("Build your week and choose the workout that fits you best.")

activity_file, _ = get_user_cache_paths(username)
activities = pd.read_csv(activity_file) if os.path.exists(activity_file) else None
today = date.today()
timeline_start = today - timedelta(days=today.weekday())
completed_zone_minutes = get_completed_week_zones(
    activities,
    timeline_start,
    today,
    float(planning_settings.get("ftp", 0) or 0),
)
completed_week_tss = 0.0
if activities is not None and not activities.empty and "date" in activities:
    activity_dates = pd.to_datetime(activities["date"], errors="coerce").dt.date
    current_week_rows = activities[
        (activity_dates >= timeline_start) & (activity_dates <= today)
    ]
    if "stress" in current_week_rows:
        completed_week_tss = pd.to_numeric(
            current_week_rows["stress"], errors="coerce"
        ).fillna(0).sum()

athlete_state = calculate_athlete_state(
    activities,
    ftp=float(planning_settings.get("ftp", 0) or 0),
)
activity_state_signature = repr(athlete_state)

if "training_plan_horizon" not in st.session_state:
    st.session_state.training_plan_horizon = load_training_plan(username) or []

goal_day = pd.to_datetime(goal_date, errors="coerce").date() if goal_date else None
stored_plan = st.session_state.training_plan_horizon
stored_end = (
    pd.to_datetime(stored_plan[-1].get("date"), errors="coerce").date()
    if stored_plan else None
)
plan_needs_update = (
    not stored_plan
    or st.session_state.get("training_plan_version") != plan_version
    or st.session_state.get("training_plan_inputs") != plan_inputs_signature
    or (goal_day is not None and (stored_end is None or stored_end < goal_day))
)

if plan_needs_update:
    settings = planning_settings
    availability = weekly_availability
    st.session_state.training_plan_horizon = generate_long_term_plan(
        goal=goal,
        goal_date=goal_date,
        availability=availability,
        workouts=workouts,
        baseline_tss=weekly_tss,
        progression=float(settings.get("training_progression", 8) or 8),
        start_date=timeline_start,
        activities=activities,
        athlete_level=settings.get("athlete_level"),
        completed_zone_minutes=completed_zone_minutes,
        completed_tss=completed_week_tss,
        event_demand=(
            calculate_event_demand(
                training_goal.get("event_distance_km"),
                training_goal.get("event_climb_m"),
                training_goal.get("event_type"),
                settings.get("ftp"),
            )
            if training_goal.get("event_distance_km")
            else None
        ),
    )
    save_training_plan(username, st.session_state.training_plan_horizon)
    st.session_state.training_plan_version = plan_version
    st.session_state.training_plan_inputs = plan_inputs_signature
    st.session_state.training_plan_activity_state = activity_state_signature
elif st.session_state.get("training_plan_activity_state") != activity_state_signature:
    st.session_state.training_plan_horizon = reoptimize_future_plan(
        plan=st.session_state.training_plan_horizon,
        goal=goal,
        goal_date=goal_date,
        availability=weekly_availability,
        workouts=workouts,
        baseline_tss=weekly_tss,
        progression=float(planning_settings.get("training_progression", 8) or 8),
        activities=activities,
        athlete_level=planning_settings.get("athlete_level"),
        completed_zone_minutes=completed_zone_minutes,
        completed_tss=completed_week_tss,
        event_demand=(
            calculate_event_demand(
                training_goal.get("event_distance_km"),
                training_goal.get("event_climb_m"),
                training_goal.get("event_type"),
                planning_settings.get("ftp"),
            )
            if training_goal.get("event_distance_km")
            else None
        ),
        current_date=today,
        horizon_days=14,
    )
    save_training_plan(username, st.session_state.training_plan_horizon)
    st.session_state.training_plan_activity_state = activity_state_signature

training_plan = st.session_state.training_plan_horizon
if not training_plan:
    st.info("Set weekly availability to create your training plan.")
    st.stop()

display_plan = list(training_plan)
if activities is not None and not activities.empty and "date" in activities:
    completed_frame = activities.copy()
    completed_frame["date"] = pd.to_datetime(completed_frame["date"], errors="coerce").dt.date
    completed_frame = completed_frame[
        (completed_frame["date"] >= timeline_start) & (completed_frame["date"] <= today)
    ]
    plan_by_date = {str(item.get("date")): item for item in display_plan}
    for current_date, day_activities in completed_frame.groupby("date"):
        actual_tss = pd.to_numeric(
            day_activities["stress"] if "stress" in day_activities else 0,
            errors="coerce",
        )
        if not isinstance(actual_tss, pd.Series):
            actual_tss = pd.Series(0.0, index=day_activities.index)
        actual_tss = actual_tss.fillna(0).sum()
        activity_type = clean_activity_type(day_activities.iloc[0].get("type", "Completed activity"))
        completed_item = {
            "date": current_date.isoformat(),
            "day": current_date.strftime("%A"),
            "category": activity_type,
            "target_tss": float(actual_tss),
            "actual_tss": float(actual_tss),
            "workout": None,
            "completed": True,
            "rest": False,
            "week_number": 1,
            "week_target_tss": plan_by_date.get(
                current_date.isoformat(), training_plan[0]
            ).get("week_target_tss", 0),
        }
        if current_date.isoformat() in plan_by_date:
            plan_by_date[current_date.isoformat()] = completed_item
        else:
            display_plan.append(completed_item)
    display_plan = list(plan_by_date.values())
    display_plan.sort(key=lambda item: item.get("date", ""))

st.subheader("This week")
today = date.today()
timeline_start = today - timedelta(days=today.weekday())
timeline_dates = [timeline_start + timedelta(days=offset) for offset in range(7)]
plans_by_date = {plan.get("date"): plan for plan in training_plan}
activity_by_date = {}
activity_type_by_date = {}
if activities is not None and not activities.empty and "date" in activities:
    activity_frame = activities.copy()
    activity_frame["date"] = pd.to_datetime(activity_frame["date"], errors="coerce").dt.date
    if "stress" in activity_frame:
        activity_frame["stress"] = pd.to_numeric(activity_frame["stress"], errors="coerce").fillna(0)
        activity_by_date = activity_frame.groupby("date")["stress"].sum().to_dict()
        if "type" in activity_frame:
            activity_type_by_date = (
                activity_frame.assign(type=activity_frame["type"].map(clean_activity_type))
                .groupby("date")["type"].first().to_dict()
            )

timeline_cols = st.columns(7, gap="small")
for column, current_date in zip(timeline_cols, timeline_dates):
    with column:
        date_label = current_date.strftime("%a").upper()
        short_date = current_date.strftime("%d %b")
        activity_tss = float(activity_by_date.get(current_date, 0) or 0)
        has_activity = current_date <= today and activity_tss > 0
        is_past = current_date < today
        plan = plans_by_date.get(current_date.isoformat())
        if is_past or has_activity:
            activity_name = activity_type_by_date.get(current_date, "Activity") if activity_tss else "Rest"
            detail = f"{activity_tss:.0f} TSS" if activity_tss else "No activity"
            if activity_tss <= 0:
                color = "#98a6b3"
            elif activity_tss < 50:
                color = "#6f9bb2"
            elif activity_tss < 100:
                color = "#d39a45"
            else:
                color = "#b85c5c"
        elif not plan or plan.get("rest"):
            activity_name = "Rest"
            detail = "Recovery"
            color = "#98a6b3"
        else:
            activity_name = plan.get("category", "Training")
            workout = plan.get("workout") or {}
            duration = get_workout_duration(workout)
            hours, minutes = divmod(duration, 60)
            intensity = float((workout or {}).get("target_if", 0) or 0)
            detail = f"{hours}h {minutes:02d}min · IF {intensity:.2f}" if hours else f"{minutes}min · IF {intensity:.2f}"
            color = CATEGORY_COLORS.get(activity_name, "#557b91")
        background = f"{color}18" if not is_past else f"{color}12"
        st.markdown(
            f'<div style="background:{background};border:1px solid {color}55;'
            f'border-top:3px solid {color};border-radius:7px;padding:9px 7px;'
            'min-height:92px;text-align:center;">'
            f'<div style="font-size:10px;color:#7a8792;font-weight:700;">{date_label}'
            f'{" · TODAY" if current_date == today else ""}</div>'
            f'<div style="font-size:11px;color:#7a8792;margin-top:2px;">{short_date}</div>'
            f'<div style="font-size:12px;color:#17212b;font-weight:700;margin-top:13px;">{activity_name}</div>'
            f'<div style="font-size:10px;color:#6b7785;margin-top:4px;">{detail}</div></div>',
            unsafe_allow_html=True,
        )
        if not is_past and plan and plan.get("workout"):
            if st.button("View workout", key=f"timeline_details_{current_date}", use_container_width=True):
                workout_details_dialog(plan["workout"])

st.subheader("Weekly Training Load / Intensity Progress")
week_plan_items = [
    plan for plan in training_plan
    if timeline_start.isoformat() <= str(plan.get("date", "")) <= (timeline_start + timedelta(days=6)).isoformat()
]
zone_targets = {zone: 0.0 for zone in ("Zone 1+2", "Zone 3", "Zone 4", "Zone 5+")}
zone_forecast = {zone: 0.0 for zone in zone_targets}
zone_completed = {zone: 0.0 for zone in zone_targets}
week_budget = next(
    (plan.get("intensity_budget") for plan in week_plan_items
     if isinstance(plan.get("intensity_budget"), dict)),
    None,
)
if week_budget:
    budget_zones = week_budget.get("zone_minutes", {})
    zone_targets["Zone 1+2"] = float(budget_zones.get("Zone 1+2", 0) or 0)
    zone_targets["Zone 3"] = float(budget_zones.get("Zone 3", 0) or 0)
    zone_targets["Zone 4"] = float(budget_zones.get("Zone 4", 0) or 0)
    zone_targets["Zone 5+"] = float(budget_zones.get("Zone 5+", 0) or 0)
for plan in week_plan_items:
    planned_zones = get_workout_zone_minutes(plan.get("workout"))
    for zone in zone_targets:
        if str(plan.get("date")) > today.isoformat() and not plan.get("rest"):
            zone_forecast[zone] += planned_zones[zone]

if not any(zone_targets.values()):
    planner_week_tss = max(
        (float(plan.get("week_target_tss", 0) or 0) for plan in week_plan_items),
        default=0,
    ) or float(weekly_tss or 0)
    zone_targets["Zone 1+2"] = planner_week_tss * 0.6 * 0.6
    zone_targets["Zone 3"] = planner_week_tss * 0.1 * 0.6
    zone_targets["Zone 4"] = planner_week_tss * 0.3 * 0.6 * 0.7
    zone_targets["Zone 5+"] = planner_week_tss * 0.3 * 0.6 * 0.3

if activities is not None and not activities.empty and "date" in activities:
    zone_settings = get_user_settings(username)
    ftp = float(zone_settings.get("ftp", 0) or 0)
    current_week_activities = activity_frame[
        (activity_frame["date"] >= timeline_start)
        & (activity_frame["date"] <= today)
    ]
    for _, activity in current_week_activities.iterrows():
        activity_type = str(activity.get("type", ""))
        power_value = activity.get("weighted_average_watts")
        if power_value is None or pd.isna(power_value):
            power_value = activity.get("average_watts")
        is_ride_with_power = (
            "ride" in activity_type.lower()
            and ftp > 0
            and power_value is not None
            and not pd.isna(power_value)
        )
        duration_minutes = float(activity.get("moving_time", 0) or 0) / 60
        if is_ride_with_power:
            intensity = float(power_value) / ftp
            if intensity < 0.76:
                zone_completed["Zone 1+2"] += duration_minutes
            elif intensity < 0.91:
                zone_completed["Zone 3"] += duration_minutes
            else:
                zone_completed["Zone 4"] += duration_minutes if intensity <= 1.05 else 0
                zone_completed["Zone 5+"] += duration_minutes if intensity > 1.05 else 0
        else:
            for zone, columns in (
                ("Zone 1+2", ("time_z1_hr", "time_z2_hr")),
                ("Zone 3", ("time_z3_hr",)),
                ("Zone 4", ("time_z4_hr",)),
                ("Zone 5+", ("time_z5_hr",)),
            ):
                for column in columns:
                    value = activity.get(column, 0)
                    zone_completed[zone] += 0 if pd.isna(value) else float(value) / 60

zone_colors = {"Zone 1+2": "#6f9bb2", "Zone 3": "#d39a45", "Zone 4": "#b85c5c", "Zone 5+": "#8f3f56"}
for zone in zone_targets:
    target = zone_targets[zone]
    current = zone_completed[zone] + zone_forecast[zone]
    progress = min(1.0, current / target) if target else 0.0
    remaining = max(0.0, target - current)
    st.markdown(
        f'<div style="margin:6px 0 10px;">'
        f'<div style="display:flex;justify-content:space-between;font-size:11px;color:#526170;">'
        f'<strong>{zone}</strong><span>target {format_minutes(target)} · completed {format_minutes(zone_completed[zone])} · remaining {format_minutes(remaining)}</span></div>'
        f'<div style="height:7px;background:#e5eaed;border-radius:4px;margin-top:4px;overflow:hidden;">'
        f'<div style="width:{progress * 100:.1f}%;height:100%;background:{zone_colors[zone]};"></div></div></div>',
        unsafe_allow_html=True,
    )

tss_target = max(
    (float(plan.get("week_target_tss", 0) or 0) for plan in week_plan_items),
    default=float(weekly_tss or 0),
)
future_planned_tss = sum(
    float((plan.get("workout") or {}).get("target_tss", 0) or 0)
    for plan in week_plan_items
    if str(plan.get("date")) > today.isoformat() and plan.get("workout")
)
tss_current = completed_week_tss + future_planned_tss
tss_remaining = max(0.0, tss_target - tss_current)
tss_progress = min(1.0, tss_current / tss_target) if tss_target else 0.0
st.markdown(
    f'<div style="margin:6px 0 10px;">'
    f'<div style="display:flex;justify-content:space-between;font-size:11px;color:#526170;">'
    f'<strong>TSS</strong><span>target {tss_target:.0f} · completed {completed_week_tss:.0f} · '
    f'planned {future_planned_tss:.0f} · remaining {tss_remaining:.0f}</span></div>'
    f'<div style="height:7px;background:#e5eaed;border-radius:4px;margin-top:4px;overflow:hidden;">'
    f'<div style="width:{tss_progress * 100:.1f}%;height:100%;background:#4f7f92;"></div></div></div>',
    unsafe_allow_html=True,
)

if training_plan:
    st.divider()
    st.subheader("Full plan until goal")
    weeks = {}
    for plan in display_plan:
        weeks.setdefault(plan["week_number"], []).append(plan)

    for week_number, week_plans in weeks.items():
        target_week_tss = float(week_plans[0]["week_target_tss"])
        planned_week_tss = sum(
            float((plan.get("workout") or {}).get(
                "target_tss",
                (plan.get("workout") or {}).get(
                    "estimated_tss", plan.get("target_tss", 0)
                ),
            ) or plan.get("target_tss", 0) or 0)
            for plan in week_plans
            if not plan.get("completed")
        )
        week_dates = {
            pd.to_datetime(plan.get("date")).date()
            for plan in week_plans
        }
        completed_week_tss = sum(
            float(activity_by_date.get(activity_date, 0) or 0)
            for activity_date in week_dates
            if activity_date <= today
        )
        total_week_tss = planned_week_tss + completed_week_tss
        remaining_week_budget = target_week_tss - completed_week_tss
        week_label = (
            f"Week {week_number} · target {week_plans[0]['week_target_tss']} TSS"
            f" · covered {total_week_tss:.0f} TSS"
            f" ({completed_week_tss:.0f} completed + {planned_week_tss:.0f} planned)"
            f" · budget remaining {remaining_week_budget:.0f} TSS"
        )
        if len(week_plans) < 7:
            week_label += " · partial week"
        if week_plans[0].get("deload"):
            week_label += " · deload"
        st.markdown(
            f'<div style="font-size:12px;font-weight:700;margin:10px 0 4px;">'
            f'{week_label}</div>',
            unsafe_allow_html=True,
        )
        if len(week_plans) == 7 and abs(total_week_tss - target_week_tss) >= max(20, target_week_tss * 0.1):
            st.warning(
                "This week's planned TSS cannot closely match the target with the "
                "current weekly availability and workout library."
            )
        plans_by_day = {plan["day"]: plan for plan in week_plans}
        week_cols = st.columns(7, gap="small")
        for day, col in zip(DAYS, week_cols):
            with col:
                plan = plans_by_day.get(day)
                if not plan:
                    st.markdown('<div style="height:48px;"></div>', unsafe_allow_html=True)
                    continue
                if plan.get("rest"):
                    training_label = "Rest"
                else:
                    category = plan.get("category", "Endurance")
                    duration = get_workout_duration(plan.get("workout"))
                    hours, minutes = divmod(duration, 60)
                    duration_text = f"{hours}h {minutes:02d}min" if hours else f"{minutes}min"
                    training_label = f"{category} · {duration_text}"
                color = "#94A3B8" if plan.get("rest") else CATEGORY_COLORS.get(category, "#64748B")
                st.markdown(
                    f'<div style="border-top:3px solid {color};background:{color}12;'
                    'border-radius:6px;padding:5px 4px;height:48px;text-align:center;'
                    'overflow:hidden;">'
                    f'<div style="font-size:9px;color:#64748B;">{day[:3]} · {plan["date"][5:]}</div>'
                    f'<div style="font-size:10px;font-weight:700;color:{color};margin-top:5px;">'
                    f'{training_label}</div></div>',
                    unsafe_allow_html=True,
                )
                if plan.get("workout"):
                    if st.button("View", key=f"full_plan_details_{plan['date']}", use_container_width=True):
                        workout_details_dialog(plan["workout"])

st.stop()