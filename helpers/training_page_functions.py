import os
from datetime import date,timedelta
from pathlib import Path
import pandas as pd
import streamlit as st
from helpers.metrics import TRAINING_ZONES,get_training_zone,ZONE_KEYS,ZONE_TO_DISPLAY
from helpers.training_plan_functions import DAYS,CATEGORY_COLORS,load_workouts,workout_to_plot_steps,generate_workout_fit
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
        for index,zone in enumerate(ZONE_KEYS,1):
            power_col=f"time_z{index}_power"
            hr_col=f"time_z{index}_hr"
            power_time=activity.get(power_col,0)
            hr_time=activity.get(hr_col,0)
            if power_time is not None and not pd.isna(power_time):power_time=float(power_time)/60
            else:power_time=0
            if hr_time is not None and not pd.isna(hr_time):hr_time=float(hr_time)/60
            else:hr_time=0
            zones[zone]+=power_time+hr_time
        vo2max_power=activity.get("time_z5_power",0)
        anaerobic_power=activity.get("time_z6_power",0)
        if vo2max_power is not None and not pd.isna(vo2max_power):vo2max_power=float(vo2max_power)/60
        else:vo2max_power=0
        if anaerobic_power is not None and not pd.isna(anaerobic_power):anaerobic_power=float(anaerobic_power)/60
        else:anaerobic_power=0
        zones["VO2max"]+=vo2max_power
        zones["Anaerobic"]+=anaerobic_power
    return zones
def get_workout_duration(workout):
    steps=(workout or {}).get("steps",[])
    if not steps:return 0
    return round(sum(float(step.get("duration_seconds",0) or 0) for step in steps)/60)
def get_workout_zone_minutes(workout):
    display_zones = list(dict.fromkeys([ZONE_TO_DISPLAY[z] for z in ZONE_KEYS]))
    zones={z:0.0 for z in display_zones}
    for step in (workout or {}).get("steps",[]):
        intensity=float(step.get("intensity",0) or 0)/100
        minutes=float(step.get("duration_seconds",0) or 0)/60
        zone=ZONE_TO_DISPLAY.get(get_training_zone(intensity),"Zone 1")
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
def render_preview(workout,key,height=115):
    steps=workout_to_plot_steps(workout)
    if not steps:return
    from helpers.workout_builder import plot_workout_summary
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
        st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;padding:7px 10px;margin-bottom:3px;background:#f8fafc;border:1px solid #e5e7eb;border-radius:5px;font-size:11px;color:#17212b;"><span>{name}{repeat_text}</span><span style="font-weight:700;">{minutes}:{secs:02d} · IF {intensity/100:.2f}</span></div>',unsafe_allow_html=True)
    render_preview(workout,f"details_preview_{workout.get('id',workout.get('_file','workout'))}",height=260)
    try:
        fit_bytes,filename=generate_workout_fit(workout)
        st.download_button("Download FIT",data=fit_bytes,file_name=filename,mime="application/octet-stream",use_container_width=True,key=f"details_fit_{workout.get('id',workout.get('_file','workout'))}")
    except Exception:
        st.warning("FIT file unavailable for this workout.")
def render_clickable_workout_card(workout,day,date_text,category,duration_text,color,key):
    st.markdown(f"""<div class="training-card-wrapper-{key}" style="position:relative;"><div style="border-top:3px solid {color};background:{color}12;border-radius:7px;padding:7px 4px;height:64px;text-align:center;overflow:hidden;box-sizing:border-box;"><div style="font-size:9px;color:#64748B;">{day[:3]} · {date_text}</div><div style="font-size:10px;font-weight:700;color:{color};margin-top:6px;">{category}</div><div style="font-size:9px;color:#64748B;margin-top:3px;">{duration_text}</div></div></div>""",unsafe_allow_html=True)
    if st.button("",key=f"click_{key}",use_container_width=True):
        workout_details_dialog(workout)
    st.markdown(f"""<style>div[data-testid="stButton"]:has(button[kind="secondary"]){{margin-top:-64px!important;position:relative!important;z-index:20!important;}}div[data-testid="stButton"]:has(button[kind="secondary"]) button{{height:64px!important;min-height:64px!important;padding:0!important;border:1px solid transparent!important;background:transparent!important;color:transparent!important;box-shadow:none!important;}}div[data-testid="stButton"]:has(button[kind="secondary"]) button:hover{{background:rgba(255,255,255,.10)!important;border:1px solid {color}66!important;}}</style>""",unsafe_allow_html=True)
