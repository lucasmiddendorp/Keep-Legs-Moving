import streamlit as st
import psycopg2
import numpy as np
from psycopg2.extras import RealDictCursor, Json
import math


def get_connection():
    return psycopg2.connect(st.secrets["database"]["url"])


def init_database():
    conn = get_connection()

    try:
        with conn.cursor() as cur:

            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(255),
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    ftp FLOAT DEFAULT 300,
                    max_hr INTEGER DEFAULT 190,
                    threshold_hr FLOAT,
                    threshold_pace FLOAT DEFAULT 5.0,
                    weight FLOAT DEFAULT 70,
                    athlete_level VARCHAR(50) DEFAULT 'Amateur',
                    training_progression FLOAT DEFAULT 8,
                    atl_tc INTEGER DEFAULT 7
                );
            """)
            cur.execute("ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS sessions_per_week INTEGER")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS training_goals (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(100),
                    goal_date DATE,
                    event_distance_km FLOAT,
                    event_climb_m FLOAT,
                    event_type VARCHAR(50)
                );
            """)
            cur.execute("ALTER TABLE training_goals ADD COLUMN IF NOT EXISTS event_distance_km FLOAT")
            cur.execute("ALTER TABLE training_goals ADD COLUMN IF NOT EXISTS event_climb_m FLOAT")
            cur.execute("ALTER TABLE training_goals ADD COLUMN IF NOT EXISTS event_type VARCHAR(50)")
            cur.execute("ALTER TABLE training_goals ADD COLUMN IF NOT EXISTS sport VARCHAR(20) DEFAULT 'Cycling'")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS strava_accounts (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    athlete_id BIGINT UNIQUE,
                    access_token TEXT,
                    refresh_token TEXT,
                    expires_at BIGINT,
                    connected BOOLEAN DEFAULT FALSE
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS availability_weekly (
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    day VARCHAR(20),
                    available BOOLEAN DEFAULT FALSE,
                    hours FLOAT DEFAULT 0,
                    start_time VARCHAR(5),
                    end_time VARCHAR(5),
                    PRIMARY KEY (user_id, day)
                );
            """)
            cur.execute("""
                ALTER TABLE availability_weekly
                ADD COLUMN IF NOT EXISTS hours FLOAT DEFAULT 0;
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS availability_exceptions (
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    date DATE,
                    available BOOLEAN DEFAULT FALSE,
                    hours FLOAT DEFAULT 0,
                    start_time VARCHAR(5),
                    end_time VARCHAR(5),
                    PRIMARY KEY (user_id, date)
                );
            """)
            cur.execute("""
                ALTER TABLE availability_exceptions
                ADD COLUMN IF NOT EXISTS hours FLOAT DEFAULT 0;
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS strava_oauth_pending (
                    state VARCHAR(255) PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS training_plans (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    plan JSONB NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS training_plan_sessions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    plan_date DATE NOT NULL,
                    session JSONB NOT NULL,
                    status VARCHAR(30) DEFAULT 'pending',
                    UNIQUE (user_id, plan_date)
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS activity_cache (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    activities JSONB NOT NULL DEFAULT '[]'::jsonb,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS power_stream_cache (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    streams JSONB NOT NULL DEFAULT '[]'::jsonb,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS running_stream_cache (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    streams JSONB NOT NULL DEFAULT '[]'::jsonb,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS curve_cache (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    power_curve JSONB NOT NULL DEFAULT '[]'::jsonb,
                    running_curve JSONB NOT NULL DEFAULT '[]'::jsonb,
                    best_20_min_power FLOAT,
                    best_6_min_distance FLOAT,
                    calculation_version INTEGER NOT NULL DEFAULT 4,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS power_efforts (
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    activity_id BIGINT NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    best_power FLOAT NOT NULL,
                    PRIMARY KEY (user_id, activity_id, duration_seconds)
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS running_efforts (
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    activity_id BIGINT NOT NULL,
                    distance_meters FLOAT NOT NULL,
                    best_speed FLOAT NOT NULL,
                    PRIMARY KEY (user_id, activity_id, distance_meters)
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS training_test_status (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    running_test_done BOOLEAN NOT NULL DEFAULT FALSE,
                    cycling_test_done BOOLEAN NOT NULL DEFAULT FALSE,
                    running_test_answered BOOLEAN NOT NULL DEFAULT FALSE,
                    cycling_test_answered BOOLEAN NOT NULL DEFAULT FALSE,
                    running_goal VARCHAR(100),
                    cycling_goal VARCHAR(100),
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("ALTER TABLE training_test_status ADD COLUMN IF NOT EXISTS running_test_answered BOOLEAN NOT NULL DEFAULT FALSE")
            cur.execute("ALTER TABLE training_test_status ADD COLUMN IF NOT EXISTS cycling_test_answered BOOLEAN NOT NULL DEFAULT FALSE")
            cur.execute("ALTER TABLE training_test_status ADD COLUMN IF NOT EXISTS running_goal VARCHAR(100)")
            cur.execute("ALTER TABLE training_test_status ADD COLUMN IF NOT EXISTS cycling_goal VARCHAR(100)")
            cur.execute("""
                ALTER TABLE curve_cache
                ADD COLUMN IF NOT EXISTS calculation_version INTEGER NOT NULL DEFAULT 4;
            """)
        conn.commit()

    finally:
        conn.close()


def get_user(username):
    conn = get_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM users WHERE username = %s",
                (username,)
            )
            return cur.fetchone()
    finally:
        conn.close()


def create_user(username, email, name, password_hash):
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users
                    (username, email, name, password_hash)
                VALUES
                    (%s, %s, %s, %s)
                RETURNING id
            """, (
                username,
                email,
                name,
                password_hash
            ))

            user_id = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO user_settings (user_id)
                VALUES (%s)
            """, (user_id,))

        conn.commit()
        return user_id

    finally:
        conn.close()


def get_user_id(username):
    user = get_user(username)

    if not user:
        return None

    return user["id"]


def save_training_plan(username, plan):
    user_id = get_user_id(username)
    if user_id is None:
        raise ValueError("User does not exist.")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO training_plans (user_id, plan, updated_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE SET
                    plan = EXCLUDED.plan,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, Json(plan)))
            if isinstance(plan, list):
                for session in plan:
                    if not session.get("date"):
                        continue
                    cur.execute("""
                        INSERT INTO training_plan_sessions
                            (user_id, plan_date, session, status)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (user_id, plan_date) DO UPDATE SET
                            session = EXCLUDED.session,
                            status = COALESCE(training_plan_sessions.status, EXCLUDED.status)
                    """, (
                        user_id,
                        session["date"],
                        Json(session),
                        "done" if session.get("completed") else "pending",
                    ))
        conn.commit()
    finally:
        conn.close()


def load_training_plan(username):
    user_id = get_user_id(username)
    if user_id is None:
        return None
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT plan FROM training_plans WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


def save_activity_cache(username, activities):
    user_id = get_user_id(username)
    if user_id is None:
        raise ValueError("User does not exist.")
    records = activities.replace([np.inf, -np.inf], np.nan).astype(object)
    records = records.where(records.notna(), None).to_dict("records")
    for record in records:
        for key, value in record.items():
            if isinstance(value, (float, np.floating)) and not np.isfinite(value):
                record[key] = None
                continue
            if hasattr(value, "isoformat"):
                record[key] = value.isoformat()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO activity_cache (user_id, activities, updated_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE SET
                    activities = EXCLUDED.activities,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, Json(records)))
        conn.commit()
    finally:
        conn.close()

def load_activity_cache(username):
    #print("DEBUG username:", repr(username))

    user_id = get_user_id(username)
    #print("DEBUG user_id:", user_id)

    if user_id is None:
        #print("DEBUG: user_id is None")
        return None

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, jsonb_array_length(activities), updated_at
                FROM activity_cache
                WHERE user_id = %s
                """,
                (user_id,)
            )

            row = cur.fetchone()

            #print("DEBUG activity_cache row:", row)

            if not row:
                #print("DEBUG: No activity_cache row found")
                return None

            # Now actually retrieve it
            cur.execute(
                """
                SELECT activities
                FROM activity_cache
                WHERE user_id = %s
                """,
                (user_id,)
            )

            activities = cur.fetchone()[0]

            print(
                "DEBUG activities returned:",
                len(activities) if activities is not None else 0
            )

            return activities

    finally:
        conn.close()

def clean_json_data(obj):
    """Convert NaN and Infinity values to None so they are valid JSON."""

    if isinstance(obj, (float, np.floating)):
        if not np.isfinite(obj):
            return None
        return float(obj)

    if isinstance(obj, (np.integer,)):
        return int(obj)

    if isinstance(obj, dict):
        return {
            key: clean_json_data(value)
            for key, value in obj.items()
        }

    if isinstance(obj, (list, tuple)):
        return [
            clean_json_data(value)
            for value in obj
        ]

    return obj

def save_power_stream_cache(username, streams):
    user_id = get_user_id(username)

    if user_id is None:
        raise ValueError("User does not exist.")

    records = streams.to_dict("records")
    records = clean_json_data(records)

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO power_stream_cache (user_id, streams, updated_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    streams = EXCLUDED.streams,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                user_id,
                Json(records)
            ))

        conn.commit()

    finally:
        conn.close()

def load_power_stream_cache(username):
    user_id = get_user_id(username)
    if user_id is None:
        return None
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT streams FROM power_stream_cache WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


def save_running_stream_cache(username, streams):
    user_id = get_user_id(username)
    if user_id is None:
        raise ValueError("User does not exist.")
    records = clean_json_data(streams.to_dict("records"))
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO running_stream_cache (user_id, streams, updated_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE SET
                    streams = EXCLUDED.streams,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, Json(records)))
        conn.commit()
    finally:
        conn.close()


def load_running_stream_cache(username):
    user_id = get_user_id(username)
    if user_id is None:
        return None
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT streams FROM running_stream_cache WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


def save_curve_cache(username, power_curve, running_curve, best_20_min_power=None, best_6_min_distance=None):
    user_id = get_user_id(username)
    if user_id is None:
        raise ValueError("User does not exist.")
    print(
        "Saving curve cache:",
        "power_points=",len(power_curve),
        "running_points=",len(running_curve),
        "running_distances=",[point.get("distance") for point in running_curve],
    )
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO curve_cache (
                    user_id, power_curve, running_curve,
                    best_20_min_power, best_6_min_distance, calculation_version, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, 4, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE SET
                    power_curve = EXCLUDED.power_curve,
                    running_curve = EXCLUDED.running_curve,
                    best_20_min_power = EXCLUDED.best_20_min_power,
                    best_6_min_distance = EXCLUDED.best_6_min_distance,
                    calculation_version = EXCLUDED.calculation_version,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                user_id,
                Json(clean_json_data(power_curve)),
                Json(clean_json_data(running_curve)),
                best_20_min_power,
                best_6_min_distance,
            ))
        conn.commit()
    finally:
        conn.close()


def load_curve_cache(username):
    user_id = get_user_id(username)
    if user_id is None:
        return None
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                  SELECT power_curve, running_curve, best_20_min_power,
                      best_6_min_distance, calculation_version
                FROM curve_cache WHERE user_id = %s
            """, (user_id,))
            row = cur.fetchone()
            if not row:
                print("Curve cache: no row found")
                return None
            print(
                "Loaded curve cache:",
                "power_points=",len(row[0] or []),
                "running_points=",len(row[1] or []),
                "running_distances=",[point.get("distance") for point in (row[1] or [])],
            )
            return {
                "power_curve": row[0] or [],
                "running_curve": row[1] or [],
                "best_20_min_power": row[2],
                "best_6_min_distance": row[3],
                "calculation_version": row[4],
            }
    finally:
        conn.close()


def save_power_efforts(username, efforts):
    user_id = get_user_id(username)
    if user_id is None:
        raise ValueError("User does not exist.")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO power_efforts
                    (user_id, activity_id, duration_seconds, best_power)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, activity_id, duration_seconds)
                DO UPDATE SET best_power = EXCLUDED.best_power
            """, [
                (user_id, int(row["activity_id"]), int(row["duration"]), float(row["value"]))
                for row in efforts
            ])
        conn.commit()
    finally:
        conn.close()


def load_power_efforts(username):
    user_id = get_user_id(username)
    if user_id is None:
        return []
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT activity_id, duration_seconds, best_power
                FROM power_efforts WHERE user_id = %s
            """, (user_id,))
            return [
                {"activity_id": row[0], "duration": row[1], "value": row[2]}
                for row in cur.fetchall()
            ]
    finally:
        conn.close()


def save_running_efforts(username, efforts):
    user_id = get_user_id(username)
    if user_id is None:
        raise ValueError("User does not exist.")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO running_efforts
                    (user_id, activity_id, distance_meters, best_speed)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, activity_id, distance_meters)
                DO UPDATE SET best_speed = EXCLUDED.best_speed
            """, [
                (user_id, int(row["activity_id"]), float(row["distance"]), float(row["speed"]))
                for row in efforts
            ])
        conn.commit()
    finally:
        conn.close()


def load_running_efforts(username):
    user_id = get_user_id(username)
    if user_id is None:
        return []
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT activity_id, distance_meters, best_speed
                FROM running_efforts WHERE user_id = %s
            """, (user_id,))
            return [
                {"activity_id": row[0], "distance": row[1], "speed": row[2]}
                for row in cur.fetchall()
            ]
    finally:
        conn.close()


def load_training_test_status(username, sport, goal):
    user_id = get_user_id(username)
    if user_id is None:
        return {"answered": False, "done": False}
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT running_test_done, cycling_test_done,
                       running_test_answered, cycling_test_answered,
                       running_goal, cycling_goal
                FROM training_test_status WHERE user_id = %s
            """, (user_id,))
            row = cur.fetchone()
            if not row:
                return {"answered": False, "done": False}
            index = 0 if sport == "Running" else 1
            answered_index = 2 if sport == "Running" else 3
            goal_index = 4 if sport == "Running" else 5
            matches_goal = row[goal_index] == goal
            return {
                "answered": bool(row[answered_index]) and matches_goal,
                "done": bool(row[index]) and matches_goal,
            }
    finally:
        conn.close()


def save_training_test_status(username, sport, goal, done):
    user_id = get_user_id(username)
    if user_id is None:
        raise ValueError("User does not exist.")
    column = "running_test_done" if sport == "Running" else "cycling_test_done"
    answered_column = "running_test_answered" if sport == "Running" else "cycling_test_answered"
    goal_column = "running_goal" if sport == "Running" else "cycling_goal"
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                INSERT INTO training_test_status (user_id, {column}, {answered_column}, {goal_column}, updated_at)
                VALUES (%s, %s, TRUE, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE SET
                    {column} = EXCLUDED.{column},
                    {answered_column} = TRUE,
                    {goal_column} = EXCLUDED.{goal_column},
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, bool(done), goal))
        conn.commit()
    finally:
        conn.close()