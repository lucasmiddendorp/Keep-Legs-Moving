import os
os.environ["SILENCE_TOKEN_WARNINGS"] = "true"

import pandas as pd
import numpy as np
from stravalib.client import Client
from helpers.database import (
    load_activity_cache,
    load_power_stream_cache,
    save_activity_cache,
    save_power_stream_cache,
    load_running_stream_cache,
    save_running_stream_cache,
    load_curve_cache,
    save_curve_cache,
    load_power_efforts,
    save_power_efforts,
    load_running_efforts,
    save_running_efforts,
)
from Strava.strava_user import get_user_settings
from helpers.thresholds import (
    CURVE_CACHE_VERSION,
    build_power_curve,
    build_running_curve,
    build_power_efforts,
    build_running_efforts,
    best_20_min_cycling,
    best_6_min_running,
)

ACTIVITY_COLUMNS = [
    "id",
    "date",
    "type",
    "distance",
    "moving_time",
    "total_elevation_gain",
    "average_speed",
    "average_heartrate",
    "max_heartrate",
    "average_watts",
    "weighted_average_watts",
    "trainer",
    "gear_id",
    "stress",
    "IF",
    "average_pace",
    "distance_km",
    "speed_kmh",
    "time_z1_hr",
    "time_z2_hr",
    "time_z3_hr",
    "time_z4_hr",
    "time_z5_hr",
    "time_z6_hr",
    "time_z1_power",
    "time_z2_power",
    "time_z3_power",
    "time_z4_power",
    "time_z5_power",
    "time_z6_power",
    "time_z1_pace",
    "time_z2_pace",
    "time_z3_pace",
    "time_z4_pace",
    "time_z5_pace",
    "time_z6_pace",
]

def get_user_client(access_token):
    client=Client()
    client.access_token=access_token
    return client

def activity_to_dict(activity):
    start_date=pd.to_datetime(activity.start_date,utc=True,errors="coerce") if activity.start_date else pd.NaT
    activity_type=activity.type.name if hasattr(activity.type,"name") else str(activity.type)
    return {
        "id":activity.id,
        "date":start_date.tz_localize(None) if pd.notna(start_date) else None,
        "type":activity_type,
        "distance":float(activity.distance) if activity.distance else None,
        "moving_time":int(activity.moving_time) if activity.moving_time else None,
        "total_elevation_gain":float(activity.total_elevation_gain) if activity.total_elevation_gain else None,
        "average_speed":float(activity.average_speed) if activity.average_speed else None,
        "average_watts":float(activity.average_watts) if getattr(activity,"average_watts",None) else None,
        "weighted_average_watts":float(activity.weighted_average_watts) if getattr(activity,"weighted_average_watts",None) else None,
        "trainer":activity.trainer,
        "gear_id":activity.gear_id,
    }

def fetch_activities(access_token,after_date=None):
    client=get_user_client(access_token)
    activities=[]
    for activity in client.get_activities(after=after_date):
        try:
            data=activity_to_dict(activity)
            if data["date"] is not None:
                activities.append(data)
        except Exception as e:
            print("Skipping activity:",activity.id,e)
    df=pd.DataFrame(activities)
    if df.empty:
        return pd.DataFrame(columns=ACTIVITY_COLUMNS)
    df["date"]=pd.to_datetime(df["date"],errors="coerce")
    df=df.dropna(subset=["date"])
    return df


