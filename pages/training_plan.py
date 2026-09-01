import os
import hashlib
import inspect
from datetime import date,timedelta
from pathlib import Path
import pandas as pd
import streamlit as st
from helpers.style import apply_global_style
from helpers.workout_builder import plot_workout_summary
from helpers.metrics import TRAINING_ZONES,get_training_zone
from helpers.training_plan_functions import DAYS,CATEGORY_COLORS,load_workouts,workout_to_plot_steps,generate_workout_fit,calculate_target_weekly_tss,calculate_previous_week_tss
from helpers.dashboard_css import inject_card_css
from Strava.strava_user import get_training_goal,get_user_settings,save_user_settings
from helpers.availability import load_availability
from helpers.database import load_training_plan,save_training_plan
from helpers.user_cache import get_user_cache_paths
from training_planner import periodization
from training_planner.periodization import calculate_athlete_state,calculate_event_demand,generate_long_term_plan
from helpers.dashboard_cards import render_metric_circle

apply_global_style()
inject_card_css()

ROOT=Path(__file__).resolve().parent.parent
LIBRARY_PATH=ROOT/"workouts"
ZONE_KEYS=tuple(TRAINING_ZONES.keys())
ZONE_COLORS=["#8fa8b5","#6f9bb2","#d39a45","#b85c5c","#8c5c8c","#76558c","#5d4b82"]

def zone_color(zone):
    try:return ZONE_COLORS[ZONE_KEYS.index(zone)%len(ZONE_COLORS)]
    except:return "#64748B"

def empty_zones():
    return {zone:0.0 for zone in ZONE_KEYS}

def get_zone_minutes_from_steps(workout):
    zones=empty_zones()
    for step in (workout or {}).get("steps",[]):
        intensity=float(step.get("intensity",0) or 0)/100
        minutes=float(step.get("duration_seconds",0) or 0)/60
        zone=get_training_zone(intensity)
        if zone in zones:zones[zone]+=minutes
    return zones

def get_completed_week_zones(activities,week_start,today,ftp):
    zones=empty_zones()
    if activities is None or activities.empty or "date" not in activities:return zones
    frame=activities.copy()
    frame["date"]=pd.to_datetime(frame["date"],errors="coerce").dt.date
    frame=frame[(frame["date"]>=week_start)&(frame["date"]<today)]
    for _,activity in frame.iterrows():
        activity_type=str(activity.get("type",""))
        power=activity.get("weighted_average_watts")
        if power is None or pd.isna(power):power=activity.get("average_watts")
        has_power="ride" in activity_type.lower() and ftp>0 and power is not None and not pd.isna(power)
        if has_power:
            zone=get_training_zone(float(power)/ftp)
            if zone in zones:zones[zone]+=float(activity.get("moving_time",0) or 0)/60
        else:
            for index,zone in enumerate(ZONE_KEYS,1):
                column=f"time_z{index}_hr"
                value=activity.get(column,0)
                if value is not None and not pd.isna(value):zones[zone]+=float(value)/60
    return zones

@st.cache_data

def get_library(library_version=1):
    return load_workouts(LIBRARY_PATH)

def get_workout_duration(workout):
    steps=(workout or {}).get("steps",[])
    if not steps:return 0
    return round(sum(float(step.get("duration_seconds",0) or 0) for step in steps)/60)

def get_workout_zone_minutes(workout):
    zones={"Zone 1":0.0,"Zone 2":0.0,"Zone 3":0.0,"Zone 4":0.0,"Zone 5+":0.0}
    zone_map={"Recovery":"Zone 1","Endurance":"Zone 2","Tempo":"Zone 3","Threshold":"Zone 4","VO2max":"Zone 5+","Anaerobic":"Zone 5+"}
    for step in (workout or {}).get("steps",[]):
        intensity=float(step.get("intensity",0) or 0)/100
        minutes=float(step.get("duration_seconds",0) or 0)/60
        zone=zone_map.get(get_training_zone(intensity),"Zone 1")
        zones[zone]+=minutes
    return zones

