import os
os.environ["SILENCE_TOKEN_WARNINGS"] = "true"
import pandas as pd
import numpy as np
from stravalib.client import Client
from stravalib.exc import Fault, RateLimitExceeded, RateLimitTimeout
from helpers.debug import debug_error, debug_log, show_debug_log, clear_debug_log
from helpers.database import load_activity_cache, save_activity_cache
from Strava.strava_user import get_user_settings
from datetime import datetime, timedelta, timezone

ACTIVITY_COLUMNS = [
    "id",
    "date",
    "type",
    "sport",
    "distance",
    "moving_time",
    "total_elevation_gain",
    "average_speed",
    "average_heartrate",
    "max_heartrate",
    "has_heartrate",
    "average_watts",
    "weighted_average_watts",
    "trainer",
    "gear_id",
    "stress",
    "IF",
    "average_pace",
    "distance_km",
    "speed_kmh",
    "power_0_50",
    "power_50_100",
    "power_100_150",
    "power_150_200",
    "power_200_250",
    "power_250_300",
    "power_300_350",
    "power_350_400",
    "power_400_450",
    "power_450_plus",
    "hr_z1",
    "hr_z2",
    "hr_z3",
    "hr_z4",
    "hr_z5",
    "zones_status",
]

POWER_BUCKET_COLUMNS = [
    "power_0_50",
    "power_50_100",
    "power_100_150",
    "power_150_200",
    "power_200_250",
    "power_250_300",
    "power_300_350",
    "power_350_400",
    "power_400_450",
    "power_450_plus",
]

HR_ZONE_COLUMNS = [
    "hr_z1",
    "hr_z2",
    "hr_z3",
    "hr_z4",
    "hr_z5",
]

HR_ZONE_IF = {
    "hr_z1": 0.55,
    "hr_z2": 0.70,
    "hr_z3": 0.83,
    "hr_z4": 0.94,
    "hr_z5": 1.00,
}

ZONE_COLUMNS = POWER_BUCKET_COLUMNS + HR_ZONE_COLUMNS

def normalize_strava_value(value):
    if value is None:
        return None
    if hasattr(value, "name"):
        value = value.name
    elif hasattr(value, "value"):
        value = value.value
    elif hasattr(value, "root"):
        value = value.root
    return str(value).replace("root='", "").replace("'", "")


def activity_to_dict(activity):
    sport = getattr(activity, "sport_type", None)
    if sport is None:
        sport = getattr(activity, "type", None)
    activity_type = getattr(activity, "type", None)
    return {
        "id": getattr(activity, "id", None),
        "date": getattr(activity, "start_date", None),
        "type": normalize_strava_value(activity_type),
        "sport": normalize_strava_value(sport),
        "distance": getattr(activity, "distance", None),
        "moving_time": getattr(activity, "moving_time", None),
        "total_elevation_gain": getattr(activity, "total_elevation_gain", None),
        "average_speed": getattr(activity, "average_speed", None),
        "average_heartrate": getattr(activity, "average_heartrate", None),
        "max_heartrate": getattr(activity, "max_heartrate", None),
        "has_heartrate": getattr(activity, "has_heartrate", None),
        "average_watts": getattr(activity, "average_watts", None),
        "weighted_average_watts": getattr(activity, "weighted_average_watts", None),
        "trainer": getattr(activity, "trainer", None),
        "gear_id": getattr(activity, "gear_id", None),
        "stress": np.nan,
        "IF": np.nan,
        "average_pace": np.nan,
        "distance_km": np.nan,
        "speed_kmh": np.nan,
    }


class StravaRateLimitReached(Exception):
    def __init__(self, reset_at=None, reason="", limit_type="15_min", remaining=None):
        self.reset_at = reset_at
        self.reason = reason
        self.limit_type = limit_type
        self.remaining = remaining
        super().__init__(reason)


class StravaZonesUnavailable(Exception):
    pass

def _rate_limit_state(client):
    response = getattr(getattr(client, "protocol", None), "last_response", None)
    if response is None:
        return None
    headers = response.headers
    usage = headers.get("X-ReadRateLimit-Usage") or headers.get("X-RateLimit-Usage")
    limit = headers.get("X-ReadRateLimit-Limit") or headers.get("X-RateLimit-Limit")
    if not usage or not limit:
        return None
    try:
        used = [int(value.strip()) for value in usage.split(",")[:2]]
        limits = [int(value.strip()) for value in limit.split(",")[:2]]
        return {
            "remaining_15_min": limits[0] - used[0],
            "remaining_daily": limits[1] - used[1],
        }
    except (ValueError, IndexError):
        return None