def update_activity_cache(username,access_token):
    stored_activities = load_activity_cache(username)

    if not stored_activities:
        print("Downloading all activities...")
        df=fetch_activities(access_token)
        new_df=df.copy()
    else:
        print("Loading activity cache...")

        try:
            df=pd.DataFrame(stored_activities)
        except Exception as e:
            print("Could not read activity cache:",e)
            df=pd.DataFrame(columns=ACTIVITY_COLUMNS)

        df["date"]=pd.to_datetime(df["date"],errors="coerce")
        df=df.dropna(subset=["date"])

        latest=df["date"].max() if not df.empty else None

        print("Latest cached activity:",latest)

        if latest is not None:
            # stravalib expects a datetime object, not a Unix timestamp
            after=latest.to_pydatetime()

            # Make sure it is timezone-aware
            if after.tzinfo is None:
                after=after.replace(tzinfo=pd.Timestamp.utcnow().tzinfo)

            print("Requesting activities after:",after)

        else:
            after=None
            print("No cached date found, downloading all activities.")

        new_df=fetch_activities(
            access_token,
            after
        )

        print("Activities returned by Strava:",len(new_df))

        if not new_df.empty:
            df=pd.concat(
                [df,new_df],
                ignore_index=True
            )

            df=df.drop_duplicates(
                "id",
                keep="last"
            )

    for column in ACTIVITY_COLUMNS:
        if column not in df:
            df[column]=np.nan
        if column not in new_df:
            new_df[column]=np.nan

    # Derived fields
    df["distance_km"]=df["distance"]/1000
    df["speed_kmh"]=df["average_speed"]*3.6
    new_df["distance_km"]=new_df["distance"]/1000
    new_df["speed_kmh"]=new_df["average_speed"]*3.6

    print("Final activity count:",len(df))
    print("New activity count:",len(new_df))

    return df,new_df

def fetch_power_stream(access_token,activity_id,activity_type=None,has_power=False):
    client=get_user_client(access_token)
    try:
        is_running = str(activity_type or "").lower() in {
            "run",
            "trailrun",
            "treadmill",
        }
        stream_types=["time","moving","heartrate","velocity_smooth","distance"]
        if not is_running and has_power:
            stream_types.append("watts")
        streams=client.get_activity_streams(
            activity_id,
            types=stream_types,
            resolution="high",
            series_type="time"
        )
        data={}
        for key in ["time","moving","watts","heartrate","velocity_smooth","distance"]:
            stream=streams.get(key)
            data[key]=stream.data if stream else []
        velocity_values=pd.to_numeric(
            data["velocity_smooth"],errors="coerce"
        )
        if not np.isfinite(velocity_values).any():
            velocity_stream=streams.get("velocity")
            data["velocity_smooth"]=(
                velocity_stream.data if velocity_stream else []
            )
        max_len=max(len(x) for x in data.values())
        for key in data:
            data[key]+= [np.nan]*(max_len-len(data[key]))
        velocity_values=pd.to_numeric(
            data["velocity_smooth"],errors="coerce"
        )
        if (not np.isfinite(velocity_values).any()
                and data["distance"] and data["time"]):
            distance=pd.Series(
                pd.to_numeric(data["distance"],errors="coerce")
            )
            elapsed=pd.Series(
                pd.to_numeric(data["time"],errors="coerce")
            )
            distance_delta=distance.diff()
            elapsed_delta=elapsed.diff()
            derived_speed=distance_delta.div(elapsed_delta.where(elapsed_delta>0))
            if len(derived_speed)>1:
                derived_speed.iloc[0]=derived_speed.iloc[1]
            data["velocity_smooth"]=derived_speed.tolist()
        df=pd.DataFrame(data)
        if df.empty:
            return None
        df["activity_id"]=activity_id
        df["timepoint"]=df.index
        columns=["activity_id","timepoint","time","moving","heartrate"]
        if not is_running and has_power:
            columns.insert(4,"watts")
        if is_running:
            columns.extend(["velocity_smooth","distance"])
        return df[columns]
    except Exception as e:
        print("Power stream error",activity_id,e)
        return None


