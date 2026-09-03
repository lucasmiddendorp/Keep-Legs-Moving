
import os
import hashlib
import inspect
from datetime import date,timedelta
from pathlib import Path
import pandas as pd
import streamlit as st
from helpers.style import apply_global_style
from helpers.dashboard_css import inject_card_css
from helpers.training_plan_functions import DAYS,CATEGORY_COLORS,load_workouts,calculate_target_weekly_tss,calculate_previous_week_tss
from helpers.training_page_functions import RECOVERY_COLOR,empty_zones,get_zone_minutes_from_steps,get_completed_week_zones,get_workout_duration,get_workout_if,get_workout_zone_minutes,format_total_time,format_minutes,clean_activity_type,render_small_progress_circle,render_clickable_workout_card,render_static_day_card,render_week_summary,render_full_week,zone_color
from Strava.strava_user import get_training_goal,get_user_settings,save_user_settings
from helpers.availability import load_availability
from helpers.database import load_training_plan,save_training_plan,load_training_test_status,save_training_test_status
from helpers.database import load_activity_cache
from training_planner import TrainingPlanBuilder

apply_global_style()
inject_card_css()


ROOT=Path(__file__).resolve().parent.parent
LIBRARY_PATH=ROOT/"workouts"
username=st.session_state.get("username")

if not username:
    st.error("Please log in first.")
    st.stop()

training_goal=get_training_goal(username)
goal_sport = training_goal.get("sport")

if not isinstance(training_goal,dict) or not training_goal.get("name"):
    st.markdown('<div class="dashboard-title">Training Plan</div>',unsafe_allow_html=True)
    st.info("Select a training goal before creating your training plan.")
    if st.button("Select training goal",type="primary"):
        st.session_state["profile_section"]="Training Goal"
        st.switch_page("pages/profile.py")
    st.stop()

goal=str(training_goal["name"]).strip().lower().replace(" ","_").replace("-","_")
running_goals={"5k","10k","half_marathon","marathon"}
is_running_plan=goal in running_goals
sport=goal_sport if goal_sport else ("Running" if is_running_plan else "Cycling")

test_status=load_training_test_status(username,sport,goal)
test_done=test_status["done"]
test_answered=test_status["answered"]
test_question=(
    "Have you done a 6-minute running test?"
    if sport == "Running"
    else "Have you done a 20-minute FTP test?"
)
test_answer=st.session_state.get(f"training_test_answer_{sport}_{goal}")
if not test_answered:
    with st.container(border=True):
        prompt_col, yes_col, no_col = st.columns([6, 1, 1], vertical_alignment="center")
        with prompt_col:
            st.markdown(
                f'<div style="font-size:13px;font-weight:650;color:#17212b;">Time for a test <span style="font-size:12px;font-weight:400;color:#7a8792;margin-left:8px;">{test_question}</span></div>',
                unsafe_allow_html=True,
            )
        with yes_col:
            yes_pressed=st.button("Yes",key=f"training_test_yes_{sport}",use_container_width=True)
        with no_col:
            no_pressed=st.button("No",key=f"training_test_no_{sport}",use_container_width=True)
        if yes_pressed:
            save_training_test_status(username,sport,goal,True)
            st.session_state.pop("training_plan_horizon",None)
            st.session_state.pop("training_plan_signature",None)
            st.rerun()
        if no_pressed:
            save_training_test_status(username,sport,goal,False)
            st.session_state[f"training_test_answer_{sport}_{goal}"]="No"
            test_answer="No"

goal_labels={"general_fitness":"General Fitness","gran_fondo":"Gran Fondo","criterium":"Criterium","5k":"5K","10k":"10K","half_marathon":"Half Marathon","marathon":"Marathon"}
goal_label=goal_labels.get(goal,str(goal).replace("_"," ").title())
weekly_availability=load_availability(username).get("weekly",{})
availability=TrainingPlanBuilder().set_availability(weekly_availability).get_availability()
has_available_day=availability.has_available_day()

if not has_available_day:
    st.markdown('<div class="dashboard-title">Training Plan</div>',unsafe_allow_html=True)
    st.info("Set your weekly availability before creating your training plan.")
    if st.button("Select weekly availability",type="primary"):
        st.session_state["profile_section"]="Weekly Availability"
        st.switch_page("pages/profile.py")
    st.stop()