def _next_quarter_hour():
    now = datetime.now(timezone.utc)
    minutes = 15 - (now.minute % 15)
    return (now + timedelta(minutes=minutes)).replace(second=0, microsecond=0)


def check_strava_rate_limit(client, safety_margin=5):
    try:
        state = _rate_limit_state(client)
        if state is None:
            return
        if state["remaining_daily"] <= safety_margin:
            raise StravaRateLimitReached(
                reason="Strava daily read limit is nearly exhausted.",
                limit_type="daily",
                remaining=state["remaining_daily"],
            )
        if state["remaining_15_min"] <= safety_margin:
            raise StravaRateLimitReached(
                reset_at=_next_quarter_hour(),
                reason="Strava 15-minute read limit is nearly exhausted.",
                limit_type="15_min",
                remaining=state["remaining_15_min"],
            )
    except StravaRateLimitReached:
        raise
    except Exception as e:
        debug_log(f"Could not inspect Strava rate-limit headers: {e}")

def fetch_activities(client):
    try:
        activities = []
        check_strava_rate_limit(client)
        activities.extend(list(client.get_activities(limit=100)))
        return activities
    except (RateLimitExceeded, RateLimitTimeout) as e:
        state = _rate_limit_state(client) or {}
        daily = state.get("remaining_daily", 1) <= 0
        raise StravaRateLimitReached(
            reset_at=None if daily else _next_quarter_hour(),
            reason=str(e),
            limit_type="daily" if daily else "15_min",
            remaining=state.get("remaining_15_min"),
        )
    except Exception as e:
        debug_error(f"Error fetching activities: {e}")
        return []

def update_activity_cache(client, username, progress_callback=None):
    try:
        df = load_activity_cache(username)
        if df is None:
            df = pd.DataFrame(columns=ACTIVITY_COLUMNS)
        elif not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)
        for column in ACTIVITY_COLUMNS:
            if column not in df.columns:
                df[column] = np.nan
        for column in ZONE_COLUMNS:
            if column not in df.columns:
                df[column] = np.nan
        if "zones_synced" not in df.columns:
            df["zones_synced"] = np.nan
        if "zones_status" not in df.columns:
            df["zones_status"] = None
        if "id" in df.columns:
            df = df.drop_duplicates(subset=["id"], keep="last").reset_index(drop=True)
        activities = fetch_activities(client)
        if not activities:
            if progress_callback:
                progress_callback("Found 0 new activities. Syncing...", 0.0)
            return df, pd.DataFrame(columns=ACTIVITY_COLUMNS)
        new_rows = [activity_to_dict(activity) for activity in activities]
        new_df = pd.DataFrame(new_rows)
        existing_ids = set(df["id"].dropna()) if "id" in df.columns else set()
        new_activities = new_df[~new_df["id"].isin(existing_ids)].copy()
        if progress_callback:
            progress_callback(
                f"Found {len(new_activities)} new activities. Syncing...",
                0.0,
            )
        new_df["zones_synced"] = np.nan
        new_df["zones_status"] = None
        old_zone_values = (
            df.set_index("id")[ZONE_COLUMNS]
            if not df.empty and "id" in df.columns
            else pd.DataFrame()
        )
        old_zone_states = (
            df.set_index("id")["zones_synced"]
            if not df.empty and "id" in df.columns
            else pd.Series(dtype=object)
        )
        old_zone_statuses = (
            df.set_index("id")["zones_status"]
            if not df.empty and "id" in df.columns
            else pd.Series(dtype=object)
        )
        combined = pd.concat([df, new_df], ignore_index=True, sort=False)
        combined = combined.drop_duplicates(subset=["id"], keep="last")
        for column in ZONE_COLUMNS:
            if not old_zone_values.empty:
                combined[column] = combined[column].fillna(
                    combined["id"].map(old_zone_values[column])
                )
        combined["zones_synced"] = combined["zones_synced"].fillna(
            combined["id"].map(old_zone_states)
        ).fillna(False)
        combined["zones_status"] = combined["zones_status"].fillna(
            combined["id"].map(old_zone_statuses)
        )
        combined["date"] = pd.to_datetime(
            combined["date"],
            errors="coerce",
            utc=True,
        ).dt.tz_localize(None)
        combined["distance"] = pd.to_numeric(combined["distance"], errors="coerce")
        combined["moving_time"] = pd.to_numeric(combined["moving_time"], errors="coerce")
        combined["average_speed"] = pd.to_numeric(combined["average_speed"], errors="coerce")
        combined["distance_km"] = combined["distance"] / 1000
        combined["speed_kmh"] = combined["average_speed"] * 3.6
        for column in ACTIVITY_COLUMNS:
            if column not in combined.columns:
                combined[column] = np.nan
        combined = combined[ACTIVITY_COLUMNS + ["zones_synced"]]
        combined = combined.sort_values("date", ascending=False, na_position="last")
        save_activity_cache(username, combined)
        debug_log(f"Activity summaries updated: {len(new_df)} activities fetched.")
        return combined, new_activities
    except StravaRateLimitReached:
        raise
    except Exception as e:
        debug_error(f"Error updating activity cache: {e}")
        fallback = df if "df" in locals() else pd.DataFrame(columns=ACTIVITY_COLUMNS)
        for column in ACTIVITY_COLUMNS:
            if column not in fallback.columns:
                fallback[column] = np.nan
        return fallback, pd.DataFrame(columns=ACTIVITY_COLUMNS)
