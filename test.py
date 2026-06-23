from stravalib.client import Client
import pandas as pd
import os
from strava_auth import get_client

os.environ["SILENCE_TOKEN_WARNINGS"] = "true"

client = get_client()
ride_id = 17332573156

# Only request the streams you want
desired_streams = ['time', 'moving', 'watts']

# Retrieve only the selected streams for this ride
streams = client.get_activity_streams(ride_id, types=desired_streams)

# Build a dict of lists for each stream (key: stream name, value: list of data)
data = {}
max_length = 0

for stream_type in desired_streams:
    stream_obj = streams.get(stream_type)
    values = getattr(stream_obj, "data", []) if stream_obj else []
    data[stream_type] = values
    if len(values) > max_length:
        max_length = len(values)

# Pad shorter streams with None so all columns are the same length
for key in data:
    if len(data[key]) < max_length:
        data[key] += [None] * (max_length - len(data[key]))

# Create DataFrame and save to CSV
df = pd.DataFrame(data)
df.index.name = 'timepoint'  # (optional) Label the index as 'timepoint'
csv_filename = f"ride_{ride_id}_time_moving_watts.csv"
df.to_csv(csv_filename)
print(f"Saved selected streams to {csv_filename}")