# Convert minutes into a readable duration
def format_total_time(minutes):
    minutes=int(round(minutes))
    hours,mins=divmod(minutes,60)
    return f"{hours}h {mins:02d}min" if hours else f"{mins}min"

# Render the small progress circles
def render_small_progress_circle(title,percentage,subtitle,color):
    percentage=max(0,min(float(percentage),100))
    st.markdown(f"""
    <div style="text-align:center;">
        <div style="
            width:82px;
            height:82px;
            border-radius:50%;
            background:conic-gradient({color} {percentage * 3.6}deg,#e6ebef 0deg);
            display:flex;
            align-items:center;
            justify-content:center;
            margin:auto;
        ">
            <div style="
                width:66px;
                height:66px;
                border-radius:50%;
                background:white;
                display:flex;
                align-items:center;
                justify-content:center;
                font-size:18px;
                font-weight:800;
                color:#17212b;
            ">
                {percentage:.0f}%
            </div>
        </div>
        <div style="
            margin-top:8px;
            font-size:10px;
            font-weight:700;
            color:#526170;
            text-transform:uppercase;
            letter-spacing:.06em;
        ">
            {title}
        </div>
        <div style="
            margin-top:2px;
            font-size:9px;
            color:#7a8792;
        ">
            {subtitle}
        </div>
    </div>
    """,unsafe_allow_html=True)


def format_minutes(minutes):
    total_minutes=max(0,round(float(minutes or 0)))
    hours,remaining_minutes=divmod(total_minutes,60)
    return f"{hours}h {remaining_minutes:02d}min" if hours else f"{remaining_minutes}min"

def clean_activity_type(value):
    return str(value or "Activity").replace("root='","").replace("'","")

def render_preview(workout,key,height=115):
    steps=workout_to_plot_steps(workout)
    if not steps:return
    workout_sport=str(workout.get("sport","Cycling") or "Cycling")
    fig=plot_workout_summary(steps,sport=workout_sport)
    fig.update_layout(height=height,margin=dict(l=5,r=5,t=3,b=3),xaxis=dict(showticklabels=False,showgrid=False,title=None),yaxis=dict(showticklabels=False,showgrid=False,title=None))
    st.plotly_chart(fig,width="stretch",config={"displayModeBar":False},key=key)

@st.dialog("Workout details")

def workout_details_dialog(workout):
    category=workout.get("_category",workout.get("category","Workout"))
    duration=get_workout_duration(workout)
    target_tss=float(workout.get("target_tss",workout.get("estimated_tss",0)) or 0)
    target_if=float(workout.get("target_if",0) or 0)
    st.subheader(workout.get("name","Workout"))
    st.caption(f"{category} · {format_minutes(duration)} · IF {target_if:.2f} · {target_tss:.0f} TSS")
    st.markdown("**Workout intervals**")
    for step in workout.get("steps",[]):
        name=step.get("name","Interval")
        seconds=float(step.get("duration_seconds",0) or 0)
        intensity=float(step.get("intensity",0) or 0)
        repeat=int(step.get("repeat",1) or 1)
        minutes,secs=divmod(round(seconds),60)
        repeat_text=f" × {repeat}" if repeat>1 else ""
        st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;padding:7px 10px;margin-bottom:3px;background:#f8fafc;border:1px solid #e5e7eb;border-radius:5px;font-size:11px;color:#17212b;"><span>{name}{repeat_text}</span><span style="font-weight:700;color:#17212b;">{minutes}:{secs:02d} · IF {intensity/100:.2f}</span></div>',unsafe_allow_html=True)
    render_preview(workout,f"details_preview_{workout.get('id',workout.get('_file','workout'))}",height=260)
    try:
        fit_bytes,filename=generate_workout_fit(workout)
        st.download_button("Download FIT",data=fit_bytes,file_name=filename,mime="application/octet-stream",use_container_width=True,key=f"details_fit_{workout.get('id',workout.get('_file','workout'))}")
    except Exception:
        st.warning("FIT file unavailable for this workout.")

@st.dialog("Choose workout")

