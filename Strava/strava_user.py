import pandas as pd
import streamlit as st
from stravalib.client import Client

from helpers.database import (
    get_user,
    get_user_id,
    get_connection,
)


def get_user_strava(username):
    user_id = get_user_id(username)

    if user_id is None:
        return {"connected": False}

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    athlete_id,
                    access_token,
                    refresh_token,
                    expires_at,
                    connected
                FROM strava_accounts
                WHERE user_id = %s
            """, (user_id,))

            row = cur.fetchone()

            if not row:
                return {"connected": False}

            return {
                "athlete_id": row[0],
                "access_token": row[1],
                "refresh_token": row[2],
                "expires_at": row[3],
                "connected": row[4],
            }

    finally:
        conn.close()


def save_user_strava(username, token):
    user_id = get_user_id(username)

    if user_id is None:
        raise ValueError("User does not exist.")

    athlete = token.get("athlete") if isinstance(token, dict) else None
    athlete_id = None

    if isinstance(athlete, dict):
        athlete_id = athlete.get("id")

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            if athlete_id is None:
                cur.execute(
                    "SELECT athlete_id FROM strava_accounts WHERE user_id = %s",
                    (user_id,),
                )
                existing = cur.fetchone()
                athlete_id = existing[0] if existing else None

            if athlete_id is None:
                raise ValueError("Strava token response did not include an athlete ID.")

            cur.execute("""
                INSERT INTO strava_accounts (
                    user_id,
                    athlete_id,
                    access_token,
                    refresh_token,
                    expires_at,
                    connected
                )
                VALUES (%s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    athlete_id = EXCLUDED.athlete_id,
                    access_token = EXCLUDED.access_token,
                    refresh_token = EXCLUDED.refresh_token,
                    expires_at = EXCLUDED.expires_at,
                    connected = TRUE
            """, (
                user_id,
                athlete_id,
                token["access_token"],
                token["refresh_token"],
                token["expires_at"],
            ))

        conn.commit()

    finally:
        conn.close()


def reset_user_strava(username):
    user_id = get_user_id(username)

    if user_id is None:
        return

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM strava_accounts WHERE user_id = %s",
                (user_id,)
            )

        conn.commit()

    finally:
        conn.close()


def get_user_by_strava_athlete_id(athlete_id):
    if athlete_id is None:
        return None

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.username
                FROM users u
                JOIN strava_accounts s
                    ON s.user_id = u.id
                WHERE s.athlete_id = %s
            """, (athlete_id,))

            row = cur.fetchone()

            return row[0] if row else None

    finally:
        conn.close()


def get_user_settings(username):
    user_id = get_user_id(username)

    if user_id is None:
        return {
            "ftp": 300,
            "threshold_pace": 5.0,
            "max_hr": 190,
            "weight": 70,
            "athlete_level": "Amateur",
            "training_progression": 8,
            "atl_tc": 7,
            "sessions_per_week": None,
        }

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    ftp,
                    max_hr,
                    threshold_hr,
                    threshold_pace,
                    weight,
                    athlete_level,
                    training_progression,
                    atl_tc,
                    sessions_per_week
                FROM user_settings
                WHERE user_id = %s
            """, (user_id,))

            row = cur.fetchone()

            if not row:
                return {
                    "ftp": 300,
                    "threshold_pace": 5.0,
                    "max_hr": 190,
                    "weight": 70,
                    "athlete_level": "Amateur",
                    "training_progression": 8,
                    "atl_tc": 7,
                    "sessions_per_week": None,
                }

            return {
                "ftp": row[0],
                "max_hr": row[1],
                "threshold_hr": row[2],
                "threshold_pace": row[3],
                "weight": row[4],
                "athlete_level": row[5],
                "training_progression": row[6],
                "atl_tc": row[7],
                "sessions_per_week": row[8],
            }

    finally:
        conn.close()


def save_user_settings(
    username,
    ftp=None,
    max_hr=None,
    threshold_pace=None,
    weight=None,
    athlete_level=None,
    atl_tc=None,
    threshold_hr=None,
    training_progression=None,
    sessions_per_week=None,
):
    user_id = get_user_id(username)
    if user_id is None:
        raise ValueError("User does not exist.")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_settings (
                    user_id,
                    ftp,
                    max_hr,
                    threshold_hr,
                    threshold_pace,
                    weight,
                    athlete_level,
                    training_progression,
                    atl_tc,
                    sessions_per_week
                )
                VALUES (
                    %s,
                    COALESCE(%s, 300),
                    COALESCE(%s, 190),
                    %s,
                    COALESCE(%s, 5.0),
                    COALESCE(%s, 70),
                    COALESCE(%s, 'Amateur'),
                    COALESCE(%s, 8),
                    COALESCE(%s, 7),
                    %s
                )
                ON CONFLICT (user_id)
                DO UPDATE SET
                    ftp = CASE WHEN EXCLUDED.ftp != 300 THEN EXCLUDED.ftp ELSE user_settings.ftp END,
                    max_hr = CASE WHEN EXCLUDED.max_hr != 190 THEN EXCLUDED.max_hr ELSE user_settings.max_hr END,
                    threshold_hr = COALESCE(EXCLUDED.threshold_hr, user_settings.threshold_hr),
                    threshold_pace = CASE WHEN EXCLUDED.threshold_pace != 5.0 THEN EXCLUDED.threshold_pace ELSE user_settings.threshold_pace END,
                    weight = CASE WHEN EXCLUDED.weight != 70 THEN EXCLUDED.weight ELSE user_settings.weight END,
                    athlete_level = CASE WHEN EXCLUDED.athlete_level != 'Amateur' THEN EXCLUDED.athlete_level ELSE user_settings.athlete_level END,
                    training_progression = CASE WHEN EXCLUDED.training_progression != 8 THEN EXCLUDED.training_progression ELSE user_settings.training_progression END,
                    atl_tc = CASE WHEN EXCLUDED.atl_tc != 7 THEN EXCLUDED.atl_tc ELSE user_settings.atl_tc END,
                    sessions_per_week = COALESCE(EXCLUDED.sessions_per_week, user_settings.sessions_per_week)
            """, (
                user_id,
                ftp,
                max_hr,
                threshold_hr,
                threshold_pace,
                weight,
                athlete_level,
                training_progression,
                atl_tc,
                sessions_per_week,
            ))
        conn.commit()
    finally:
        conn.close()


