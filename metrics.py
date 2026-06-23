import pandas as pd
import config
import matplotlib.pyplot as plt

df = pd.read_csv("activities_cache.csv", parse_dates=["date"])

df = df[df["weighted_average_watts"].notna()]
df["IF"] = df["weighted_average_watts"] / config.FTP
df["TSS"] = (df["moving_time"] * df["weighted_average_watts"] * df["IF"]) / (config.FTP * 3600) * 100

df_daily = df.groupby("date")["TSS"].sum().reset_index()
df_daily = df_daily.set_index("date").asfreq("D", fill_value=0)

df_daily["CTL"] = df_daily["TSS"].ewm(span=config.CTL_TIME_CONSTANT, adjust=False).mean()
df_daily["ATL"] = df_daily["TSS"].ewm(span=config.ATL_TIME_CONSTANT, adjust=False).mean()
df_daily["TSB"] = df_daily["CTL"] - df_daily["ATL"]