def calculate_hr_zones(stream_df,max_hr):
    from helpers.metrics import HR_ZONES
    hr=pd.to_numeric(stream_df["heartrate"],errors="coerce")

    if hr.notna().sum()==0:
        return {
            "time_z1_hr":np.nan,
            "time_z2_hr":np.nan,
            "time_z3_hr":np.nan,
            "time_z4_hr":np.nan,
            "time_z5_hr": np.nan,
            "time_z6_hr":np.nan
        }

    if max_hr <= 0:
        return {"time_z1_hr": 0, "time_z2_hr": 0, "time_z3_hr": 0, "time_z4_hr": 0, "time_z5_hr":0, "time_z6_hr":0}

    hr_percent = hr / max_hr
    z1=((hr_percent>=HR_ZONES["Recovery"]["min"])&(hr_percent<HR_ZONES["Recovery"]["max"])).sum()
    z2=((hr_percent>=HR_ZONES["Endurance"]["min"])&(hr_percent<HR_ZONES["Endurance"]["max"])).sum()
    z3=((hr_percent>=HR_ZONES["Tempo"]["min"])&(hr_percent<HR_ZONES["Tempo"]["max"])).sum()
    z4=((hr_percent>=HR_ZONES["Threshold"]["min"])&(hr_percent<HR_ZONES["Threshold"]["max"])).sum()
    z5=((hr_percent>=HR_ZONES["VO2max"]["min"])&(hr_percent<HR_ZONES["VO2max"]["max"])).sum()
    z6=((hr_percent>=HR_ZONES["Anaerobic"]["min"])).sum()

    return {
        "time_z1_hr":int(z1),
        "time_z2_hr":int(z2),
        "time_z3_hr":int(z3),
        "time_z4_hr":int(z4),
        "time_z5_hr":int(z5),
        "time_z6_hr":int(z6)
    }

def calculate_power_zones(stream_df,ftp,sport="Cycling"):
    from helpers.metrics import get_zone_definitions
    zone_definitions = get_zone_definitions(sport)
    watts=pd.to_numeric(stream_df["watts"],errors="coerce")

    if watts.notna().sum()==0 or ftp<=0:
        return {
            "time_z1_power":np.nan,
            "time_z2_power":np.nan,
            "time_z3_power":np.nan,
            "time_z4_power":np.nan,
            "time_z5_power":np.nan,
            "time_z6_power":np.nan
        }

    intensity = watts / ftp
    z1=((intensity>=zone_definitions["Recovery"]["min"])&(intensity<zone_definitions["Recovery"]["max"])).sum()
    z2=((intensity>=zone_definitions["Endurance"]["min"])&(intensity<zone_definitions["Endurance"]["max"])).sum()
    z3=((intensity>=zone_definitions["Tempo"]["min"])&(intensity<zone_definitions["Tempo"]["max"])).sum()
    z4=((intensity>=zone_definitions["Threshold"]["min"])&(intensity<zone_definitions["Threshold"]["max"])).sum()
    z5=((intensity>=zone_definitions["VO2max"]["min"])&(intensity<zone_definitions["VO2max"]["max"])).sum()
    z6=((intensity>=zone_definitions["Anaerobic"]["min"])).sum()

    return {
        "time_z1_power":int(z1),
        "time_z2_power":int(z2),
        "time_z3_power":int(z3),
        "time_z4_power":int(z4),
        "time_z5_power":int(z5),
        "time_z6_power":int(z6)
    }

def calculate_pace_zones(stream_df,threshold_pace):
    from helpers.metrics import get_zone_definitions, get_training_zone
    speed=pd.to_numeric(stream_df["velocity_smooth"],errors="coerce")
    if speed.notna().sum()==0 or threshold_pace<=0:
        return {f"time_z{index}_pace":np.nan for index in range(1,7)}

    pace=1000/(speed*60)
    intensity=threshold_pace/pace
    zone_definitions=get_zone_definitions("Running")
    zone_times={f"time_z{index}_pace":0 for index in range(1,7)}
    for zone_index,zone_name in enumerate(zone_definitions,1):
        zone_times[f"time_z{zone_index}_pace"] = int(
            ((intensity>=zone_definitions[zone_name]["min"])
             &(intensity<zone_definitions[zone_name]["max"])).sum()
        )
    return zone_times