def edit_workout_dialog(day,plan,workouts, sport):
    category=plan.get("category","Endurance")
    target_tss=float(plan.get("target_tss",0) or 0)
    color=CATEGORY_COLORS.get(category,"#64748B")
    
    options=[workout for workout in workouts if workout.get("_category")==category and workout.get("sport","Cycling")==sport]
    if not options:
        st.warning(f"No {category} workouts are available.")
        return
    options=sorted(options,key=lambda workout:abs(float(workout.get("target_tss",0) or 0)-target_tss))
    st.markdown(f'<div style="font-size:13px;color:#64748B;margin-bottom:14px;">{day} · {category} · planned target {target_tss:.0f} TSS</div>',unsafe_allow_html=True)
    for index,workout in enumerate(options):
        actual_tss=float(workout.get("target_tss",0) or 0)
        duration=get_workout_duration
        difference=actual_tss-target_tss
        selected=current and workout.get("_file")==current.get("_file") if (current:=plan.get("workout")) else False
        border=color if selected else "rgba(148,163,184,.18)"
        background=f"{color}12" if selected else "rgba(148,163,184,.04)"
        st.markdown(f'<div style="border:1px solid {border};border-radius:12px;padding:10px 12px 6px;margin-top:8px;background:{background};"><div style="font-size:13px;font-weight:700;">{workout.get("name","Workout")}</div><div style="font-size:11px;color:#64748B;margin-top:3px;">{duration} min · {actual_tss:.0f} TSS · {difference:+.0f} vs target</div></div>',unsafe_allow_html=True)
        render_preview(workout,f"dialog_preview_{day}_{index}",height=85)
        selected_label="Selected" if selected else "Select"
        if st.button(selected_label,key=f"select_workout_{day}_{index}",use_container_width=True,disabled=selected):
            plan["workout"]=workout
            plan_date=plan.get("date")
            for stored_index,stored_plan in enumerate(st.session_state.training_plan_horizon):
                if stored_plan.get("date")==plan_date:
                    st.session_state.training_plan_horizon[stored_index]=plan
                    break
            save_training_plan(username,st.session_state.training_plan_horizon)
            st.rerun()

username=st.session_state.get("username")
if not username:
    st.error("Please log in first.")
    st.stop()

training_goal=get_training_goal(username)

if not isinstance(training_goal,dict) or not training_goal.get("name"):
    st.markdown('<div class="dashboard-title">Training Plan</div>',unsafe_allow_html=True)
    st.info("Select a training goal before creating your training plan.")
    if st.button("Select training goal",type="primary"):
        st.session_state["settings_section"]="Training Goal"
        st.switch_page("pages/settings.py")
    st.stop()

goal=training_goal["name"]

# Running goals use the same planner structure as cycling,
# but the workout library and training distribution are running-specific.
running_goals={"5k","10k","half_marathon","marathon"}
is_running_plan=goal in running_goals
sport="Running" if is_running_plan else "Cycling"

goal_labels={
    "general_fitness":"General Fitness",
    "gran_fondo":"Gran Fondo",
    "criterium":"Criterium",
    "5k":"5K",
    "10k":"10K",
    "half_marathon":"Half Marathon",
    "marathon":"Marathon",
}

goal_label=goal_labels.get(goal,str(goal).replace("_"," ").title())

weekly_availability=load_availability(username).get("weekly",{})
has_available_day=any(float(day.get("hours",0) or 0)>0 or (day.get("available") and day.get("start") and day.get("end")) for day in weekly_availability.values() if isinstance(day,dict))
if not has_available_day:
    st.markdown('<div class="dashboard-title">Training Plan</div>',unsafe_allow_html=True)
    st.info("Set your weekly availability before creating your training plan.")
    if st.button("Select weekly availability",type="primary"):st.switch_page("pages/settings_availability.py")
    st.stop()

availability_summary=" · ".join(f"{day[:3]} {float(data.get('hours',0) or 0):g}h" for day,data in weekly_availability.items() if isinstance(data,dict) and float(data.get("hours",0) or 0)>0)


col1,col2=st.columns(2,gap="large")

