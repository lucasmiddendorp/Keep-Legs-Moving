from pathlib import Path

BASE_DIR = Path("data")


def get_user_cache_paths(username: str):

    user_dir = BASE_DIR / username

    return (
        user_dir / "activities_cache.csv",
        user_dir / "power_streams.parquet",
    )