def get_training_goal(username):
    user_id = get_user_id(username)

    if user_id is None:
        return {
            "name": None,
            "goal_date": None,
        }

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT name, goal_date, event_distance_km, event_climb_m, event_type, sport
                FROM training_goals
                WHERE user_id = %s
            """, (user_id,))

            row = cur.fetchone()

            if not row:
                return {
                    "name": None,
                    "goal_date": None,
                }

            return {
                "name": row[0],
                "sport": row[5],
                "goal_date": row[1],
                "event_distance_km": row[2],
                "event_climb_m": row[3],
                "event_type": row[4],
            }

    finally:
        conn.close()


def save_training_goal(
    username,
    goal_name,
    goal_date,
    event_distance_km=None,
    event_climb_m=None,
    event_type=None,
    sport=None,
):
    user_id = get_user_id(username)

    if user_id is None:
        raise ValueError("User does not exist.")

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO training_goals (
                    user_id, name, goal_date, event_distance_km,
                    event_climb_m, event_type, sport
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    goal_date = EXCLUDED.goal_date,
                    event_distance_km = EXCLUDED.event_distance_km,
                    event_climb_m = EXCLUDED.event_climb_m,
                    event_type = EXCLUDED.event_type,
                    sport = EXCLUDED.sport
            """, (
                user_id,
                goal_name,
                goal_date,
                event_distance_km,
                event_climb_m,
                event_type,
                sport,
            ))

        conn.commit()

    finally:
        conn.close()


def get_valid_access_token(username):
    strava = get_user_strava(username)

    if not strava.get("connected"):
        raise Exception("Strava account not connected")

    expires_at = strava.get("expires_at")

    if (
        expires_at
        and pd.Timestamp.now().timestamp() < float(expires_at) - 60
    ):
        return strava["access_token"]

    if not strava.get("refresh_token"):
        raise Exception("No Strava refresh token available.")

    client = Client()

    token = client.refresh_access_token(
        client_id=st.secrets["strava"]["CLIENT_ID"],
        client_secret=st.secrets["strava"]["CLIENT_SECRET"],
        refresh_token=strava["refresh_token"],
    )

    save_user_strava(username, token)

    return token["access_token"]


def save_pending_user(username, state):
    user_id = get_user_id(username)

    if user_id is None:
        raise ValueError("User does not exist.")

    conn = get_connection()

    try:
        with conn.cursor() as cur:

            cur.execute("""
                INSERT INTO strava_oauth_pending (
                    state,
                    user_id
                )
                VALUES (%s, %s)
                ON CONFLICT (state)
                DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    created_at = CURRENT_TIMESTAMP
            """, (
                state,
                user_id,
            ))

        conn.commit()

    finally:
        conn.close()


def get_pending_user(state):
    if not state:
        return None

    conn = get_connection()

    try:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT u.username
                FROM strava_oauth_pending p
                JOIN users u
                    ON u.id = p.user_id
                WHERE p.state = %s
            """, (
                state,
            ))

            row = cur.fetchone()

            return row[0] if row else None

    finally:
        conn.close()


def clear_pending_user(state):
    if not state:
        return

    conn = get_connection()

    try:
        with conn.cursor() as cur:

            cur.execute("""
                DELETE FROM strava_oauth_pending
                WHERE state = %s
            """, (
                state,
            ))

        conn.commit()

    finally:
        conn.close()