with col1:
    st.caption(f"Weekly availability: {availability_summary}")

with col2:
    planning_settings=get_user_settings(username)
    session_count_options=[2,3,4,5,6]
    stored_sessions_per_week=planning_settings.get("sessions_per_week")
    default_sessions=stored_sessions_per_week if stored_sessions_per_week in session_count_options else 4
    col1,col2=st.columns([1,2],vertical_alignment="center")
    st.markdown("""
    <div style="
        background:white;
        border:1px solid #e5e7eb;
        border-radius:10px;
        padding:12px 16px;
        margin:8px 0 16px;
    ">
        <div style="
            display:flex;
            align-items:center;
            justify-content:space-between;
        ">
            <div>
                <div style="font-size:13px;font-weight:700;color:#17212b;">
                    Training days per week
                </div>
                <div style="font-size:11px;color:#6b7785;margin-top:2px;">
                    Choose how many days you want to train
                </div>
            </div>
        </div>
    </div>
    """,unsafe_allow_html=True)

    sessions_per_week=st.segmented_control(
        "Training days per week",
        options=session_count_options,
        selection_mode="single",
        default=default_sessions,
        key="sessions_per_week_select",
        label_visibility="collapsed",
    )

    sessions_per_week=sessions_per_week or default_sessions

    if sessions_per_week!=stored_sessions_per_week:
        save_user_settings(username,sessions_per_week=sessions_per_week)
        planning_settings["sessions_per_week"]=sessions_per_week

header_col,edit_col=st.columns([8,1],vertical_alignment="center")
with header_col:st.markdown(f'<div class="dashboard-title">Training Plan <span style="font-size:18px;color:#94A3B8;font-weight:400;">for {goal_label} for {sport}</span></div>',unsafe_allow_html=True)
with edit_col:
    if st.button("Edit",key="edit_training_goal"):
        st.session_state["settings_section"]="Training Goal"
        st.switch_page("pages/settings.py")
workouts=get_library(library_version=2)
goal_date=training_goal.get("goal_date")
weekly_tss=calculate_target_weekly_tss(username)
previous_week_tss=calculate_previous_week_tss(username)


if previous_week_tss>0:
    change=((weekly_tss/previous_week_tss)-1)*100
    st.caption(f"Last week: {previous_week_tss:.0f} TSS · This week: {weekly_tss:.0f} TSS · {change:+.0f}%")

else:st.caption("Build your week and choose the workout that fits you best.")

activity_file,_=get_user_cache_paths(username)
activities=pd.read_csv(activity_file) if os.path.exists(activity_file) else None
today=date.today()

timeline_start=today-timedelta(days=today.weekday())
completed_zone_minutes=get_completed_week_zones(activities,timeline_start,today,float(planning_settings.get("ftp",0) or 0))
completed_week_tss=0.0

if activities is not None and not activities.empty and "date" in activities:
    activity_dates=pd.to_datetime(activities["date"],errors="coerce").dt.date
    current_week_rows=activities[(activity_dates>=timeline_start)&(activity_dates<=today)]
    if "stress" in current_week_rows:completed_week_tss=pd.to_numeric(current_week_rows["stress"],errors="coerce").fillna(0).sum()

athlete_state=calculate_athlete_state(activities,ftp=float(planning_settings.get("ftp",0) or 0))

planner_source_path=inspect.getsourcefile(periodization) or inspect.getfile(periodization)

planner_version=hashlib.sha256(Path(planner_source_path).read_bytes()).hexdigest()
plan_signature=repr((planner_version,today.isoformat(),goal,goal_date,training_goal.get("event_distance_km"),training_goal.get("event_climb_m"),training_goal.get("event_type"),planning_settings.get("ftp"),planning_settings.get("athlete_level"),planning_settings.get("training_progression"),sessions_per_week,sorted((day,data.get("hours"),data.get("available")) for day,data in weekly_availability.items() if isinstance(data,dict)),repr(athlete_state)))

if "training_plan_horizon" not in st.session_state:st.session_state.training_plan_horizon=load_training_plan(username) or []

