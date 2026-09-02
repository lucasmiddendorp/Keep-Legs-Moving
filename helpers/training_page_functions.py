import os
from datetime import date,timedelta
from pathlib import Path
import pandas as pd
import streamlit as st
from Strava.strava_user import get_user_settings
from helpers.metrics import TRAINING_ZONES,get_training_zone,ZONE_KEYS,ZONE_TO_DISPLAY
from helpers.training_plan_functions import DAYS,CATEGORY_COLORS,load_workouts,workout_to_plot_steps,generate_user_fit_workout
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
        repeat=int(step.get("repeat",1) or 1)
        minutes=float(step.get("duration_seconds",0) or 0)*repeat/60
        zone=get_training_zone(intensity)
        if zone == "Anaerobic":
            zone = "VO2max"
        if zone in zones:zones[zone]+=minutes
    return zones
def get_completed_week_zones(activities,week_start,today,ftp):
    zones=empty_zones()
    if activities is None or activities.empty or "date" not in activities:return zones
    frame=activities.copy()
    frame["date"]=pd.to_datetime(frame["date"],errors="coerce").dt.date
    frame=frame[(frame["date"]>=week_start)&(frame["date"]<=today)]
    for _,activity in frame.iterrows():
        power_times=[]
        hr_times=[]
        for index in range(1,len(ZONE_KEYS)+1):
            power_time=activity.get(f"time_z{index}_power",0)
            hr_time=activity.get(f"time_z{index}_hr",0)
            power_times.append(float(power_time) if power_time is not None and not pd.isna(power_time) else 0)
            hr_times.append(float(hr_time) if hr_time is not None and not pd.isna(hr_time) else 0)
        source_times=power_times if any(power_times) else hr_times
        for zone,seconds in zip(ZONE_KEYS,source_times):zones[zone]+=seconds/60
    zones["VO2max"] += zones["Anaerobic"]
    zones["Anaerobic"] = 0.0
    return zones
def get_workout_duration(workout):
    steps=(workout or {}).get("steps",[])
    if not steps:
        return round(float((workout or {}).get("duration_minutes",0) or 0))
    return round(sum((float(step.get("duration_seconds",0) or 0) or float(step.get("duration_minutes",0) or 0)*60)*int(step.get("repeat",1) or 1) for step in steps)/60)
def get_workout_if(workout):
    target_if=float((workout or {}).get("target_if",0) or 0)
    if target_if:return target_if
    steps=(workout or {}).get("steps",[])
    total=sum(float(step.get("duration_seconds",0) or 0)*int(step.get("repeat",1) or 1) for step in steps)
    if not total:return 0.0
    weighted=sum(float(step.get("duration_seconds",0) or 0)*int(step.get("repeat",1) or 1)*(float(step.get("intensity",0) or 0)/100)**4 for step in steps)
    return (weighted/total)**0.25
def get_workout_zone_minutes(workout):
    display_zones = list(dict.fromkeys([ZONE_TO_DISPLAY[z] for z in ZONE_KEYS]))
    zones={z:0.0 for z in display_zones}
    for step in (workout or {}).get("steps",[]):
        intensity=float(step.get("intensity",0) or 0)/100
        repeat=int(step.get("repeat",1) or 1)
        minutes=float(step.get("duration_seconds",0) or 0)*repeat/60
        zone_name=get_training_zone(intensity)
        if zone_name == "Anaerobic":
            zone_name = "VO2max"
        zone=ZONE_TO_DISPLAY.get(zone_name,"Zone 1")
        zones[zone]+=minutes
    return zones
def format_total_time(minutes):
    minutes=int(round(minutes))
    hours,mins=divmod(minutes,60)
    return f"{hours}h {mins:02d}min" if hours else f"{mins}min"
def format_minutes(minutes):
    total_minutes=max(0,round(float(minutes or 0)))
    hours,remaining_minutes=divmod(total_minutes,60)
    return f"{hours}h {remaining_minutes:02d}min" if hours else f"{remaining_minutes}min"
def clean_activity_type(value):
    return str(value or "Activity").replace("root='","").replace("'","")
def render_small_progress_circle(title,percentage,subtitle,color):
    percentage=max(0,min(float(percentage),100))
    st.markdown(f"""<div style="text-align:center;"><div style="width:82px;height:82px;border-radius:50%;background:conic-gradient({color} {percentage*3.6}deg,#e6ebef 0deg);display:flex;align-items:center;justify-content:center;margin:auto;"><div style="width:66px;height:66px;border-radius:50%;background:white;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:800;color:#17212b;">{percentage:.0f}%</div></div><div style="margin-top:8px;font-size:10px;font-weight:700;color:#526170;text-transform:uppercase;letter-spacing:.06em;">{title}</div><div style="margin-top:2px;font-size:9px;color:#7a8792;">{subtitle}</div></div>""",unsafe_allow_html=True)

