from __future__ import annotations

import os
import warnings
from datetime import timedelta
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from virtualship.models.schedule import Schedule
    from virtualship.models.ship_config import ShipConfig

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


def load_coordinates(file_path):
    """Loads coordinates from a file based on its extension."""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[-1].lower()

    try:
        if ext in [".xls", ".xlsx"]:
            return pd.read_excel(file_path)

        if ext == ".csv":
            return pd.read_csv(file_path)

        raise ValueError(f"Unsupported file extension {ext}.")

    except Exception as e:
        raise RuntimeError(
            "Could not read coordinates data from the provided file. "
            "Ensure it is either a csv or excel file."
        ) from e


def validate_coordinates(coordinates_data):
    # Expected column headers
    expected_columns = {"Station Type", "Name", "Latitude", "Longitude", "Instrument"}

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
        warnings.warn(
            f"Found additional unexpected columns {list(extra_columns)}. "
            "Manually added columns have no effect. "
            "If the MFP export format changed, please submit an issue: "
            "https://github.com/OceanParcels/virtualship/issues.",
            stacklevel=2,
        )

    # Drop unexpected columns (optional, only if you want to ensure strict conformity)
    coordinates_data = coordinates_data[list(expected_columns)]

    # Continue with the rest of the function after validation...
    coordinates_data = coordinates_data.dropna()

    # Convert latitude and longitude to floats, replacing commas with dots
    # Handles case when the latitude and longitude have decimals with commas
    if coordinates_data["Latitude"].dtype in ["object", "string"]:
        coordinates_data["Latitude"] = coordinates_data["Latitude"].apply(
            lambda x: float(x.replace(",", "."))
        )

    if coordinates_data["Longitude"].dtype in ["object", "string"]:
        coordinates_data["Longitude"] = coordinates_data["Longitude"].apply(
            lambda x: float(x.replace(",", "."))
        )

    return coordinates_data


def mfp_to_yaml(coordinates_file_path: str, yaml_output_path: str):  # noqa: D417
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
    from virtualship.models.schedule import Location, Schedule, Waypoint
    from virtualship.models.ship_config import InstrumentType
    from virtualship.expedition.space_time_region import (
        SpaceTimeRegion,
        SpatialRange,
        TimeRange,
    )

    # Read data from file
    coordinates_data = load_coordinates(coordinates_file_path)

    coordinates_data = validate_coordinates(coordinates_data)

    # maximum depth (in meters), buffer (in degrees) for each instrument
    instrument_max_depths = {
        "XBT": 2000,
        "CTD": 5000,
        "CTD_BGC": 5000,
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


def _get_schedule(expedition_dir: Path) -> Schedule:
    """Load Schedule object from yaml config file in `expedition_dir`."""
    from virtualship.models.schedule import Schedule

    file_path = expedition_dir.joinpath(SCHEDULE)
    try:
        return Schedule.from_yaml(file_path)
    except FileNotFoundError as e:
        raise FileNotFoundError(f'Schedule not found. Save it to "{file_path}".') from e


def _get_ship_config(expedition_dir: Path) -> ShipConfig:
    from virtualship.models.ship_config import ShipConfig

    file_path = expedition_dir.joinpath(SHIP_CONFIG)
    try:
        return ShipConfig.from_yaml(file_path)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f'Ship config not found. Save it to "{file_path}".'
        ) from e
