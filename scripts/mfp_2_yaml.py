import numpy as np
import pandas as pd
import yaml

start_time = "2023-01-01 00:00:00"
end_time = "2023-02-01 00:00:00"


coordinates_data = pd.read_csv(
    "CoordinatesExport-Filled.csv",
    usecols=["Station Type", "Name", "Latitude", "Longitude", "Instrument"],
)
coordinates_data = coordinates_data.dropna()

# Define maximum depth for each instrument
instrument_depth_map = {
    "CTD": 2000,
    "DRIFTER": 1,
    "ARGO_FLOAT": 1500,
}

unique_instruments = np.unique(
    np.hstack(coordinates_data["Instrument"].apply(lambda a: a.split(", ")).values)
)

# Determine the maximum depth based on the unique instruments
maximum_depth = max(instrument_depth_map.get(inst, 0) for inst in unique_instruments)

minimum_depth = 0

buffer = 2

# template for the yaml output
yaml_output = {
    "space_time_region": {
        "spatial_range": {
            "minimum_longitude": coordinates_data["Longitude"].min() - buffer,
            "maximum_longitude": coordinates_data["Longitude"].max() + buffer,
            "minimum_latitude": coordinates_data["Latitude"].min() - buffer,
            "maximum_latitude": coordinates_data["Latitude"].max() + buffer,
            "minimum_depth": minimum_depth,
            "maximum_depth": maximum_depth,
        },
        "time_range": {
            "start_time": start_time,
            "end_time": end_time,
        },
    },
    "waypoints": [],
}

for index, row in coordinates_data.iterrows():
    instruments = row["Instrument"].split(", ")
    for instrument in instruments:
        waypoint = {
            "instrument": instrument,
            "location": {"latitude": row["Latitude"], "longitude": row["Longitude"]},
            "time": f"2023-01-01 {index:02d}:00:00",  # Placeholder time TODO
        }
        yaml_output["waypoints"].append(waypoint)

# Save the YAML content to a file
yaml_file_path = "./coordinates_to_yaml_output.yaml"
with open(yaml_file_path, "w") as file:
    yaml.dump(yaml_output, file, default_flow_style=False)