def render_preview(workout, key, height=180):
    raw_steps = workout.get("steps", [])
    if not raw_steps:
        st.caption("No workout steps available.")
        return
    plot_steps = []
    for step in raw_steps:
        duration = float(step.get("duration_seconds", 0) or 0)
        if duration <= 0:
            duration = (
                float(step.get("duration_minutes", 0) or 0) * 60
                + float(step.get("duration_seconds", 0) or 0)
            )
        if duration <= 0:
            continue
        intensity = float(step.get("intensity", 55) or 55)
        plot_steps.append({
            "name": step.get("name", "Step"),
            "duration": duration,
            "target_low": intensity,
            "target_high": intensity,
            "type": "step",
        })
    if not plot_steps:
        st.caption("No timed steps available for this workout.")
        return
    from helpers.workout_builder import plot_workout_summary 
    username=st.session_state.get("username")
    user_settings=get_user_settings(username) if username else {}
    sport = str(workout.get("sport",workout.get("_sport","Cycling")) or "Cycling").title()
    ftp=float(user_settings.get("ftp",0) or 0)
    running_threshold=user_settings.get("threshold_pace")
    print("Running threshold:", running_threshold)
    fig=plot_workout_summary(
        plot_steps,
        sport=sport,
        ftp=workout.get("_ftp", ftp),
        threshold_pace=running_threshold,
    )
    fig.update_layout(
        height=height,
    )
    st.plotly_chart(
        fig,
        width="stretch",
        config={"displayModeBar": False},
        key=key,
    )
    
@st.dialog("Workout details")
def workout_details_dialog(workout):
    category=workout.get("_category",workout.get("category","Workout"))
    duration=get_workout_duration(workout)
    target_tss=float(workout.get("target_tss",workout.get("estimated_tss",0)) or 0)
    target_if=get_workout_if(workout)
    st.subheader(workout.get("name","Workout"))
    st.caption(f"{category} · {format_minutes(duration)} · IF {target_if:.2f} · {target_tss:.0f} TSS")
    render_preview(
        workout,
        f"details_preview_{workout.get('id',workout.get('_file','workout'))}",
        height=260
    )
    try:
        username=st.session_state.get("username")
        if not username:
            raise ValueError("Please log in first.")
        fit_bytes,filename=generate_user_fit_workout(workout,username)
        st.download_button(
            "Download FIT",
            data=fit_bytes,
            file_name=filename,
            mime="application/octet-stream",
            use_container_width=True,
            key=f"details_fit_{workout.get('id',workout.get('_file','workout'))}"
        )
    except Exception:
        st.warning("FIT file unavailable for this workout.")

