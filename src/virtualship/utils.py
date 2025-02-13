from functools import lru_cache
from importlib.resources import files
from typing import TextIO

import numpy as np
import pandas as pd
import yaml
from pydantic import BaseModel

SCHEDULE = "schedule.yaml"
SHIP_CONFIG = "ship_config.yaml"
CHECKPOINT = "checkpoint.yaml"


def load_static_file(name: str) -> str:
    """Load static file from the ``virtualship.static`` module by file name."""
    return files("virtualship.static").joinpath(name).read_text(encoding="utf-8")


@lru_cache(None)
def get_example_config() -> str:
    """Get the example configuration file."""
    return load_static_file(SHIP_CONFIG)


@lru_cache(None)
def get_example_schedule() -> str:
    """Get the example schedule file."""
    return load_static_file(SCHEDULE)


def _dump_yaml(model: BaseModel, stream: TextIO) -> str | None:
    """Dump a pydantic model to a yaml string."""
    return yaml.safe_dump(
        model.model_dump(by_alias=True), stream, default_flow_style=False
    )


def _generic_load_yaml(data: str, model: BaseModel) -> BaseModel:
    """Load a yaml string into a pydantic model."""
    return model.model_validate(yaml.safe_load(data))


def mfp_to_yaml(excel_file_path: str):
    """
    Generates a YAML file with spatial and temporal information based on instrument data from MFP excel file.

    Parameters
    ----------
    - excel_file_path (str): Path to the Excel file containing coordinate and instrument data.

    The function:
    1. Reads instrument and location data from the Excel file.
    2. Determines the maximum depth and buffer based on the instruments present.
    3. Ensures longitude and latitude values remain valid after applying buffer adjustments.
    4. returns the yaml information.

    """
    # Read data from Excel
    coordinates_data = pd.read_excel(
        excel_file_path,
        usecols=["Station Type", "Name", "Latitude", "Longitude", "Instrument"],
    )
    coordinates_data = coordinates_data.dropna()

    # Define maximum depth and buffer for each instrument
    instrument_properties = {
        "CTD": {"depth": 5000, "buffer": 1},
        "DRIFTER": {"depth": 1, "buffer": 5},
        "ARGO_FLOAT": {"depth": 2000, "buffer": 5},
    }

    # Extract unique instruments from dataset
    unique_instruments = np.unique(
        np.hstack(coordinates_data["Instrument"].apply(lambda a: a.split(", ")).values)
    )

    # Determine the maximum depth based on the unique instruments
    maximum_depth = max(
        instrument_properties.get(inst, {"depth": 0})["depth"]
        for inst in unique_instruments
    )
    minimum_depth = 0

    # Determine the buffer based on the maximum buffer of the instruments present
    buffer = max(
        instrument_properties.get(inst, {"buffer": 0})["buffer"]
        for inst in unique_instruments
    )

    # Adjusted spatial range
    min_longitude = coordinates_data["Longitude"].min() - buffer
    max_longitude = coordinates_data["Longitude"].max() + buffer
    min_latitude = coordinates_data["Latitude"].min() - buffer
    max_latitude = coordinates_data["Latitude"].max() + buffer

    # Template for the YAML output
    yaml_output = {
        "space_time_region": {
            "spatial_range": {
                "minimum_longitude": min_longitude,
                "maximum_longitude": max_longitude,
                "minimum_latitude": min_latitude,
                "maximum_latitude": max_latitude,
                "minimum_depth": minimum_depth,
                "maximum_depth": maximum_depth,
            },
            "time_range": {
                "start_time": "",  # Blank start time
                "end_time": "",  # Blank end time
            },
        },
        "waypoints": [],
    }

    # Populate waypoints
    for _, row in coordinates_data.iterrows():
        instruments = row["Instrument"].split(", ")
        for instrument in instruments:
            waypoint = {
                "instrument": instrument,
                "location": {
                    "latitude": row["Latitude"],
                    "longitude": row["Longitude"],
                },
                "time": "",  # Blank time
            }
            yaml_output["waypoints"].append(waypoint)

    return yaml.dump(yaml_output, default_flow_style=False)
