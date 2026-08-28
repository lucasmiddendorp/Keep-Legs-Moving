import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor, Json


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