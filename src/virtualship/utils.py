from datetime import timedelta
from functools import lru_cache
from importlib.resources import files
from typing import TextIO

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


def mfp_to_yaml(excel_file_path: str, yaml_output_path: str):  # noqa: D417
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
    # Importing Schedule and related models from expedition module
    from virtualship.expedition.instrument_type import InstrumentType
    from virtualship.expedition.schedule import Schedule
    from virtualship.expedition.space_time_region import (
        SpaceTimeRegion,
        SpatialRange,
        TimeRange,
    )
    from virtualship.expedition.waypoint import Location, Waypoint

    # Expected column headers
    expected_columns = {"Station Type", "Name", "Latitude", "Longitude", "Instrument"}

    # Read data from Excel
    coordinates_data = pd.read_excel(excel_file_path)

    # Check if the headers match the expected ones
    actual_columns = set(coordinates_data.columns)

    if "Instrument" not in actual_columns:
        raise ValueError(
            "Error: Missing column 'Instrument'. Have you added this column after exporting from MFP?"
        )

    missing_columns = expected_columns - actual_columns
    if missing_columns:
        raise ValueError(
            f"Error: Found columns {list(actual_columns)}, but expected columns {list(expected_columns)}. "
            "Are you sure that you're using the correct export from MFP?"
        )

    extra_columns = actual_columns - expected_columns
    if extra_columns:
        print(
            f"Warning: Found additional unexpected columns {list(extra_columns)}. "
            "Manually added columns have no effect. "
            "If the MFP export format changed, please submit an issue: "
            "https://github.com/OceanParcels/virtualship/issues."
        )

    # Drop unexpected columns (optional, only if you want to ensure strict conformity)
    coordinates_data = coordinates_data[list(expected_columns)]

    # Continue with the rest of the function after validation...
    coordinates_data = coordinates_data.dropna()

    # maximum depth (in meters), buffer (in degrees) for each instrument
    instrument_max_depths = {
        "XBT": 2000,
        "CTD": 5000,
        "DRIFTER": 1,
        "ARGO_FLOAT": 2000,
    }

    unique_instruments = set()

    for instrument_list in coordinates_data["Instrument"]:
        instruments = instrument_list.split(", ")
        unique_instruments |= set(instruments)

    # Determine the maximum depth based on the unique instruments
    maximum_depth = max(
        instrument_max_depths.get(instrument, 0) for instrument in unique_instruments
    )

    spatial_range = SpatialRange(
        minimum_longitude=coordinates_data["Longitude"].min(),
        maximum_longitude=coordinates_data["Longitude"].max(),
        minimum_latitude=coordinates_data["Latitude"].min(),
        maximum_latitude=coordinates_data["Latitude"].max(),
        minimum_depth=0,
        maximum_depth=maximum_depth,
    )

    # Create space-time region object
    space_time_region = SpaceTimeRegion(
        spatial_range=spatial_range,
        time_range=TimeRange(),
    )

    # Generate waypoints
    waypoints = []
    for _, row in coordinates_data.iterrows():
        try:
            instruments = [
                InstrumentType(instrument)
                for instrument in row["Instrument"].split(", ")
            ]
        except ValueError as err:
            raise ValueError(
                f"Error: Invalid instrument type in row {row.name}. "
                "Please ensure that the instrument type is one of: "
                f"{[instrument.name for instrument in InstrumentType]}. "
                "Also be aware that these are case-sensitive."
            ) from err
        waypoints.append(
            Waypoint(
                instrument=instruments,
                location=Location(latitude=row["Latitude"], longitude=row["Longitude"]),
            )
        )

    # Create Schedule object
    schedule = Schedule(
        waypoints=waypoints,
        space_time_region=space_time_region,
    )

    # Save to YAML file
    schedule.to_yaml(yaml_output_path)


def _validate_numeric_mins_to_timedelta(value: int | float | timedelta) -> timedelta:
    """Convert minutes to timedelta when reading."""
    if isinstance(value, timedelta):
        return value
    return timedelta(minutes=value)


def get_instruments_in_schedule(schedule):
    instruments_in_schedule = []
    for waypoint in schedule.waypoints:
        if waypoint.instrument:
            for instrument in waypoint.instrument.name:
                if instrument:
                    instruments_in_schedule.append(instrument)
    return instruments_in_schedule