@st.dialog("Choose workout")
def edit_workout_dialog(day,plan,workouts,sport,username):
    category=plan.get("category","Endurance")
    target_tss=float(plan.get("target_tss",0) or 0)
    color=CATEGORY_COLORS.get(category,"#64748B")
    options=[workout for workout in workouts if workout.get("_category")==category and workout.get("sport","Cycling")==sport]
    if not options:
        st.warning(f"No {category} workouts are available.")
        return
    options=sorted(options,key=lambda workout:abs(float(workout.get("target_tss",0) or 0)-target_tss))
    for index,workout in enumerate(options):
        actual_tss=float(workout.get("target_tss",0) or 0)
        duration=get_workout_duration(workout)
        difference=actual_tss-target_tss
        current=plan.get("workout")
        selected=current and workout.get("_file")==current.get("_file") if current else False
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
            from helpers.database import save_training_plan
            save_training_plan(username,st.session_state.training_plan_horizon)
            st.rerun()
def render_plan_day_card(plan,username):
    day=plan.get("day","")
    if plan.get("rest"):
        category="Rest"
        duration_text="Recovery"
        color="#94A3B8"
        workout=None
    else:
        category=plan.get("category","Endurance")
        workout=plan.get("workout") or {}
        duration=get_workout_duration(workout)
        hours,minutes=divmod(duration,60)
        duration_text=f"{hours}h {minutes:02d}min" if hours else f"{minutes}min"
        color=CATEGORY_COLORS.get(category,"#64748B")
    date_text=str(plan.get("date",""))[5:]
    if workout:
        if st.button(f"{day[:3]} · {date_text}\n{category}\n{duration_text}",key=f"full_plan_day_{plan['date']}",use_container_width=True):
            workout_details_dialog(workout)
    else:
        st.markdown(f'<div style="height:64px;border-top:3px solid {color};background:{color}12;border-radius:7px;padding:7px 4px;text-align:center;box-sizing:border-box;"><div style="font-size:9px;color:#64748B;">{day[:3]} · {date_text}</div><div style="font-size:10px;font-weight:700;color:{color};margin-top:6px;">{category}</div><div style="font-size:9px;color:#64748B;margin-top:3px;">{duration_text}</div></div>',unsafe_allow_html=True)
def render_week_summary(week_plans,zone_target,target_week_tss):
    planned_workouts_tss=sum(float((plan.get("workout") or {}).get("target_tss",(plan.get("workout") or {}).get("estimated_tss",0)) or 0) for plan in week_plans if not plan.get("completed") and not plan.get("rest") and plan.get("workout"))
    display_zones = list(dict.fromkeys([ZONE_TO_DISPLAY[z] for z in ZONE_KEYS]))
    planned_workout_zone_minutes={z:0 for z in display_zones}
    for item in week_plans:
        if item.get("workout"):
            zones=get_workout_zone_minutes(item["workout"])
            for z in planned_workout_zone_minutes:planned_workout_zone_minutes[z]+=zones.get(z,0)
    longterm_zone_minutes={ZONE_TO_DISPLAY[z]:zone_target.get(z,0) for z in ZONE_KEYS}
    st.markdown('<div style="display:grid;grid-template-columns:0.8fr 1fr 1fr;padding:5px 8px;border-bottom:1px solid #edf0f2;background:#f8fafb;"><span style="font-size:8px;font-weight:700;color:#687581;">ZONE</span><span style="font-size:8px;font-weight:700;color:#687581;text-align:right;">PLAN</span><span style="font-size:8px;font-weight:700;color:#687581;text-align:right;">WORKOUTS</span></div>',unsafe_allow_html=True)
    rows=[("TSS",target_week_tss,planned_workouts_tss)]+[(z,longterm_zone_minutes[z],planned_workout_zone_minutes[z]) for z in display_zones]
    for i,(label,longterm,weekly) in enumerate(rows):
        border="" if i==len(rows)-1 else "border-bottom:1px solid #f0f2f4;"
        color=zone_color(label) if label!="TSS" else "#17212b"
        st.markdown(f'<div style="display:grid;grid-template-columns:0.8fr 1fr 1fr;padding:3px 8px;{border}"><span style="font-size:8px;color:#687581;">{label}</span><span style="font-size:9px;font-weight:700;color:{color};text-align:right;">{format_minutes(longterm) if label!="TSS" else f"{longterm:.0f}"}</span><span style="font-size:9px;font-weight:700;color:{color};text-align:right;">{format_minutes(weekly) if label!="TSS" else f"{weekly:.0f}"}</span></div>',unsafe_allow_html=True)