def update_running_stream_cache(username,access_token,activities):
    stored_streams=load_running_stream_cache(username)
    stream_df=pd.DataFrame(stored_streams or [])
    cached_ids=set()
    if not stream_df.empty and "activity_id" in stream_df:
        for activity_id, group in stream_df.groupby("activity_id"):
            if pd.to_numeric(group.get("velocity_smooth"),errors="coerce").notna().any():
                cached_ids.add(int(activity_id))
    running_activities=activities[
        activities["type"].astype(str).str.contains("Run|TrailRun|Treadmill",case=False,regex=True)
    ]
    streams=[]
    for _,row in running_activities.iterrows():
        activity_id=int(row["id"])
        if activity_id in cached_ids:
            continue
        stream=fetch_power_stream(access_token,activity_id,row.get("type"))
        if stream is not None:
            streams.append(stream.drop(columns=["watts"],errors="ignore"))
    if streams:
        stream_df=pd.concat([stream_df,*streams],ignore_index=True)
        stream_df=stream_df.drop_duplicates(
            subset=["activity_id","timepoint"],keep="last"
        )
        save_running_stream_cache(username,stream_df)
    new_streams=(
        pd.concat(streams,ignore_index=True)
        if streams
        else stream_df.iloc[0:0].copy()
    )
    return new_streams, bool(streams)

def update_power_stream_cache(username,access_token,activities):
    stored_streams=load_power_stream_cache(username)
    if stored_streams:
        power_df=pd.DataFrame(stored_streams)
    else:
        power_df=pd.DataFrame()

    if not power_df.empty and "activity_id" in power_df.columns:
        cached_ids=set(pd.to_numeric(power_df["activity_id"],errors="coerce").dropna().astype(int))
    else:
        cached_ids=set()

    cache_changed=False
    if "watts" in power_df and not power_df["watts"].notna().any():
        power_df=power_df.drop(columns=["watts"])
        cache_changed=True

    streams=[]
    for _,row in activities.iterrows():
        activity_id=int(row["id"])
        activity_type=str(row.get("type","")).lower()
        if "run" in activity_type or "treadmill" in activity_type or activity_id in cached_ids:
            continue

        print("DEBUG: fetching streams for activity:",activity_id,activity_type)

        has_power=bool(
            pd.notna(row.get("weighted_average_watts"))
            or pd.notna(row.get("average_watts"))
        )
        stream=fetch_power_stream(
            access_token,
            activity_id,
            row.get("type"),
            has_power=has_power,
        )
        if stream is not None:
            stream=stream.drop(columns=["velocity_smooth","distance"],errors="ignore")

        if stream is not None:
            print(
                "DEBUG: fetched",
                len(stream),
                "rows | watts:",
                stream["watts"].notna().sum() if "watts" in stream else 0,
            )
            streams.append(stream)

    if streams:
        power_df=pd.concat(
            [power_df,*streams],
            ignore_index=True
        )

        power_df=power_df.drop_duplicates(
            subset=["activity_id","timepoint"],
            keep="last",
        )

        # Make sure all expected columns exist.
        for column in [
            "activity_id",
            "timepoint",
            "time",
            "moving",
            "heartrate",
            "velocity_smooth",
            "distance",
        ]:
            if column not in power_df.columns:
                power_df[column]=np.nan

        if "watts" in power_df and not power_df["watts"].notna().any():
            power_df=power_df.drop(columns=["watts"])
            cache_changed=True

        save_power_stream_cache(username,power_df)

    new_streams=(
        pd.concat(streams,ignore_index=True)
        if streams
        else power_df.iloc[0:0].copy()
    )
    return new_streams, bool(streams)