def get_activity_zone_data(client,activity_id):
    zone_data={column:np.nan for column in ZONE_COLUMNS}
    try:
        check_strava_rate_limit(client)
        zones=client.get_activity_zones(activity_id)
        check_strava_rate_limit(client)
        for zone in zones:
            zone_type=getattr(zone,"type",None)
            if zone_type is None:
                continue
            zone_type=getattr(zone_type,"root",zone_type)
            zone_type=getattr(zone_type,"value",zone_type)
            zone_type = (
                str(zone_type)
                .lower()
                .replace("root='", "")
                .replace("'", "")
                .replace("_", "")
                .replace("-", "")
            )
            buckets=getattr(zone,"distribution_buckets",None)
            if not buckets:
                continue
            if zone_type=="power":
                for bucket in buckets:
                    minimum=getattr(bucket,"min",None)
                    maximum=getattr(bucket,"max",None)
                    time=float(getattr(bucket,"time",0) or 0)
                    if minimum is None:
                        continue
                    minimum=int(minimum)
                    maximum=int(maximum) if maximum is not None else -1
                    bucket_map={
                        (0,50):"power_0_50",
                        (50,100):"power_50_100",
                        (100,150):"power_100_150",
                        (150,200):"power_150_200",
                        (200,250):"power_200_250",
                        (250,300):"power_250_300",
                        (300,350):"power_300_350",
                        (350,400):"power_350_400",
                        (400,450):"power_400_450",
                        (450,-1):"power_450_plus"
                    }
                    column=bucket_map.get((minimum,maximum))
                    if column:
                        zone_data[column]=time
            elif zone_type in ("heartrate", "heartratezone"):
                for i,bucket in enumerate(buckets[:5]):
                    zone_data[f"hr_z{i+1}"]=float(getattr(bucket,"time",0) or 0)
        return zone_data
    except (RateLimitExceeded,RateLimitTimeout) as e:
        raise StravaRateLimitReached(reason=str(e))
    except StravaRateLimitReached:
        raise
    except Fault as e:
        status_code = getattr(getattr(e, "response", None), "status_code", None)
        if status_code == 402:
            raise StravaZonesUnavailable(str(e))
        debug_error(f"Error fetching zones for activity {activity_id}: {e}")
        return None
    except Exception as e:
        debug_error(f"Error fetching zones for activity {activity_id}: {e}")
        return None

    
def activity_has_hr(row):
    has_heartrate = row.get("has_heartrate")
    if pd.notna(has_heartrate) and str(has_heartrate).lower() == "true":
        return True
    return pd.notna(row.get("average_heartrate")) or pd.notna(row.get("max_heartrate"))


def activity_has_power(row):
    return (
        pd.notna(row.get("average_watts"))
        or pd.notna(row.get("weighted_average_watts"))
    )