def render_full_week(week_plans,username):
    plans_by_day={plan["day"]:plan for plan in week_plans}
    week_cols=st.columns(7,gap="small")
    for day,col in zip(DAYS,week_cols):
        with col:
            plan=plans_by_day.get(day)
            if not plan:
                st.markdown('<div style="height:64px;"></div>',unsafe_allow_html=True)
                continue
            render_plan_day_card(plan,username)
            if plan.get("workout"):
                zones=get_workout_zone_minutes(plan["workout"])
                st.markdown(f'<div style="font-size:8px;line-height:1.35;color:#94A3B8;margin-top:4px;padding-left:3px;"><div>Z1&nbsp;&nbsp;{zones["Zone 1"]:.0f} min</div><div>Z2&nbsp;&nbsp;{zones["Zone 2"]:.0f} min</div><div>Z3&nbsp;&nbsp;{zones["Zone 3"]:.0f} min</div><div>Z4&nbsp;&nbsp;{zones["Zone 4"]:.0f} min</div><div>Z5+ {zones["Zone 5+"]:.0f} min</div></div>',unsafe_allow_html=True)


def render_training_box_start():
    st.markdown('<div class="training-box">',unsafe_allow_html=True)

def render_training_box_end():
    st.markdown('</div>',unsafe_allow_html=True)

def inject_training_page_css():
    st.markdown("""
    <style>
    .training-box{
        background:#ffffff;
        border:1px solid #e5e9ed;
        border-radius:10px;
        padding:12px 14px;
        margin-bottom:10px;
        box-shadow:0 1px 2px rgba(15,23,42,.02);
    }
    .training-box-title{
        font-size:11px;
        font-weight:750;
        color:#17212b;
        letter-spacing:.01em;
        margin-bottom:7px;
    }
    .training-box-subtitle{
        font-size:9px;
        color:#7a8792;
        margin-top:-3px;
        margin-bottom:7px;
    }
    .training-section-title{
        font-size:13px;
        font-weight:750;
        color:#17212b;
        margin:0;
    }
    .training-section-meta{
        font-size:9px;
        color:#7a8792;
    }
    .training-day-card{
        border-radius:6px;
        padding:6px 4px;
        min-height:62px;
        text-align:center;
        box-sizing:border-box;
    }
    .training-day-name{
        font-size:8px;
        font-weight:700;
        color:#64748b;
    }
    .training-day-date{
        font-size:8px;
        color:#94a3b8;
        margin-top:1px;
    }
    .training-day-category{
        font-size:9px;
        font-weight:750;
        margin-top:7px;
    }
    .training-day-detail{
        font-size:8px;
        color:#64748b;
        margin-top:2px;
    }
    .training-zone-row{
        font-size:7px;
        line-height:1.3;
        color:#94a3b8;
        margin-top:3px;
    }
    </style>
    """,unsafe_allow_html=True)