from datetime import date
import streamlit as st
from Strava.strava_user import get_training_goal
from helpers.training_plan_functions import _parse_goal_date

PHASE_COLORS = {
    "Base": "#3B82F6",
    "Build": "#10B981",
    "Threshold": "#F59E0B",
    "Peak": "#EF4444",
}

PHASE_DEFINITIONS = [
    ("Base", 0.40, "Endurance"),
    ("Build", 0.30, "Tempo"),
    ("Threshold", 0.20, "Threshold"),
    ("Peak", 0.10, "VO2max"),
]

def build_phases(weeks_to_goal):
    phases = []
    remaining = weeks_to_goal
    for name, percentage, focus in PHASE_DEFINITIONS:
        if remaining <= 0:
            break
        weeks = max(1, round(weeks_to_goal * percentage))
        weeks = min(weeks, remaining)
        phases.append({"name": name, "weeks": weeks, "focus": focus})
        remaining -= weeks
    if phases:
        phases[-1]["weeks"] += remaining
    return phases

def show_periodisation_dialog(username):
    goal = get_training_goal(username)
    goal_date = goal.get("goal_date") if isinstance(goal, dict) else None
    goal_name = goal.get("name") if isinstance(goal, dict) else None
    parsed_goal = _parse_goal_date(goal_date)
    if not parsed_goal:
        st.info("Set a goal date in Settings to view your periodisation plan.")
        return
    days_to_goal = max(0, (parsed_goal - date.today()).days)
    weeks_to_goal = max(1, (days_to_goal + 6) // 7)
    phases = build_phases(weeks_to_goal)
    goal_label = {
        "general_fitness": "General Fitness",
        "gran_fondo": "Gran Fondo",
        "criterium": "Criterium",
        "race": "Race",
    }.get(goal_name, str(goal_name or "General Fitness").replace("_", " ").title())
    total_phase_weeks = sum(phase["weeks"] for phase in phases)
    st.markdown(f"""
    <div style="border:1px solid rgba(148,163,184,.18);border-radius:14px;padding:16px 18px;margin-bottom:18px;background:rgba(255,255,255,.02);">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:20px;">
            <div>
                <div style="font-size:20px;font-weight:750;">{goal_label}</div>
                <div style="font-size:12px;color:#64748B;margin-top:3px;">{weeks_to_goal} weeks to goal · {parsed_goal.strftime("%d %b %Y")}</div>
            </div>
            <div style="text-align:right;white-space:nowrap;">
                <div style="font-size:11px;color:#64748B;text-transform:uppercase;letter-spacing:.06em;font-weight:700;">Training approach</div>
                <div style="font-size:13px;font-weight:600;margin-top:2px;">Progressive</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div style="font-size:14px;font-weight:700;margin-bottom:10px;">Periodisation</div>', unsafe_allow_html=True)
    timeline = ""
    for phase in phases:
        color = PHASE_COLORS.get(phase["name"], "#64748B")
        width = phase["weeks"] / total_phase_weeks * 100
        timeline += f'<div style="width:{width:.2f}%;height:8px;background:{color};"></div>'
    st.markdown(f'<div style="display:flex;width:100%;height:8px;border-radius:999px;overflow:hidden;margin-bottom:10px;">{timeline}</div>', unsafe_allow_html=True)
    phase_cols = st.columns(len(phases))
    for col, phase in zip(phase_cols, phases):
        with col:
            color = PHASE_COLORS.get(phase["name"], "#64748B")
            st.markdown(f"""
            <div style="padding:8px 0;">
                <div style="font-size:12px;font-weight:750;color:{color};">{phase["name"]}</div>
                <div style="font-size:11px;color:#64748B;margin-top:2px;">{phase["weeks"]} week{"s" if phase["weeks"] != 1 else ""}</div>
            </div>
            """, unsafe_allow_html=True)
    st.divider()
    for index, phase in enumerate(phases):
        name = phase["name"]
        focus = phase["focus"]
        weeks = phase["weeks"]
        color = PHASE_COLORS.get(name, "#64748B")
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:14px;padding:11px 4px;border-bottom:1px solid rgba(148,163,184,.12);">
            <div style="width:34px;height:34px;min-width:34px;border-radius:10px;background:{color}18;color:{color};display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:800;">{index + 1}</div>
            <div style="flex:1;">
                <div style="font-size:13px;font-weight:700;">{name}</div>
                <div style="font-size:11px;color:{color};font-weight:600;margin-top:2px;">{focus} focus</div>
            </div>
            <div style="font-size:11px;color:#64748B;">{weeks} week{"s" if weeks != 1 else ""}</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("""
    <div style="margin-top:16px;padding:11px 13px;border-radius:10px;background:rgba(148,163,184,.06);font-size:11px;color:#64748B;line-height:1.5;">
        Training gradually shifts from aerobic development toward higher-intensity, goal-specific work as the goal approaches.
    </div>
    """, unsafe_allow_html=True)

@st.dialog("Periodisation plan", width="large")
def open_periodisation_dialog(username):
    show_periodisation_dialog(username)