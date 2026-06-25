import os
from datetime import date

import pandas as pd


class ActivityCache:
    """
    Manages the on-disk activity CSV and power-stream parquet caches.

    Parameters
    ----------
    cache_file       : path to the activities CSV  (e.g. "activities_cache_lucas.csv")
    power_cache_file : path to the power-stream parquet (e.g. "power_streams_lucas.parquet")
    """

    def __init__(self, cache_file: str, power_cache_file: str) -> None:
        self.cache_file = cache_file
        self.power_cache_file = power_cache_file

    # ------------------------------------------------------------------
    # Date helpers
    # ------------------------------------------------------------------

    def get_latest_date(self) -> date | None:
        """
        Return the most-recent activity date found in the cache, or None if the
        cache doesn't exist / is empty.
        """
        if not os.path.exists(self.cache_file):
            return None

        df = pd.read_csv(self.cache_file, parse_dates=["date"])
        if df.empty or "date" not in df.columns:
            return None

        latest = df["date"].dropna().max()
        return latest.date() if pd.notna(latest) else None

    @staticmethod
    def is_after_cutoff(activity_date, cutoff: date | None) -> bool:
        """
        Return True when *activity_date* is strictly after *cutoff*.
        Always returns True when cutoff is None (no existing cache → keep everything).
        """
        if cutoff is None:
            return True
        if activity_date is None:
            return False
        # activity_date may arrive as datetime.date or pandas Timestamp
        if hasattr(activity_date, "date"):
            activity_date = activity_date.date()
        return activity_date > cutoff

    # ------------------------------------------------------------------
    # Cache persistence
    # ------------------------------------------------------------------

    def merge_activities(self, new_df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        """
        Merge *new_df* into the existing activities CSV, deduplicating by ``id``.

        Returns
        -------
        combined : full DataFrame now on disk
        added    : number of net-new rows written
        """
        if os.path.exists(self.cache_file):
            existing = pd.read_csv(self.cache_file)
            combined = (
                pd.concat([existing, new_df], ignore_index=True)
                .drop_duplicates(subset="id")
            )
            added = len(combined) - len(existing)
        else:
            combined = new_df.copy()
            added = len(combined)

        combined.to_csv(self.cache_file, index=False)
        return combined, added

    def merge_power_streams(self, power_frames: list[pd.DataFrame]) -> int:
        """
        Merge a list of per-activity power DataFrames into the parquet cache,
        deduplicating by ``(activity_id, timepoint)``.

        Returns the number of new power-point rows added.
        """
        if not power_frames:
            return 0

        new_power = pd.concat(power_frames, ignore_index=True)

        if os.path.exists(self.power_cache_file):
            existing_power = pd.read_parquet(self.power_cache_file)
            combined_power = (
                pd.concat([existing_power, new_power], ignore_index=True)
                .drop_duplicates(subset=["activity_id", "timepoint"])
            )
        else:
            combined_power = new_power

        combined_power.to_parquet(self.power_cache_file)
        return len(new_power)