def render_clickable_workout_card(workout,day,date_text,category,duration_text,color,key):
    st.markdown(
        f"""
        <div class="workout-day-card" style="
            position:relative;
            height:64px;
            box-sizing:border-box;
            background:{color}12;
            border:1px solid {color}55;
            border-top:3px solid {color};
            border-radius:7px;
            padding:7px 4px;
            text-align:center;
            overflow:hidden;
        ">
            <div style="
                font-size:8px;
                color:#7a8792;
                font-weight:700;
                line-height:1.2;
            ">
                {day[:3]} · {date_text}
            </div>
            <div style="
                font-size:10px;
                color:#17212b;
                font-weight:700;
                margin-top:8px;
                white-space:nowrap;
                overflow:hidden;
                text-overflow:ellipsis;
            ">
                {category}
            </div>
            <div style="
                font-size:8px;
                color:#6b7785;
                margin-top:3px;
                white-space:nowrap;
                overflow:hidden;
                text-overflow:ellipsis;
            ">
                {duration_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "",
        key=f"click_{key}",
        width="stretch",
        help="Open workout",
    ):
        workout_details_dialog(workout)

    st.markdown(
        f"""
        <style>
        div.st-key-click_{key} {{
            position:relative;
            margin-top:-94px;
            height:64px;
            z-index:10;
        }}

        div.st-key-click_{key} button {{
            width:100%!important;
            height:64px!important;
            min-height:64px!important;
            padding:0!important;
            margin:0!important;
            border:0!important;
            background:transparent!important;
            box-shadow:none!important;
            color:transparent!important;
            cursor:pointer!important;
        }}

        div.st-key-click_{key} button:hover {{
            border:0!important;
            background:{color}10!important;
            box-shadow:none!important;
        }}

        div.st-key-click_{key} button:focus {{
            border:0!important;
            box-shadow:none!important;
            outline:none!important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_static_day_card(day,date_text,category,detail,color):
    st.markdown(
        f"""
        <div style="
            height:64px;
            box-sizing:border-box;
            background:{color}12;
            border:1px solid {color}55;
            border-top:3px solid {color};
            border-radius:7px;
            padding:7px 4px;
            text-align:center;
            overflow:hidden;
        ">
            <div style="
                font-size:8px;
                color:#7a8792;
                font-weight:700;
                line-height:1.2;
            ">
                {day[:3]} · {date_text}
            </div>
            <div style="
                font-size:10px;
                color:#17212b;
                font-weight:700;
                margin-top:8px;
                white-space:nowrap;
                overflow:hidden;
                text-overflow:ellipsis;
            ">
                {category}
            </div>
            <div style="
                font-size:8px;
                color:#6b7785;
                margin-top:3px;
                white-space:nowrap;
                overflow:hidden;
                text-overflow:ellipsis;
            ">
                {detail}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_plan_day_card(plan):
    day=plan.get("day","")
    if plan.get("rest"):
        category="Rest"
        duration_text="Recovery"
        color="#94A3B8"
        workout=None
    else:
        category=plan.get("category","Endurance")
        workout=plan.get("workout") or {}
        if plan.get("completed"):
            duration=round(float(plan.get("duration_minutes",0) or 0))
            hours,minutes=divmod(duration,60)
            duration_text=f"{hours}h {minutes:02d}min" if hours else f"{minutes}min"
            duration_text=f"{duration_text} · {float(plan.get('actual_tss',0) or 0):.0f} TSS"
            color="#6f9bb2"
        else:
            duration=get_workout_duration(workout)
            hours,minutes=divmod(duration,60)
            duration_text=f"{hours}h {minutes:02d}min" if hours else f"{minutes}min"
            duration_text=f"{duration_text} · IF {get_workout_if(workout):.2f}"
            color=CATEGORY_COLORS.get(category,"#64748B")
    date_text=str(plan.get("date",""))[5:]
    if workout:
        render_clickable_workout_card(
            workout,
            day,
            date_text,
            category,
            duration_text,
            color,
            f"full_plan_day_{plan['date']}",
        )
    else:
        render_static_day_card(day,date_text,category,duration_text,color)


def render_week_summary(week_plans,zone_target,target_week_tss,activities=None):
    planned_workouts_tss=sum(float((plan.get("workout") or {}).get("target_tss",(plan.get("workout") or {}).get("estimated_tss",0)) or 0) for plan in week_plans if not plan.get("completed") and not plan.get("rest") and plan.get("workout"))
    completed_workouts_tss=0.0
    if activities is not None and not activities.empty and "date" in activities.columns:
        week_dates={str(plan.get("date")) for plan in week_plans}
        completed=activities.copy()
        completed["date"]=pd.to_datetime(completed["date"],errors="coerce").dt.date.astype(str)
        completed=completed[completed["date"].isin(week_dates)]
        if "stress" in completed.columns:
            completed_workouts_tss=pd.to_numeric(completed["stress"],errors="coerce").fillna(0).sum()
    workouts_tss=planned_workouts_tss+completed_workouts_tss
    display_zones = list(dict.fromkeys([ZONE_TO_DISPLAY[z] for z in ZONE_KEYS]))
    planned_workout_zone_minutes={z:0 for z in display_zones}
    for item in week_plans:
        if item.get("workout"):
            zones=get_workout_zone_minutes(item["workout"])
            for z in planned_workout_zone_minutes:planned_workout_zone_minutes[z]+=zones.get(z,0)
    longterm_zone_minutes={}
    for zone in ZONE_KEYS:
        display_zone=ZONE_TO_DISPLAY[zone]
        longterm_zone_minutes[display_zone]=longterm_zone_minutes.get(display_zone,0)+zone_target.get(zone,0)
    st.markdown('<div style="display:grid;grid-template-columns:0.8fr 1fr 1fr;padding:5px 8px;border-bottom:1px solid #edf0f2;background:#f8fafb;"><span style="font-size:8px;font-weight:700;color:#687581;">ZONE</span><span style="font-size:8px;font-weight:700;color:#687581;text-align:right;">PLAN</span><span style="font-size:8px;font-weight:700;color:#687581;text-align:right;">WORKOUTS</span></div>',unsafe_allow_html=True)
    rows=[("TSS",target_week_tss,workouts_tss)]+[(z,longterm_zone_minutes[z],planned_workout_zone_minutes[z]) for z in display_zones]
    for i,(label,longterm,weekly) in enumerate(rows):
        border="" if i==len(rows)-1 else "border-bottom:1px solid #f0f2f4;"
        color=zone_color(label) if label!="TSS" else "#17212b"
        st.markdown(f'<div style="display:grid;grid-template-columns:0.8fr 1fr 1fr;padding:3px 8px;{border}"><span style="font-size:8px;color:#687581;">{label}</span><span style="font-size:9px;font-weight:700;color:{color};text-align:right;">{format_minutes(longterm) if label!="TSS" else f"{longterm:.0f}"}</span><span style="font-size:9px;font-weight:700;color:{color};text-align:right;">{format_minutes(weekly) if label!="TSS" else f"{weekly:.0f}"}</span></div>',unsafe_allow_html=True)

def render_full_week(week_plans):
    plans_by_day={plan["day"]:plan for plan in week_plans}
    week_cols=st.columns(7,gap="small")
    for day,col in zip(DAYS,week_cols):
        with col:
            plan=plans_by_day.get(day)
            if not plan:
                st.markdown('<div style="height:64px;"></div>',unsafe_allow_html=True)
                continue
            render_plan_day_card(plan)


def render_training_box_start():
    st.markdown('<div class="training-box">',unsafe_allow_html=True)

def render_training_box_end():
    st.markdown('</div>',unsafe_allow_html=True)