def update_activity_zones(client,df,username,progress_callback=None):
    if df is None or df.empty:
        return df, 0, None
    df=df.copy()
    for column in ZONE_COLUMNS:
        if column not in df.columns:
            df[column]=np.nan
    if "zones_synced" not in df.columns:
        df["zones_synced"] = False
    if "zones_status" not in df.columns:
        df["zones_status"] = None
    unavailable_mask = df["zones_status"].eq("unavailable")
    if unavailable_mask.any():
        df.loc[unavailable_mask, ZONE_COLUMNS] = np.nan
    incomplete_count = int((~df["zones_synced"].astype(bool)).sum())
    completed_count = 0
    processed = 0
    synced_through = None
    for index, row in df.iterrows():
        if (
            bool(row.get("zones_synced", False))
            and row.get("zones_status") != "unavailable"
            and activity_has_hr(row)
            and df.loc[index, HR_ZONE_COLUMNS].fillna(0).sum() == 0
        ):
            df.at[index, "zones_synced"] = False
        if bool(row.get("zones_synced", False)):
            continue
        activity_id=df.at[index,"id"]
        if pd.isna(activity_id):
            df.at[index, "zones_synced"] = True
            save_activity_cache(username, df)
            completed_count += 1
            continue
        has_hr = activity_has_hr(row)
        has_power = activity_has_power(row)
        hr_complete = not has_hr or all(pd.notna(row.get(column)) for column in HR_ZONE_COLUMNS)
        power_complete = not has_power or all(pd.notna(row.get(column)) for column in POWER_BUCKET_COLUMNS)
        if hr_complete and power_complete:
            df.at[index, "zones_synced"] = True
            save_activity_cache(username, df)
            processed += 1
            synced_through = row.get("date")
            completed_count += 1
            if progress_callback:
                progress_callback(
                    f"Syncing... {completed_count}/{incomplete_count} activities",
                    completed_count / max(incomplete_count, 1),
                )
            continue
        if not has_hr and not has_power:
            df.at[index, "zones_synced"] = True
            save_activity_cache(username, df)
            processed += 1
            synced_through = row.get("date")
            completed_count += 1
            if progress_callback:
                progress_callback(
                    f"Syncing... {completed_count}/{incomplete_count} activities",
                    completed_count / max(incomplete_count, 1),
                )
            continue
        try:
            zone_data=get_activity_zone_data(client,int(activity_id))
        except StravaRateLimitReached as e:
            save_activity_cache(username,df)
            e.processed = processed
            e.synced_through = synced_through
            raise
        except StravaZonesUnavailable:
            remaining_mask = ~df["zones_synced"].astype(bool)
            df.loc[remaining_mask, ZONE_COLUMNS] = np.nan
            df.loc[remaining_mask, "zones_synced"] = True
            df.loc[remaining_mask, "zones_status"] = "unavailable"
            save_activity_cache(username, df)
            remaining_count = int(remaining_mask.sum())
            processed += remaining_count
            synced_through = row.get("date")
            debug_log(
                "Strava zone endpoint returned HTTP 402. "
                f"Marked {remaining_count} activities as unavailable; "
                "skipping further zone requests."
            )
            completed_count += remaining_count
            if progress_callback:
                progress_callback(
                    "Zone data unavailable from Strava; continuing with stress calculation.",
                    0.9,
                )
            return df, processed, synced_through
        if zone_data is None:
            save_activity_cache(username, df)
            continue
        for column,value in zone_data.items():
            df.at[index,column]=value
        hr_complete = not has_hr or all(
            pd.notna(df.at[index, column]) for column in HR_ZONE_COLUMNS
        )
        power_complete = not has_power or all(
            pd.notna(df.at[index, column]) for column in POWER_BUCKET_COLUMNS
        )
        if not hr_complete or not power_complete:
            save_activity_cache(username, df)
            debug_log(
                f"Incomplete zone response for activity {activity_id}; "
                "leaving it pending for a later sync."
            )
            continue
        df.at[index, "zones_synced"] = True
        save_activity_cache(username,df)
        processed += 1
        synced_through = row.get("date")
        completed_count += 1
        if progress_callback:
            progress_callback(
                f"Syncing... {completed_count}/{incomplete_count} activities",
                completed_count / max(incomplete_count, 1),
            )
        debug_log(f"Zone data saved for activity {activity_id}.")
    return df, processed, synced_through

