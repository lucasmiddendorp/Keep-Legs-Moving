import os
import json
from datetime import datetime, timedelta
from helpers.user_cache import get_user_cache_paths


DEFAULT_AVAILABILITY = {
    "weekly": {
        day: {
            "available": False,
            "start": None,
            "end": None
        }
        for day in [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
    },
    "exceptions": {}
}


def get_availability_file(username):
    activity_file, _ = get_user_cache_paths(username)
    folder = os.path.dirname(activity_file)
    return os.path.join(folder, "availability.json")


def load_availability(username):

    path = get_availability_file(username)

    if not os.path.exists(path):
        save_availability(username, DEFAULT_AVAILABILITY)
        return DEFAULT_AVAILABILITY

    with open(path, "r") as file:
        return json.load(file)


def save_availability(username, availability):

    path = get_availability_file(username)

    with open(path, "w") as file:
        json.dump(
            availability,
            file,
            indent=4
        )


def update_weekly_availability(username, weekly):

    availability = load_availability(username)

    availability["weekly"] = weekly

    save_availability(
        username,
        availability
    )


def update_exception(username, date, data):

    availability = load_availability(username)

    availability["exceptions"][str(date)] = data

    save_availability(
        username,
        availability
    )


def remove_exception(username, date):

    availability = load_availability(username)

    date = str(date)

    if date in availability["exceptions"]:
        del availability["exceptions"][date]

    save_availability(
        username,
        availability
    )


def get_day_availability(username, date):

    availability = load_availability(username)

    date_string = str(date)

    # Exceptions always override weekly schedule
    if date_string in availability["exceptions"]:
        return availability["exceptions"][date_string]


    weekday = date.strftime("%A")

    return availability["weekly"].get(
        weekday,
        {
            "available": False,
            "start": None,
            "end": None
        }
    )


def get_available_hours(username, start_date, days=7):

    available = []

    for i in range(days):

        current_date = start_date + timedelta(days=i)

        day = get_day_availability(
            username,
            current_date
        )

        if day["available"]:

            start = datetime.strptime(
                day["start"],
                "%H:%M"
            )

            end = datetime.strptime(
                day["end"],
                "%H:%M"
            )

            hours = (
                end-start
            ).seconds / 3600

            available.append(
                {
                    "date": current_date,
                    "hours": hours,
                    "start": day["start"],
                    "end": day["end"]
                }
            )

    return available