planning_settings=get_user_settings(username)
session_count_options=[2,3,4,5,6]
stored_sessions_per_week=planning_settings.get("sessions_per_week")
default_sessions=stored_sessions_per_week if stored_sessions_per_week in session_count_options else 4
sessions_per_week=st.session_state.get("sessions_per_week_select",default_sessions)
day_order=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
day_short={"Monday":"MON","Tuesday":"TUE","Wednesday":"WED","Thursday":"THU","Friday":"FRI","Saturday":"SAT","Sunday":"SUN"}

workouts_path = Path(LIBRARY_PATH) / sport.lower()
print(workouts_path)
workouts = load_workouts(workouts_path)

goal_date=training_goal.get("goal_date")
weekly_tss=calculate_target_weekly_tss(username)
previous_week_tss=calculate_previous_week_tss(username)

stored_activities=load_activity_cache(username)
activities=pd.DataFrame(stored_activities) if stored_activities else None
today=date.today()
timeline_start=today-timedelta(days=today.weekday())
completed_week_tss=0.0
completed_session_dates=[]
completed_activity_signature=()

if activities is not None and not activities.empty and "date" in activities.columns:
    activity_dates=pd.to_datetime(activities["date"],errors="coerce").dt.date
    current_week_rows=activities[(activity_dates>=timeline_start)&(activity_dates<=today)]
    completed_session_dates=current_week_rows["date"].dropna().tolist()
    completed_activity_signature=repr(current_week_rows.fillna("").to_dict("records"))
    if "stress" in current_week_rows.columns:
        completed_week_tss=pd.to_numeric(current_week_rows["stress"],errors="coerce").fillna(0).sum()

planner=(TrainingPlanBuilder()
    .set_availability(weekly_availability)
    .set_goal_and_phase(goal)
    .set_recovery_profile(activities)
    .set_workouts(workouts))
athlete_state=planner.get_recovery_profile()
planner_source_path=inspect.getsourcefile(TrainingPlanBuilder) or inspect.getfile(TrainingPlanBuilder)
selector_source_path=inspect.getsourcefile(TrainingPlanBuilder.select_workout)
planner_sources=Path(planner_source_path).read_bytes()+Path(selector_source_path).read_bytes()
planner_version=hashlib.sha256(planner_sources).hexdigest()

plan_signature=repr((planner_version,today.isoformat(),goal,sport,goal_date,training_goal.get("event_distance_km"),training_goal.get("event_climb_m"),training_goal.get("event_type"),planning_settings.get("ftp"),planning_settings.get("athlete_level"),planning_settings.get("training_progression"),sessions_per_week,completed_session_dates,completed_activity_signature,sorted((day,data.get("hours"),data.get("available")) for day,data in weekly_availability.items() if isinstance(data,dict)),repr(athlete_state)))


def threshold_test_workout():
    test_subtype = "6_min_run" if sport == "Running" else "ftp_test"
    return next(
        (
            workout
            for workout in workouts
            if workout.get("subtype") == test_subtype
        ),
        None,
    )


def replace_next_threshold_test(plan):
    if test_done or test_answer != "No":
        return False
    test_workout=threshold_test_workout()
    if not test_workout:
        return False
    if any(
        (item.get("workout") or {}).get("id") == test_workout.get("id")
        for item in plan
    ):
        return False
    for item in plan:
        if (
            item.get("category") == "VO2max"
            and str(item.get("date", "")) >= today.isoformat()
        ):
            item["category"]="Testing"
            item["target_tss"]=test_workout.get("target_tss",0)
            item["actual_tss"]=test_workout.get("target_tss",0)
            item["workout"]=test_workout
            item["rest"]=False
            return True
    return False

if "training_plan_horizon" not in st.session_state:
    st.session_state.training_plan_horizon=load_training_plan(username) or []

goal_day=pd.to_datetime(goal_date,errors="coerce").date() if goal_date else None
stored_plan=st.session_state.training_plan_horizon
stored_end=pd.to_datetime(stored_plan[-1].get("date"),errors="coerce").date() if stored_plan else None
plan_needs_update=not stored_plan or st.session_state.get("training_plan_signature")!=plan_signature or (goal_day is not None and (stored_end is None or stored_end<goal_day))