def update_hr_zones_from_streams(username,activities,max_hr,threshold_pace=5.0):
    power_streams=load_power_stream_cache(username) or []
    running_streams=load_running_stream_cache(username) or []
    if not power_streams and not running_streams:
        return activities
    power_df=pd.DataFrame(power_streams)
    running_df=pd.DataFrame(running_streams)
    for activity_id in activities["id"]:
        activity_type=str(activities.loc[activities["id"]==activity_id,"type"].iloc[0]).lower()
        source_df=running_df if activity_type in {"run","trailrun","treadmill"} else power_df
        stream=source_df[source_df["activity_id"]==activity_id] if not source_df.empty else pd.DataFrame()
        if stream.empty:
            continue
        if activity_type in {"run","trailrun","treadmill"} and "velocity_smooth" in stream:
            zones=calculate_pace_zones(stream,threshold_pace)
        else:
            zones=calculate_hr_zones(stream,max_hr)
        for key,value in zones.items():
            activities.loc[activities["id"]==activity_id,key]=value
    return activities

def update_power_zones_from_streams(username,activities,ftp,sport="Cycling"):
    stored_streams = load_power_stream_cache(username)
    if not stored_streams:
        return activities
    power_df=pd.DataFrame(stored_streams)
    for activity_id in activities["id"]:
        stream=power_df[power_df["activity_id"]==activity_id]
        if stream.empty:
            continue
        activity_sport = activities.loc[activities["id"] == activity_id, "sport"].iloc[0] if "sport" in activities.columns else sport
        zones=calculate_power_zones(stream,ftp,activity_sport)
        for key,value in zones.items():
            activities.loc[activities["id"]==activity_id,key]=value
    return activities

def calculate_hr_stress(row):
    zones={
        "time_z1_hr":0.55,
        "time_z2_hr":0.75,
        "time_z3_hr":0.85,
        "time_z4_hr":1.0,
        "time_z5_hr":1.
    }
    stress=0
    for zone,IF in zones.items():
        value=row.get(zone,0)
        if pd.notna(value):
            stress+=value*(IF**2)
    return stress/3600*100

def calculate_activity_stress(df,ftp,max_hr,threshold_pace):
    df=df.copy()
    df["moving_time"]=pd.to_numeric(df["moving_time"],errors="coerce")
    df["average_speed"]=pd.to_numeric(df["average_speed"],errors="coerce")
    df["weighted_average_watts"] = pd.to_numeric(df["weighted_average_watts"],errors="coerce")
    hours=df["moving_time"]/3600
    df["stress"]=0.0
    df["IF"]=0.4

    df["average_pace"]=np.where(df["average_speed"]>0,1000/(df["average_speed"]*60),np.nan)

    activity_type=df["type"].fillna("").astype(str)
    cycling_mask=activity_type.str.contains("Ride|VirtualRide|GravelRide|MountainBikeRide|Handcycle|Velomobile",case=False,regex=True) & ~activity_type.str.contains("EBikeRide",case=False,na=False)
    running_mask=activity_type.str.contains("Run|TrailRun|Treadmill",case=False,regex=True)

    power_mask = cycling_mask & df["weighted_average_watts"].notna()
    df.loc[power_mask,"IF"] = df.loc[power_mask,"weighted_average_watts"] / ftp

    running_pace_mask = running_mask & df["time_z1_pace"].notna()
    hr_mask = (~power_mask) & (~running_pace_mask) & df["time_z1_hr"].notna()
    df.loc[hr_mask,"stress"] = df.loc[hr_mask].apply(calculate_hr_stress, axis=1)

    pace_mask = (~power_mask) & running_pace_mask & df["average_pace"].notna()
    df.loc[pace_mask,"IF"] = threshold_pace / df.loc[pace_mask,"average_pace"]

    # Power and pace stress
    if_mask = power_mask | pace_mask
    df.loc[if_mask,"IF"] = df.loc[if_mask,"IF"].clip(0.2,1.5)
    df.loc[if_mask,"stress"] = hours[if_mask] * (df.loc[if_mask,"IF"]**2) * 100

    # No data fallback
    fallback_mask = (~power_mask) & (~hr_mask) & (~pace_mask)
    df.loc[fallback_mask,"IF"] = 0.4
    df.loc[fallback_mask,"stress"] = hours[fallback_mask] * (0.4**2) * 100
    return df


def update_strava_data(username,access_token):
    print("="*60)
    print("STARTING STRAVA SYNC")
    print("Username:",username)
    print("Access token present:",bool(access_token))
    print("="*60)

    try:
        print("[1/7] Loading/updating activity cache...")

        activities,new_activities=update_activity_cache(
            username,
            access_token
        )

        print(
            "[1/7] Activity cache loaded successfully."
            f" Total activities: {len(activities)}"
            f" | New activities: {len(new_activities)}"
        )

        if not activities.empty:
            print(
                f"[2/7] Updating activity streams for "
                f"{len(activities)} activities..."
            )

            running_streams,running_changed=update_running_stream_cache(username,access_token,activities)
            power_streams,power_changed=update_power_stream_cache(
                username,
                access_token,
                activities
            )
            if running_changed:
                save_running_efforts(
                    username,
                    build_running_efforts(running_streams),
                )
            if power_changed:
                save_power_efforts(
                    username,
                    build_power_efforts(power_streams),
                )
            curve_cache=load_curve_cache(username)
            if (
                running_changed
                or power_changed
                or curve_cache is None
                or curve_cache.get("calculation_version") != CURVE_CACHE_VERSION
            ):
                power_efforts=load_power_efforts(username)
                running_efforts=load_running_efforts(username)
                if not power_efforts:
                    power_records=load_power_stream_cache(username) or []
                    power_efforts=build_power_efforts(power_records)
                    save_power_efforts(username,power_efforts)
                if not running_efforts:
                    running_records=load_running_stream_cache(username) or []
                    running_efforts=build_running_efforts(running_records)
                    save_running_efforts(username,running_efforts)
                save_curve_cache(
                    username,
                    build_power_curve(power_efforts),
                    build_running_curve(running_efforts),
                    best_20_min_cycling(power_efforts),
                    best_6_min_running(running_efforts),
                )

            print("[2/7] Activity streams updated successfully.")

        else:
            print("[2/7] No activities. Skipping power streams.")

        print("[3/7] Loading user settings...")

        settings=get_user_settings(username)

        print("[3/7] User settings loaded.")
        print("FTP:",settings.get("ftp",200))
        print("Max HR:",settings.get("max_hr",190))
        print("Threshold pace:",settings.get("threshold_pace",5))

        print("[4/7] Updating HR zones...")

        activities=update_hr_zones_from_streams(
            username,
            activities,
            settings.get("max_hr",190),
            settings.get("threshold_pace",5),
        )

        print("[4/7] HR zones updated successfully.")

        print("[5/7] Updating power zones...")

        activities=update_power_zones_from_streams(
            username,
            activities,
            settings.get("ftp",200)
        )

        print("[5/7] Power zones updated successfully.")

        print("[6/7] Calculating activity stress...")

        activities=calculate_activity_stress(
            activities,
            ftp=settings.get("ftp",200),
            max_hr=settings.get("max_hr",190),
            threshold_pace=settings.get("threshold_pace",5)
        )

        print("[6/7] Activity stress calculated successfully.")

        print("[7/7] Saving activity cache...")

        if activities.empty:
            raise ValueError(
                "Strava returned no activities, so no activity data was saved."
            )
        save_activity_cache(username, activities)

        saved_activities = load_activity_cache(username)
        if not saved_activities:
            raise RuntimeError(
                "Activity data was saved but could not be read back from PostgreSQL."
            )

        print("[6/6] Activity cache saved successfully.")
        print("Total activities:",len(activities))
        print("="*60)
        print("STRAVA SYNC COMPLETE")
        print("="*60)

        return activities,new_activities

    except Exception as e:
        print("="*60)
        print("STRAVA SYNC FAILED")
        print("Error type:",type(e).__name__)
        print("Error:",str(e))
        print("="*60)

        import traceback
        traceback.print_exc()

        raise