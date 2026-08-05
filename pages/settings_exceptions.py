import streamlit as st


from datetime import date, timedelta, datetime

from streamlit_calendar import calendar

from helpers.availability import load_availability
from helpers.exceptions import save_exception
from helpers.exceptions import remove_exception
from helpers.style import calendar_style

def clean_calendar_date(value):
    """
    Fix streamlit-calendar UTC offset bug.
    """

    if "T" in value:

        # Take date part
        date_string = value[:10]

        # Shift one day forward
        corrected_date = (
            datetime.strptime(date_string, "%Y-%m-%d")
            + timedelta(days=1)
        )

        return corrected_date.strftime("%Y-%m-%d")

    return value

def get_hours_for_date(day, availability):

    day_string = str(day)

    if day_string in availability["exceptions"]:
        return availability["exceptions"][day_string]["hours"]

    weekday = day.strftime("%A")

    return availability["weekly"][weekday]["hours"]


def get_color(hours):

    if hours == 0:
        return "#9ca3af"

    elif hours <= 2:
        return "#3b82f6"

    elif hours <= 4:
        return "#f59e0b"

    else:
        return "#ef4444"




username = st.session_state["username"]

availability = load_availability(username)

st.write("Availability loaded:")

events = []


start_date = date.today()

end_date = start_date + timedelta(days=180)


current = start_date


while current <= end_date:

    weekly_hours = availability["weekly"][current.strftime("%A")].get("hours", 0)


    # Normal weekly availability
    events.append(
        {
            "title": "Rest" if weekly_hours == 0 else f"{weekly_hours}h",
            "start": str(current),
            "backgroundColor": get_color(weekly_hours),
            "borderColor": get_color(weekly_hours),
        }
    )


    # Exception availability
    current_string = current.isoformat()

    if current_string in availability["exceptions"]:

        exception_hours = availability["exceptions"][current_string].get("hours", 0)

        events.append(
            {
                "title": f"Exception: {exception_hours}h",
                "start": current_string,
                "backgroundColor": "#8b5cf6",
                "borderColor": "#8b5cf6",
            }
        )


    current += timedelta(days=1)

calendar_style()
selected = calendar(
    events=events,
    options={
        "initialView": "dayGridMonth",
        "initialDate": str(date.today()),

        "height": 700,
        "timezone": 'local',
    },
    callbacks=["dateClick"],
    key=f"availability_calendar_{username}"
)

# Calendar click
if selected and selected.get("dateClick"):

    selected_date = clean_calendar_date(
        selected["dateClick"]["date"]
    )

    st.session_state.selected_date = selected_date


if "selected_date" in st.session_state:


    selected_date = st.session_state.selected_date


    st.divider()


    st.subheader(
        f"Change availability: {selected_date}"
    )


    selected_day = date.fromisoformat(
        selected_date
    )


    current_hours = get_hours_for_date(
        selected_day,
        availability
    )


    hours = st.slider(
        "Available training hours",
        min_value=0,
        max_value=6,
        value=current_hours,
        step=1
    )


    col1, col2 = st.columns(2)


    with col1:

        if st.button(
            "Save exception",
            type="primary"
        ):

            save_exception(
                username,
                selected_date,
                {
                    "available": hours > 0,
                    "hours": hours
                }
            )

            st.success(
                "Availability exception saved"
            )


            del st.session_state.selected_date

            st.rerun()



    with col2:

        if selected_date in availability["exceptions"]:

            if st.button("Remove exception"):

                remove_exception(
                    username,
                    selected_date
                )

                st.success(
                    "Exception removed"
                )

                del st.session_state.selected_date
                st.cache_data.clear()
                st.rerun()