if plan_needs_update:
    settings=planning_settings
    st.session_state.training_plan_horizon=planner.build_long_term_plan(baseline_tss=weekly_tss,progression=float(settings.get("training_progression",8) or 8),start_date=timeline_start,goal_date=goal_date,sessions_per_week=sessions_per_week,completed_session_dates=completed_session_dates)
    replace_next_threshold_test(st.session_state.training_plan_horizon)
    save_training_plan(username,st.session_state.training_plan_horizon)
    st.session_state.training_plan_signature=plan_signature

training_plan=st.session_state.training_plan_horizon

if replace_next_threshold_test(training_plan):
    save_training_plan(username,training_plan)

if not training_plan:
    st.info("Set weekly availability to create your training plan.")
    st.stop()

if goal_day:
    for plan in training_plan:
        if str(plan.get("date")) == goal_day.isoformat():
            plan["race_day"] = True

display_plan=list(training_plan)

if activities is not None and not activities.empty and "date" in activities.columns:
    completed_frame=activities.copy()
    completed_frame["date"]=pd.to_datetime(completed_frame["date"],errors="coerce").dt.date
    completed_frame=completed_frame[(completed_frame["date"]>=timeline_start)&(completed_frame["date"]<=today)]
    plan_by_date={str(item.get("date")):item for item in display_plan}
    for current_date,day_activities in completed_frame.groupby("date"):
        actual_tss=pd.to_numeric(day_activities["stress"] if "stress" in day_activities.columns else 0,errors="coerce")
        if not isinstance(actual_tss,pd.Series):
            actual_tss=pd.Series(0.0,index=day_activities.index)
        actual_tss=actual_tss.fillna(0).sum()
        moving_time=day_activities["moving_time"] if "moving_time" in day_activities.columns else pd.Series(0,index=day_activities.index)
        completed_minutes=pd.to_numeric(moving_time,errors="coerce").fillna(0).sum()/60
        activity_type=clean_activity_type(day_activities.iloc[0].get("type","Completed activity"))
        completed_item={"date":current_date.isoformat(),"day":current_date.strftime("%A"),"category":activity_type,"target_tss":float(actual_tss),"actual_tss":float(actual_tss),"duration_minutes":float(completed_minutes),"workout":None,"completed":True,"rest":False,"week_number":plan_by_date.get(current_date.isoformat(),{}).get("week_number",1),"week_target_tss":plan_by_date.get(current_date.isoformat(),{}).get("week_target_tss",0)}
        plan_by_date[current_date.isoformat()]=completed_item
    display_plan=list(plan_by_date.values())
    display_plan.sort(key=lambda item:item.get("date",""))

# ============================================================
# BOX 1 — TRAINING GOAL + TRAINING DAYS
# ============================================================
with st.container(border=True):
    goal_col,training_days_col=st.columns([1,1], vertical_alignment="center")

    with goal_col:
        st.markdown(
            f'<div style="font-size:16px;font-weight:700;color:#18181b;line-height:1.2;">Training Goal <span style="font-size:10px;font-weight:400;color:#71717a;margin-left:6px;">{goal_label} · {sport}</span></div>',
            unsafe_allow_html=True
        )
    with training_days_col:
        header_col,selector_col=st.columns([1,1.35],vertical_alignment="center")
        with header_col:
            st.markdown('<div style="font-size:16px;font-weight:700;color:#18181b;line-height:1.2;">Training Days / Week</div>',unsafe_allow_html=True)
        with selector_col:
            selected_sessions=st.segmented_control("Training Days / Week",options=session_count_options,selection_mode="single",default=sessions_per_week,key="sessions_per_week_select",label_visibility="collapsed")
            sessions_per_week=selected_sessions or default_sessions
        if sessions_per_week!=stored_sessions_per_week:
            save_user_settings(username,sessions_per_week=sessions_per_week)
            planning_settings["sessions_per_week"]=sessions_per_week

    st.markdown("</div>",unsafe_allow_html=True)

