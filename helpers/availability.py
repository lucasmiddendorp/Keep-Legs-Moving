import os
import json
from datetime import datetime, timedelta
from helpers.database import get_connection, get_user_id
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
    user_id = get_user_id(username)
    if user_id is None:
        return json.loads(json.dumps(DEFAULT_AVAILABILITY))

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT day, available, hours, start_time, end_time
                FROM availability_weekly WHERE user_id = %s
            """, (user_id,))
            weekly_rows = cur.fetchall()
            cur.execute("""
                SELECT date, available, hours, start_time, end_time
                FROM availability_exceptions WHERE user_id = %s
            """, (user_id,))
            exception_rows = cur.fetchall()
    finally:
        conn.close()

    if not weekly_rows and not exception_rows:
        try:
            with open(get_availability_file(username), "r") as file:
                legacy = json.load(file)
            save_availability(username, legacy)
            return legacy
        except FileNotFoundError:
            return json.loads(json.dumps(DEFAULT_AVAILABILITY))

    weekly = json.loads(json.dumps(DEFAULT_AVAILABILITY["weekly"]))
    for day, available, hours, start, end in weekly_rows:
        weekly[day] = {"available": available, "hours": hours or 0,
                       "start": start, "end": end}

    exceptions = {}
    for exception_date, available, hours, start, end in exception_rows:
        exceptions[exception_date.isoformat()] = {
            "available": available, "hours": hours or 0,
            "start": start, "end": end,
        }
    return {"weekly": weekly, "exceptions": exceptions}


def save_availability(username, availability):
    user_id = get_user_id(username)
    if user_id is None:
        raise ValueError("User does not exist.")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for day, data in availability.get("weekly", {}).items():
                cur.execute("""
                    INSERT INTO availability_weekly
                        (user_id, day, available, hours, start_time, end_time)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, day) DO UPDATE SET
                        available = EXCLUDED.available, hours = EXCLUDED.hours,
                        start_time = EXCLUDED.start_time, end_time = EXCLUDED.end_time
                """, (user_id, day, data.get("available", False),
                       data.get("hours", 0), data.get("start"), data.get("end")))
            for exception_date, data in availability.get("exceptions", {}).items():
                cur.execute("""
                    INSERT INTO availability_exceptions
                        (user_id, date, available, hours, start_time, end_time)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, date) DO UPDATE SET
                        available = EXCLUDED.available, hours = EXCLUDED.hours,
                        start_time = EXCLUDED.start_time, end_time = EXCLUDED.end_time
                """, (user_id, exception_date, data.get("available", False),
                       data.get("hours", 0), data.get("start"), data.get("end")))
        conn.commit()
    finally:
        conn.close()


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
    save_availability(username, availability)


def remove_exception(username, date):
    user_id = get_user_id(username)
    if user_id is None:
        raise ValueError("User does not exist.")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM availability_exceptions WHERE user_id = %s AND date = %s",
                (user_id, date),
            )
        conn.commit()
    finally:
        conn.close()


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

            hours = day.get("hours", 0)
            if not hours and day.get("start") and day.get("end"):
                start = datetime.strptime(day["start"], "%H:%M")
                end = datetime.strptime(day["end"], "%H:%M")
                hours = (end - start).seconds / 3600

            available.append(
                {
                    "date": current_date,
                    "hours": hours,
                    "start": day["start"],
                    "end": day["end"]
                }
            )

    return available