goal_day=pd.to_datetime(goal_date,errors="coerce").date() if goal_date else None
stored_plan=st.session_state.training_plan_horizon
stored_end=pd.to_datetime(stored_plan[-1].get("date"),errors="coerce").date() if stored_plan else None
plan_needs_update=not stored_plan or st.session_state.get("training_plan_signature")!=plan_signature or (goal_day is not None and (stored_end is None or stored_end<goal_day))

if plan_needs_update:
    settings=planning_settings
    st.session_state.training_plan_horizon=generate_long_term_plan(goal=goal,goal_date=goal_date,availability=weekly_availability,workouts=workouts,baseline_tss=weekly_tss,progression=float(settings.get("training_progression",8) or 8),start_date=timeline_start,activities=activities,athlete_level=settings.get("athlete_level"),completed_zone_minutes=completed_zone_minutes,completed_tss=completed_week_tss,sessions_per_week=sessions_per_week,event_demand=calculate_event_demand(training_goal.get("event_distance_km"),training_goal.get("event_climb_m"),training_goal.get("event_type"),settings.get("ftp")) if training_goal.get("event_distance_km") else None)
    save_training_plan(username,st.session_state.training_plan_horizon)
    st.session_state.training_plan_signature=plan_signature

training_plan=st.session_state.training_plan_horizon
if not training_plan:
    st.info("Set weekly availability to create your training plan.")
    st.stop()
display_plan=list(training_plan)

if activities is not None and not activities.empty and "date" in activities:
    completed_frame=activities.copy()
    completed_frame["date"]=pd.to_datetime(completed_frame["date"],errors="coerce").dt.date
    completed_frame=completed_frame[(completed_frame["date"]>=timeline_start)&(completed_frame["date"]<=today)]
    plan_by_date={str(item.get("date")):item for item in display_plan}
    for current_date,day_activities in completed_frame.groupby("date"):
        actual_tss=pd.to_numeric(day_activities["stress"] if "stress" in day_activities else 0,errors="coerce")
        if not isinstance(actual_tss,pd.Series):actual_tss=pd.Series(0.0,index=day_activities.index)
        actual_tss=actual_tss.fillna(0).sum()
        activity_type=clean_activity_type(day_activities.iloc[0].get("type","Completed activity"))
        completed_item={"date":current_date.isoformat(),"day":current_date.strftime("%A"),"category":activity_type,"target_tss":float(actual_tss),"actual_tss":float(actual_tss),"workout":None,"completed":True,"rest":False,"week_number":1,"week_target_tss":plan_by_date.get(current_date.isoformat(),training_plan[0]).get("week_target_tss",0)}
        if current_date.isoformat() in plan_by_date:plan_by_date[current_date.isoformat()]=completed_item
        else:display_plan.append(completed_item)
    display_plan=list(plan_by_date.values())
    display_plan.sort(key=lambda item:item.get("date",""))

st.subheader("This week")
timeline_dates=[timeline_start+timedelta(days=offset) for offset in range(7)]
plans_by_date={plan.get("date"):plan for plan in training_plan}
activity_by_date={}
activity_type_by_date={}

if activities is not None and not activities.empty and "date" in activities:
    activity_frame=activities.copy()
    activity_frame["date"]=pd.to_datetime(activity_frame["date"],errors="coerce").dt.date
    if "stress" in activity_frame:
        activity_frame["stress"]=pd.to_numeric(activity_frame["stress"],errors="coerce").fillna(0)
        activity_by_date=activity_frame.groupby("date")["stress"].sum().to_dict()
        if "type" in activity_frame:activity_type_by_date=activity_frame.assign(type=activity_frame["type"].map(clean_activity_type)).groupby("date")["type"].first().to_dict()

timeline_cols=st.columns(7,gap="small")