# ============================================================
# BOX 2 — TRAINING PLAN + THIS WEEK
# ============================================================
with st.container(border=True):

    st.markdown('<div style="font-size:13px;font-weight:700;color:#17212b;margin-bottom:8px;">This week</div>',unsafe_allow_html=True)

    timeline_dates=[timeline_start+timedelta(days=offset) for offset in range(7)]
    plans_by_date={str(plan.get("date")):plan for plan in training_plan}
    activity_by_date={}
    activity_type_by_date={}

    if activities is not None and not activities.empty and "date" in activities.columns:
        activity_frame=activities.copy()
        activity_frame["date"]=pd.to_datetime(activity_frame["date"],errors="coerce").dt.date
        if "stress" in activity_frame.columns:
            activity_frame["stress"]=pd.to_numeric(activity_frame["stress"],errors="coerce").fillna(0)
            activity_by_date=activity_frame.groupby("date")["stress"].sum().to_dict()
        if "type" in activity_frame.columns:
            activity_type_by_date=activity_frame.assign(type=activity_frame["type"].map(clean_activity_type)).groupby("date")["type"].first().to_dict()

    timeline_cols=st.columns(7,gap="small")

    for column,current_date in zip(timeline_cols,timeline_dates):
        with column:
            date_label=current_date.strftime("%a").upper()
            short_date=current_date.strftime("%d %b")
            activity_tss=float(activity_by_date.get(current_date,0) or 0)
            has_activity=current_date<=today and activity_tss>0
            is_past=current_date<today
            is_today=current_date==today
            plan=plans_by_date.get(current_date.isoformat())
            if is_past or has_activity:
                activity_name=activity_type_by_date.get(current_date,"Activity") if activity_tss else "Rest"
                detail=f"{activity_tss:.0f} TSS" if activity_tss else "No activity"
                color=RECOVERY_COLOR if activity_tss<=0 else "#6f9bb2" if activity_tss<50 else "#d39a45" if activity_tss<100 else "#b85c5c"
            elif plan and plan.get("race_day"):
                activity_name="Race Day"
                detail="Event day"
                color="#b85c5c"
            elif not plan or plan.get("rest"):
                activity_name="Rest"
                detail="Recovery"
                color=RECOVERY_COLOR
            else:
                activity_name=plan.get("category","Training")
                workout=plan.get("workout") or {}
                duration=get_workout_duration(workout)
                hours,minutes=divmod(duration,60)
                intensity=get_workout_if(workout)
                detail=f"{hours}h {minutes:02d}min · IF {intensity:.2f}" if hours else f"{minutes}min · IF {intensity:.2f}"
                color=CATEGORY_COLORS.get(activity_name,"#557b91")
            if not is_past and plan and plan.get("workout"):
                render_clickable_workout_card(plan["workout"],current_date.strftime("%A"),short_date,activity_name,detail,color,f"timeline_{current_date.isoformat()}")
            else:
                render_static_day_card(current_date.strftime("%A"),f"{short_date}{' · TODAY' if is_today else ''}",activity_name,detail,color)

    st.markdown('</div>',unsafe_allow_html=True)

