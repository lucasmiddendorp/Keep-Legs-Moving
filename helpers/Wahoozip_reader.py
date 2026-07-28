import hashlib
import os
import tempfile
import zipfile

import pandas as pd
from fitparse import FitFile

from helpers.Activities_cache import ActivityCache

CACHE_FILE = "activities_cache_lucas.csv"
POWER_CACHE_FILE = "power_streams_lucas.parquet"


def wahoo_activity_id(filename: str) -> int:
    """
    Generate a stable negative integer ID from the filename.
    Negative to avoid any collision with positive Strava IDs.
    """
    return -int(hashlib.md5(os.path.basename(filename).encode()).hexdigest()[:12], 16)


def parse_fit_file(fit_path: str) -> tuple[dict, pd.DataFrame | None]:
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

    activity_id  = wahoo_activity_id(fit_path)
    start_time   = session.get("start_time")
    date         = start_time.date() if start_time else None
    trainer      = sub_sport in {"indoor_cycling", "virtual_activity"} if sub_sport else False

    total_dist  = session.get("total_distance")
    moving_time = session.get("total_moving_time") or session.get("total_timer_time")
    avg_speed   = session.get("avg_speed")
    elev_gain   = session.get("total_ascent")
    avg_hr      = session.get("avg_heart_rate")
    max_hr      = session.get("max_heart_rate")
    avg_power   = session.get("avg_power")
    norm_power  = session.get("normalized_power")

    activity = {
        # --- Core fields (same as strava_client.py activity_to_dict) ---
        "id":                     activity_id,
        "date":                   date,
        "type":                   sport,
        "distance":               float(total_dist)  if total_dist  is not None else None,
        "moving_time":            int(moving_time)   if moving_time is not None else None,
        "total_elevation_gain":   float(elev_gain)   if elev_gain   is not None else None,
        "average_speed":          float(avg_speed)   if avg_speed   is not None else None,
        "average_heartrate":      float(avg_hr)      if avg_hr      is not None else None,
        "max_heartrate":          float(max_hr)      if max_hr      is not None else None,
        "average_watts":          float(avg_power)   if avg_power   is not None else None,
        "weighted_average_watts": float(norm_power)  if norm_power  is not None else None,
        "trainer":                trainer,
        "gear_id":                None,
        # --- Derived fields ---
        "distance_km": float(total_dist) / 1000 if total_dist else None,
        "speed_kmh":   float(avg_speed)  * 3.6  if avg_speed  else None,
        # --- Source tag ---
        "source": "wahoo",
    }

    # --- Power stream (matches power_streams.parquet schema) ---
    power_df = None
    if records:
        df_rec = pd.DataFrame(records)

        if "timestamp" in df_rec.columns and start_time is not None:
            try:
                ts = pd.to_datetime(df_rec["timestamp"]).dt.tz_localize(None)
                t0 = pd.Timestamp(start_time).tz_localize(None)
                df_rec["time"] = (ts - t0).dt.total_seconds().astype(int)
            except Exception:
                df_rec["time"] = df_rec.index
        else:
            df_rec["time"] = df_rec.index

        if "speed" in df_rec.columns:
            df_rec["moving"] = df_rec["speed"] > 0
        else:
            df_rec["moving"] = None

        power_df = pd.DataFrame({
            "activity_id": activity_id,
            "timepoint":   df_rec.index,
            "time":        df_rec["time"],
            "moving":      df_rec.get("moving"),
            "watts":       df_rec.get("power"),
        })

        # --- Tracking ----
        
    return activity, power_df


def load_wahoo_zip(
    zip_path: str,
    cache_file: str = CACHE_FILE,
    power_cache_file: str = POWER_CACHE_FILE,
) -> pd.DataFrame:
    """
    Read all .fit files from a Wahoo export ZIP and merge them into
    the shared activities CSV and power-stream parquet caches.

    Only activities strictly newer than the latest date already present
    in *cache_file* are processed — older files are skipped.

    Parameters
    ----------
    zip_path         : path to the Wahoo export ZIP
    cache_file       : path to the activities CSV cache
    power_cache_file : path to the power-stream parquet cache

    Returns
    -------
    The full (merged) activities DataFrame now on disk.
    """
    cache = ActivityCache(cache_file, power_cache_file)

    # ── Find the cutoff date from the existing cache ──────────────────
    cutoff = cache.get_latest_date()
    if cutoff:
        print(f"Latest date in cache: {cutoff} — skipping activities on or before this date.")
    else:
        print("No existing cache found — importing all activities.")

    activity_rows: list[dict]         = []
    power_frames:  list[pd.DataFrame] = []
    skipped = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_path, "r") as zf:
            fit_files = [f for f in zf.namelist() if f.lower().endswith(".fit")]
            print(f"Found {len(fit_files)} .fit files in {os.path.basename(zip_path)}")

            for fit_name in fit_files:
                zf.extract(fit_name, path=tmpdir)
                fit_path = os.path.join(tmpdir, fit_name)

                try:
                    activity, power_df = parse_fit_file(fit_path)

                    # ── Skip activities that are not newer than the cutoff ──
                    if not cache.is_after_cutoff(activity["date"], cutoff):
                        skipped += 1
                        continue

                    print(f"  Parsing {os.path.basename(fit_name)}  [{activity['date']}]")
                    activity_rows.append(activity)
                    if power_df is not None:
                        power_frames.append(power_df)

                except Exception as e:
                    print(f"  ⚠ Error parsing {fit_name}: {e}")

    if skipped:
        print(f"\n↷  {skipped} file(s) skipped (on or before {cutoff})")

    if not activity_rows:
        print("No new activities to add.")
        # Return whatever is already on disk
        return pd.read_csv(cache_file) if os.path.exists(cache_file) else pd.DataFrame()

    new_df = pd.DataFrame(activity_rows)

    # ── Persist activities ────────────────────────────────────────────
    combined, added = cache.merge_activities(new_df)
    print(f"\n✓ {added} new activities added → {cache_file} ({len(combined)} total)")

    # ── Persist power streams ─────────────────────────────────────────
    new_power_pts = cache.merge_power_streams(power_frames)
    if new_power_pts:
        print(f"✓ {new_power_pts} new power points added → {power_cache_file}")

    return combined


if __name__ == "__main__":
    import sys

    zip_path = sys.argv[1] if len(sys.argv) > 1 else "WahooFitness.zip"
    df = load_wahoo_zip(zip_path)
    print("\nSample:")
    print(df[["date", "type", "distance_km", "average_watts", "average_heartrate", "source"]].tail(10))
    print("Total activities:", len(df))