for column,current_date in zip(timeline_cols,timeline_dates):
    with column:
        date_label=current_date.strftime("%a").upper()
        short_date=current_date.strftime("%d %b")
        activity_tss=float(activity_by_date.get(current_date,0) or 0)
        has_activity=current_date<=today and activity_tss>0
        is_past=current_date<today
        plan=plans_by_date.get(current_date.isoformat())
        if is_past or has_activity:
            activity_name=activity_type_by_date.get(current_date,"Activity") if activity_tss else "Rest"
            detail=f"{activity_tss:.0f} TSS" if activity_tss else "No activity"
            color="#98a6b3" if activity_tss<=0 else "#6f9bb2" if activity_tss<50 else "#d39a45" if activity_tss<100 else "#b85c5c"
        elif not plan or plan.get("rest"):
            activity_name="Rest"
            detail="Recovery"
            color="#98a6b3"
        else:
            activity_name=plan.get("category","Training")
            workout=plan.get("workout") or {}
            duration=get_workout_duration(workout)
            hours,minutes=divmod(duration,60)
            intensity=float(workout.get("target_if",0) or 0)
            detail=f"{hours}h {minutes:02d}min · IF {intensity:.2f}" if hours else f"{minutes}min · IF {intensity:.2f}"
            color=CATEGORY_COLORS.get(activity_name,"#557b91")
        background=f"{color}18" if not is_past else f"{color}12"
        st.markdown(f'<div style="background:{background};border:1px solid {color}55;border-top:3px solid {color};border-radius:7px;padding:9px 7px;min-height:92px;text-align:center;"><div style="font-size:10px;color:#7a8792;font-weight:700;">{date_label}{" · TODAY" if current_date==today else ""}</div><div style="font-size:11px;color:#7a8792;margin-top:2px;">{short_date}</div><div style="font-size:12px;color:#17212b;font-weight:700;margin-top:13px;">{activity_name}</div><div style="font-size:10px;color:#6b7785;margin-top:4px;">{detail}</div></div>',unsafe_allow_html=True)
        if not is_past and plan and plan.get("workout"):
            if st.button("View workout",key=f"timeline_details_{current_date}",use_container_width=True):workout_details_dialog(plan["workout"])
st.subheader("Weekly Training Load / Intensity Progress")

# Get this week's planned sessions
week_plan_items=[plan for plan in training_plan if timeline_start.isoformat()<=str(plan.get("date",""))<=(timeline_start+timedelta(days=6)).isoformat()]
zone_targets=empty_zones()
zone_forecast=empty_zones()
zone_completed=empty_zones()

# Use the planner's intensity budget when available
week_budget=next((plan.get("intensity_budget") for plan in week_plan_items if isinstance(plan.get("intensity_budget"),dict)),None)
if week_budget:
    budget_zones=week_budget.get("zone_minutes",{})
    for zone in ZONE_KEYS:
        zone_targets[zone]=float(budget_zones.get(zone,0) or 0)

# Add future planned workout time to the forecast
for plan in week_plan_items:
    planned_zones=get_zone_minutes_from_steps(plan.get("workout"))
    if str(plan.get("date"))>today.isoformat() and not plan.get("rest"):
        for zone in ZONE_KEYS:
            zone_forecast[zone]+=planned_zones[zone]

# If the planner did not provide zone targets, use the actual planned workouts
if not any(zone_targets.values()):
    planned_zone_totals=empty_zones()
    for plan in week_plan_items:
        if plan.get("rest"):
            continue
        planned_zones=get_zone_minutes_from_steps(plan.get("workout"))
        for zone in ZONE_KEYS:
            planned_zone_totals[zone]+=planned_zones[zone]
    if any(planned_zone_totals.values()):
        zone_targets=planned_zone_totals.copy()

# Add completed training time
if activities is not None and not activities.empty and "date" in activities:
    zone_completed=get_completed_week_zones(activities,timeline_start,today,float(planning_settings.get("ftp",0) or 0))

# Calculate total training time
completed_minutes=sum(zone_completed.values())
forecast_minutes=sum(zone_forecast.values())
total_minutes=completed_minutes+forecast_minutes

# Calculate TSS progress
tss_target=max((float(plan.get("week_target_tss",0) or 0) for plan in week_plan_items),default=float(weekly_tss or 0))
future_planned_tss=sum(float((plan.get("workout") or {}).get("target_tss",0) or 0) for plan in week_plan_items if str(plan.get("date"))>today.isoformat() and plan.get("workout"))
tss_current=completed_week_tss+future_planned_tss
tss_progress=min(100,(tss_current/tss_target)*100) if tss_target else 0