# ============================================================
# BOX 3 — WEEKLY TRAINING LOAD / INTENSITY PROGRESS
# ============================================================
with st.container(border=True):
    st.markdown('<div style="font-size:13px;font-weight:700;color:#17212b;margin-bottom:8px;">Weekly Training Load / Intensity Progress</div>',unsafe_allow_html=True)

    week_plan_items=[plan for plan in training_plan if timeline_start.isoformat()<=str(plan.get("date",""))<=(timeline_start+timedelta(days=6)).isoformat()]
    zone_target=empty_zones()
    zone_future=empty_zones()
    zone_completed=get_completed_week_zones(activities,timeline_start,today,float(planning_settings.get("ftp",0) or 0))
    week_budget=next((plan.get("intensity_budget") for plan in week_plan_items if isinstance(plan.get("intensity_budget"),dict)),None)

    if week_budget:
        budget_zones=week_budget.get("zone_minutes",{})
        for zone in zone_target:
            zone_target[zone]=float(budget_zones.get(zone,0) or 0)

    for plan in week_plan_items:
        plan_date=str(plan.get("date"))
        has_completed_activity=plan_date==today.isoformat() and activity_by_date.get(today,0)>0
        if plan_date>=today.isoformat() and not has_completed_activity and not plan.get("rest"):
            planned_zones=get_zone_minutes_from_steps(plan.get("workout"))
            for zone in zone_future:
                zone_future[zone]+=planned_zones[zone]

    if not any(zone_target.values()):
        for plan in week_plan_items:
            if plan.get("rest"):
                continue
            planned_zones=get_zone_minutes_from_steps(plan.get("workout"))
            for zone in zone_target:
                zone_target[zone]+=planned_zones[zone]

    completed_minutes=sum(zone_completed.values())
    forecast_minutes=sum(zone_future.values())
    tss_target=max((float(plan.get("week_target_tss",0) or 0) for plan in week_plan_items),default=float(weekly_tss or 0))
    tss_progress=min(100,(completed_week_tss/tss_target)*100) if tss_target else 0

    display_zones=["Endurance","Tempo","Threshold","VO2max"]
    circle_cols=st.columns(5,gap="small")

    for column,zone in zip(circle_cols[:4],display_zones):
        with column:
            target=zone_target.get(zone,0)
            completed=zone_completed.get(zone,0)
            percentage=(completed/target)*100 if target else 0
            render_small_progress_circle(zone,percentage,f"{format_total_time(completed)} / {format_total_time(target)}",CATEGORY_COLORS.get(zone,zone_color(zone)))

    with circle_cols[4]:
        render_small_progress_circle("TSS",tss_progress,f"{completed_week_tss:.0f} / {tss_target:.0f}","#4f7f92")

    st.markdown(f'<div style="text-align:center;margin-top:5px;font-size:9px;color:#6b7785;"><strong style="color:#526170;">Total training</strong> · {format_total_time(completed_minutes)} / {format_total_time(completed_minutes+forecast_minutes)}</div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

# ============================================================
# BOX 4 — FULL PLAN UNTIL GOAL
# ============================================================
with st.container(border=True):
    st.markdown('<div style="font-size:13px;font-weight:700;color:#17212b;margin-bottom:8px;">Full plan until goal</div>',unsafe_allow_html=True)

    weeks={}
    for plan in display_plan:
        weeks.setdefault(plan["week_number"],[]).append(plan)

    for week_number,week_plans in weeks.items():
        tss_target=float(week_plans[0].get("week_target_tss",0) or 0)
        week_budget=next((plan.get("intensity_budget") for plan in week_plans if isinstance(plan.get("intensity_budget"),dict)),None)
        zone_target=empty_zones()
        if week_budget:
            budget_zones=week_budget.get("zone_minutes",{})
            for zone in zone_target:
                zone_target[zone]=float(budget_zones.get(zone,0) or 0)
        if not any(zone_target.values()):
            for plan in week_plans:
                if plan.get("rest"):
                    continue
                planned_zones=get_zone_minutes_from_steps(plan.get("workout"))
                for zone in zone_target:
                    zone_target[zone]+=planned_zones[zone]
        if not any(zone_target.values()):
            shares=[0.30,0.30,0.25,0.15]
            for zone,share in zip(list(zone_target.keys()),shares):
                zone_target[zone]=tss_target*share
        week_title=f"Week {week_number}"
        if len(week_plans)<7:
            week_title+=" · partial week"
        if week_plans[0].get("deload"):
            week_title+=" · deload"
        st.markdown(f'<div style="font-size:10px;font-weight:700;color:#526170;margin:8px 0 5px;">{week_title}</div>',unsafe_allow_html=True)
        summary_col,plan_col=st.columns([2,7],gap="small")
        with summary_col:
            if goal_day and any(str(plan.get("date")) == goal_day.isoformat() for plan in week_plans):
                st.markdown('<div style="font-size:11px;font-weight:800;color:#b85c5c;margin:0 0 6px;text-align:center;">Race Week</div>',unsafe_allow_html=True)
            render_week_summary(week_plans,zone_target,tss_target,activities)
        with plan_col:
            render_full_week(week_plans)

    st.markdown('</div>',unsafe_allow_html=True)