def calculate_activity_stress(df, ftp, running_threshold_speed=None, max_hr=190):
    df = df.copy()
    df["moving_time"] = pd.to_numeric(df["moving_time"], errors="coerce").fillna(0)
    df["average_speed"] = pd.to_numeric(df["average_speed"], errors="coerce")
    df["average_watts"] = pd.to_numeric(df["average_watts"], errors="coerce")
    df["weighted_average_watts"] = pd.to_numeric(df["weighted_average_watts"], errors="coerce")
    if "average_heartrate" not in df.columns:
        df["average_heartrate"] = np.nan
    df["average_heartrate"] = pd.to_numeric(
        df["average_heartrate"], errors="coerce"
    )
    df["average_pace"] = np.nan
    df["IF"] = np.nan
    df["stress"] = 0.0
    hours = df["moving_time"] / 3600
    cycling_mask = df["sport"].astype(str).str.lower().isin(
        ["ride", "cycling", "virtualride", "ebikeride", "velomobile"]
    )
    running_mask = df["sport"].astype(str).str.lower().isin(
        ["run", "trailrun", "virtualrun"]
    )
    cycling_power_mask = (
        cycling_mask
        & df["weighted_average_watts"].notna()
        & (df["weighted_average_watts"] > 0)
        & (ftp > 0)
    )
    heart_rate_mask = (
        ~cycling_power_mask
        & df["average_heartrate"].notna()
        & (df["average_heartrate"] > 0)
        & (max_hr > 0)
    )
    if cycling_power_mask.any():
        df.loc[cycling_power_mask, "IF"] = (
            df.loc[cycling_power_mask, "weighted_average_watts"] / ftp
        )
        df.loc[cycling_power_mask, "stress"] = (
            hours[cycling_power_mask]
            * df.loc[cycling_power_mask, "IF"] ** 2
            * 100
        )
    if heart_rate_mask.any():
        df.loc[heart_rate_mask, "IF"] = (
            df.loc[heart_rate_mask, "average_heartrate"] / max_hr
        )
        df.loc[heart_rate_mask, "stress"] = (
            hours[heart_rate_mask]
            * df.loc[heart_rate_mask, "IF"] ** 2
            * 100
        )
    running_pace_mask = (
        running_mask
        & df["average_speed"].notna()
        & (df["average_speed"] > 0)
    )
    if running_pace_mask.any():
        df.loc[running_pace_mask, "average_pace"] = (
            1000 / df.loc[running_pace_mask, "average_speed"] / 60
        )
    fallback_mask = df["IF"].isna() & (hours > 0)
    df.loc[fallback_mask, "IF"] = 0.4
    df.loc[fallback_mask, "stress"] = hours[fallback_mask] * 0.4 ** 2 * 100
    return df

def update_strava_data(username=None,access_token=None,progress_callback=None):
    clear_debug_log()
    empty_result = {
        "activities": pd.DataFrame(columns=ACTIVITY_COLUMNS + ["zones_synced"]),
        "rate_limited": False,
        "limit_type": None,
        "synced_through": None,
        "reset_at": None,
        "processed": 0,
        "remaining": None,
    }
    try:
        settings=get_user_settings(username)
        access_token=access_token or settings.get("strava_access_token")
        if not access_token:
            debug_error("No Strava access token found.")
            return empty_result
        client=Client(access_token=access_token)
        debug_log("Starting Strava sync...")
        df, new_activities = update_activity_cache(
            client,
            username,
            progress_callback=progress_callback,
        )
        df, processed, synced_through = update_activity_zones(
            client,
            df,
            username,
            progress_callback=progress_callback,
        )
        if progress_callback:
            progress_callback("Recalculating stress for all activities...", 0.95)
        settings=get_user_settings(username)
        ftp=float(settings.get("ftp",290) or 290)
        threshold_pace=float(settings.get("threshold_pace",5.0) or 5.0)
        max_hr=float(settings.get("max_hr",190) or 190)
        running_threshold_speed=1000 / (threshold_pace * 60)
        df=calculate_activity_stress(df,ftp,running_threshold_speed,max_hr)
        for column in ACTIVITY_COLUMNS + ["zones_synced"]:
            if column not in df.columns:
                df[column] = False if column == "zones_synced" else np.nan
        df=df[ACTIVITY_COLUMNS + ["zones_synced"]]
        save_activity_cache(username,df)
        debug_log(f"Strava sync complete: {len(df)} activities.")
        if progress_callback:
            progress_callback("Stress recalculated. Sync complete.", 1.0)
        show_debug_log()
        state = _rate_limit_state(client) or {}
        return {
            "activities": df,
            "rate_limited": False,
            "limit_type": None,
            "synced_through": synced_through,
            "reset_at": None,
            "processed": processed,
            "remaining": state.get("remaining_15_min"),
        }
    except StravaRateLimitReached as e:
        df=load_activity_cache(username)
        if df is None:
            df=pd.DataFrame(columns=ACTIVITY_COLUMNS + ["zones_synced"])
        elif not isinstance(df, pd.DataFrame):
            df=pd.DataFrame(df)
        debug_log("Strava rate limit reached. Progress has been saved.")
        show_debug_log()
        return {
            "activities": df,
            "rate_limited": True,
            "limit_type": e.limit_type,
            "synced_through": getattr(e, "synced_through", None),
            "reset_at": e.reset_at,
            "processed": getattr(e, "processed", 0),
            "remaining": e.remaining,
        }
    except Exception as e:
        debug_error(f"Strava sync failed: {e}")
        show_debug_log()
        return empty_result