# Only show the key intensity zones
display_zones=["Endurance","Tempo","Threshold","VO2max"]

circle_cols=st.columns(5,gap="small")

for column,zone in zip(circle_cols[:4],display_zones):
    with column:
        target=zone_targets.get(zone,0)
        completed=zone_completed.get(zone,0)
        planned=zone_forecast.get(zone,0)
        current=completed+planned
        percentage=(current/target)*100 if target else 0
        subtitle=f"{format_total_time(current)} / {format_total_time(target)}"
        render_small_progress_circle(zone,percentage,subtitle,zone_color(zone))
with circle_cols[4]:
    render_small_progress_circle("TSS",tss_progress*100,f"{completed_week_tss:.0f} / {tss_target:.0f}", "#4f7f92")


# Total training time
st.markdown(
    f'<div style="text-align:center;margin-top:8px;font-size:11px;color:#6b7785;">'
    f'<strong style="color:#526170;">Total training</strong> · {format_total_time(total_minutes)}'
    f'</div>',
    unsafe_allow_html=True,
)

st.markdown("<div style='height:12px'></div>",unsafe_allow_html=True)

if training_plan:
    st.divider()
    st.subheader("Full plan until goal")
    weeks={}
    for plan in display_plan:weeks.setdefault(plan["week_number"],[]).append(plan)
    for week_number,week_plans in weeks.items():
        target_week_tss=float(week_plans[0].get("week_target_tss",0) or 0)
        week_budget=next((plan.get("intensity_budget") for plan in week_plans if isinstance(plan.get("intensity_budget"),dict)),None)
        weekly_zone_targets=empty_zones()
        if week_budget:
            budget_zones=week_budget.get("zone_minutes",{})
            for zone in ZONE_KEYS:weekly_zone_targets[zone]=float(budget_zones.get(zone,0) or 0)
        if not any(weekly_zone_targets.values()):
            for plan in week_plans:
                if plan.get("rest"):continue
                planned_zones=get_zone_minutes_from_steps(plan.get("workout"))
                for zone in ZONE_KEYS:weekly_zone_targets[zone]+=planned_zones[zone]
        if not any(weekly_zone_targets.values()):
            shares=[0.30,0.30,0.25,0.15]
            for zone,share in zip(ZONE_KEYS,shares):weekly_zone_targets[zone]=target_week_tss*share
        planned_workouts_tss=sum(float((plan.get("workout") or {}).get("target_tss",(plan.get("workout") or {}).get("estimated_tss",0)) or 0) for plan in week_plans if not plan.get("completed") and not plan.get("rest") and plan.get("workout"))
        week_dates={pd.to_datetime(plan.get("date")).date() for plan in week_plans}
        completed_week_tss=sum(float(activity_by_date.get(activity_date,0) or 0) for activity_date in week_dates if activity_date<=today)
        week_title=f"Week {week_number}"

        if len(week_plans)<7:week_title+=" · partial week"

        if week_plans[0].get("deload"):week_title+=" · deload"

        st.markdown(f'<div style="font-size:13px;font-weight:700;margin:14px 0 7px;">{week_title}</div>',unsafe_allow_html=True)
        summary_col,plan_col=st.columns([1,7],gap="small")

        with summary_col:
            st.markdown('<div style="display:grid;grid-template-columns:1fr 0.8fr 1fr;padding:5px 8px;border-bottom:1px solid #edf0f2;background:#f8fafb;"><span style="font-size:8px;font-weight:700;color:#687581;">ZONE</span><span style="font-size:8px;font-weight:700;color:#687581;text-align:right;">PLAN</span><span style="font-size:8px;font-weight:700;color:#687581;text-align:right;">WORKOUTS</span></div>',unsafe_allow_html=True)
            planned_workout_zone_minutes = {z: 0 for z in ["Zone 1","Zone 2","Zone 3","Zone 4","Zone 5+"]}
            for item in week_plans:
                if item.get("workout"):
                    zones = get_workout_zone_minutes(item["workout"])
                    for z in planned_workout_zone_minutes:
                        planned_workout_zone_minutes[z] += zones.get(z, 0)

            longterm_zone_minutes = {
                "Zone 1": weekly_zone_targets.get("Recovery", 0),
                "Zone 2": weekly_zone_targets.get("Endurance", 0),
                "Zone 3": weekly_zone_targets.get("Tempo", 0),
                "Zone 4": weekly_zone_targets.get("Threshold", 0),
                "Zone 5+": weekly_zone_targets.get("VO2max", 0) + weekly_zone_targets.get("Anaerobic", 0),
            }

            summary_rows = [("TSS", target_week_tss, planned_workouts_tss)]
            summary_rows += [(z, longterm_zone_minutes[z], planned_workout_zone_minutes[z]) for z in longterm_zone_minutes]

            for i, (label, longterm, weekly) in enumerate(summary_rows):
                border = "" if i == len(summary_rows)-1 else "border-bottom:1px solid #f0f2f4;"
                color = zone_color(label) if label != "TSS" else "#17212b"
                st.markdown(f'<div style="display:grid;grid-template-columns:0.8fr 1fr 1fr;padding:3px 8px;{border}"><span style="font-size:8px;color:#687581;">{label}</span><span style="font-size:9px;font-weight:700;color:{color};text-align:right;">{format_minutes(longterm) if label!="TSS" else f"{longterm:.0f}"}</span><span style="font-size:9px;font-weight:700;color:{color};text-align:right;">{format_minutes(weekly) if label!="TSS" else f"{weekly:.0f}"}</span></div>', unsafe_allow_html=True)
        with plan_col:
            plans_by_day={plan["day"]:plan for plan in week_plans}
            week_cols=st.columns(7,gap="small")
            for day,col in zip(DAYS,week_cols):
                with col:
                    plan=plans_by_day.get(day)
                    if not plan:
                        st.markdown('<div style="height:48px;"></div>',unsafe_allow_html=True)
                        continue
                    if plan.get("rest"):
                        category="Rest"
                        duration_text="Recovery"
                        color="#94A3B8"
                    else:
                        category=plan.get("category","Endurance")
                        duration=get_workout_duration(plan.get("workout"))
                        hours,minutes=divmod(duration,60)
                        duration_text=f"{hours}h {minutes:02d}min" if hours else f"{minutes}min"
                        color=CATEGORY_COLORS.get(category,"#64748B")
                    st.markdown(f'<div style="border-top:3px solid {color};background:{color}12;border-radius:7px;padding:7px 4px;height:64px;text-align:center;overflow:hidden;box-sizing:border-box;"><div style="font-size:9px;color:#64748B;">{day[:3]} · {plan["date"][5:]}</div><div style="font-size:10px;font-weight:700;color:{color};margin-top:6px;">{category}</div><div style="font-size:9px;color:#64748B;margin-top:3px;">{duration_text}</div></div>',unsafe_allow_html=True)
                    if plan.get("workout"):
                        if st.button("View", key=f"full_plan_details_{plan['date']}", use_container_width=True):
                            workout_details_dialog(plan["workout"])
                        zone_minutes = get_workout_zone_minutes(plan["workout"])
                        st.markdown(
                            f'<div style="font-size:8px;line-height:1.35;color:#94A3B8;margin-top:3px;">'
                            f'<div>Z1&nbsp;&nbsp;{zone_minutes["Zone 1"]:.0f} min</div>'
                            f'<div>Z2&nbsp;&nbsp;{zone_minutes["Zone 2"]:.0f} min</div>'
                            f'<div>Z3&nbsp;&nbsp;{zone_minutes["Zone 3"]:.0f} min</div>'
                            f'<div>Z4&nbsp;&nbsp;{zone_minutes["Zone 4"]:.0f} min</div>'
                            f'<div>Z5+ {zone_minutes["Zone 5+"]:.0f} min</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )