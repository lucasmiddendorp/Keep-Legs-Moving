import streamlit as st

from helpers.availability import load_availability, save_availability
from helpers.style import apply_global_style


DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def render_weekly_availability(username):
    apply_global_style()
    availability = load_availability(username)
    weekly = availability["weekly"]
    updated_weekly = {}

    st.markdown('<div class="profile-section-title">Weekly Availability</div>', unsafe_allow_html=True)
    st.caption("Set how many hours you are normally available each day.")

    columns = st.columns(7, gap="small")
    for column, day in zip(columns, DAYS):
        with column:
            current = weekly.get(day, {"available": False, "hours": 0})
            current_hours = max(0.0, min(12.0, float(current.get("hours", 0) or 0)))
            st.markdown(
                f'<div style="font-size:12px;font-weight:700;color:#526170;">{day[:3]}</div>',
                unsafe_allow_html=True,
            )
            hours = st.number_input(
                "Hours",
                min_value=0.0,
                max_value=12.0,
                value=current_hours,
                step=0.5,
                key=f"availability_hours_{day}",
                label_visibility="collapsed",
            )
            updated_weekly[day] = {"available": hours > 0, "hours": hours}

    if st.button("Save Weekly Availability", type="primary"):
        availability["weekly"] = updated_weekly
        save_availability(username, availability)
        st.success("Weekly availability saved")
