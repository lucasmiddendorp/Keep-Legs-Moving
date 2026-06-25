import zipfile
import os
import hashlib
import tempfile
import pandas as pd
from fitparse import FitFile

CACHE_FILE = "activities_cache.csv"
POWER_CACHE_FILE = "power_streams.parquet"


def wahoo_activity_id(filename):
    """
    Generate a stable negative integer ID from the filename.
    Negative to avoid any collision with positive Strava IDs.
    """
    return -int(hashlib.md5(os.path.basename(filename).encode()).hexdigest()[:12], 16)


def parse_fit_file(fit_path):
    """
    Parse a single .fit file into:
      - activity_dict  →  matches the columns from activity_to_dict() in strava_client.py
      - power_df       →  matches the power_streams parquet schema (may be None)
    """
    fitfile = FitFile(fit_path)

    sport = "Ride"
    sub_sport = None
    session = {}
    records = []

    for msg in fitfile.get_messages("sport"):
        d = {f.name: f.value for f in msg.fields}
        if "sport" in d:
            sport = str(d["sport"]).replace("_", " ").title()
        if "sub_sport" in d:
            sub_sport = str(d["sub_sport"])

    for msg in fitfile.get_messages("session"):
        for f in msg.fields:
            session[f.name] = f.value

    for msg in fitfile.get_messages("record"):
        records.append({f.name: f.value for f in msg.fields})

    activity_id = wahoo_activity_id(fit_path)
    start_time = session.get("start_time")
    date = start_time.date() if start_time else None
    trainer = sub_sport in {"indoor_cycling", "virtual_activity"} if sub_sport else False

    total_dist   = session.get("total_distance")
    moving_time  = session.get("total_moving_time") or session.get("total_timer_time")
    avg_speed    = session.get("avg_speed")
    elev_gain    = session.get("total_ascent")
    avg_hr       = session.get("avg_heart_rate")
    max_hr       = session.get("max_heart_rate")
    avg_power    = session.get("avg_power")
    norm_power   = session.get("normalized_power")

    activity = {
        # --- Core fields (same as strava_client.py activity_to_dict) ---
        "id":                       activity_id,
        "date":                     date,
        "type":                     sport,
        "distance":                 float(total_dist)  if total_dist  is not None else None,
        "moving_time":              int(moving_time)   if moving_time is not None else None,
        "total_elevation_gain":     float(elev_gain)   if elev_gain   is not None else None,
        "average_speed":            float(avg_speed)   if avg_speed   is not None else None,
        "average_heartrate":        float(avg_hr)      if avg_hr      is not None else None,
        "max_heartrate":            float(max_hr)      if max_hr      is not None else None,
        "average_watts":            float(avg_power)   if avg_power   is not None else None,
        "weighted_average_watts":   float(norm_power)  if norm_power  is not None else None,
        "trainer":                  trainer,
        "gear_id":                  None,
        # --- Derived fields (computed in update_cache in strava_client.py) ---
        "distance_km":  float(total_dist) / 1000 if total_dist else None,
        "speed_kmh":    float(avg_speed)  * 3.6  if avg_speed  else None,
        # --- Extra field to identify source ---
        "source":       "wahoo",
    }

    # --- Power stream (matches power_streams.parquet schema) ---
    power_df = None
    if records:
        df_rec = pd.DataFrame(records)

        # Elapsed time in seconds from activity start
        if "timestamp" in df_rec.columns and start_time is not None:
            try:
                ts = pd.to_datetime(df_rec["timestamp"]).dt.tz_localize(None)
                t0 = pd.Timestamp(start_time).tz_localize(None)
                df_rec["time"] = (ts - t0).dt.total_seconds().astype(int)
            except Exception:
                df_rec["time"] = df_rec.index  # fallback: use row index
        else:
            df_rec["time"] = df_rec.index

        # Moving: True when speed > 0
        if "speed" in df_rec.columns:
            df_rec["moving"] = df_rec["speed"] > 0
        else:
            df_rec["moving"] = None

        power_df = pd.DataFrame({
            "activity_id":  activity_id,
            "timepoint":    df_rec.index,
            "time":         df_rec["time"],
            "moving":       df_rec.get("moving"),
            "watts":        df_rec.get("power"),   # None column if no power data
        })

    return activity, power_df


def load_wahoo_zip(zip_path):
    """
    Read all .fit files from a Wahoo export ZIP and merge them into
    the shared activities CSV and power stream parquet caches.

    Usage:
        df = load_wahoo_zip("wahoo_export.zip")
    """
    activity_rows = []
    power_frames  = []

    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_path, "r") as zf:
            fit_files = [f for f in zf.namelist() if f.lower().endswith(".fit")]
            print(f"Found {len(fit_files)} .fit files in {os.path.basename(zip_path)}")

            for fit_name in fit_files:
                zf.extract(fit_name, path=tmpdir)
                fit_path = os.path.join(tmpdir, fit_name)
                print(f"  Parsing {os.path.basename(fit_name)}...")

                try:
                    activity, power_df = parse_fit_file(fit_path)
                    activity_rows.append(activity)
                    if power_df is not None:
                        power_frames.append(power_df)
                except Exception as e:
                    print(f"  ⚠ Error parsing {fit_name}: {e}")

    if not activity_rows:
        print("No activities parsed.")
        return pd.DataFrame()

    new_df = pd.DataFrame(activity_rows)

    # --- Merge with existing activity cache ---
    if os.path.exists(CACHE_FILE):
        existing = pd.read_csv(CACHE_FILE)
        combined = (
            pd.concat([existing, new_df], ignore_index=True)
            .drop_duplicates(subset="id")
        )
        added = len(combined) - len(existing)
    else:
        combined = new_df
        added = len(combined)

    combined.to_csv(CACHE_FILE, index=False)
    print(f"\n✓ {added} new activities added → {CACHE_FILE} ({len(combined)} total)")

    # --- Merge with existing power stream cache ---
    if power_frames:
        new_power = pd.concat(power_frames, ignore_index=True)

        if os.path.exists(POWER_CACHE_FILE):
            existing_power = pd.read_parquet(POWER_CACHE_FILE)
            combined_power = (
                pd.concat([existing_power, new_power], ignore_index=True)
                .drop_duplicates(subset=["activity_id", "timepoint"])
            )
        else:
            combined_power = new_power

        combined_power.to_parquet(POWER_CACHE_FILE)
        print(f"✓ {len(new_power)} new power points added → {POWER_CACHE_FILE} ({len(combined_power)} total)")

    return combined


if __name__ == "__main__":
    import sys
    zip_path = sys.argv[1] if len(sys.argv) > 1 else "wahoo_export.zip"
    df = load_wahoo_zip(zip_path)
    print("\nSample:")
    print(df[["date", "type", "distance_km", "average_watts", "average_heartrate", "source"]].tail(10))
    print("Total activities:", len(df))