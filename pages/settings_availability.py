import streamlit as st

from helpers.availability import load_availability, save_availability


DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]



username = st.session_state["username"]

availability = load_availability(username)

weekly = availability["weekly"]

updated_weekly = {}

st.subheader("Weekly Availability")

st.write(
    "Set how many hours you are normally available each day."
)


for day in DAYS:

    current = weekly.get(
        day,
        {
            "available": False,
            "hours": 0
        }
    )


    hours = st.slider(
        day,
        min_value=0,
        max_value=6,
        value=current.get("hours", 0),
        step=1,
        help="Maximum training time available"
    )


    updated_weekly[day] = {
        "available": hours > 0,
        "hours": hours
    }


if st.button(
    "💾 Save Weekly Availability",
    type="primary"
):

    availability["weekly"] = updated_weekly

    save_availability(
        username,
        availability
    )

    st.success(
        "Weekly availability saved"
    )