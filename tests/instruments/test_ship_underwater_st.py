"""Test the simulation of ship salinity temperature measurements."""

import numpy as np
from parcels import FieldSet

from virtual_ship import Location, Spacetime
from virtual_ship.instruments.ship_underwater_st import simulate_ship_underwater_st
import xarray as xr
from typing import Callable
from datetime import timedelta


def test_simulate_ship_underwater_st(tmp_dir_factory: Callable[[str], str]) -> None:
    DEPTH = -2

    base_time = np.datetime64("1950-01-01")

    variables = ["salinity", "temperature", "lat", "lon"]

    sample_points = [
        Spacetime(Location(3, 0), base_time + np.timedelta64(0, "s")),
        Spacetime(Location(7, 0), base_time + np.timedelta64(1, "s")),
    ]
    expected_obs = [
        {"salinity": 1, "temperature": 2, "lat": 3, "lon": 0, "time": base_time},
        {
            "salinity": 5,
            "temperature": 6,
            "lat": 7,
            "lon": 0,
            "time": base_time + np.timedelta64(1, "s"),
        },
    ]

    fieldset = FieldSet.from_data(
        {
            "U": np.zeros((2, 2)),
            "V": np.zeros((2, 2)),
            "salinity": [
                [expected_obs[0]["salinity"], 0],
                [0, expected_obs[1]["salinity"]],
            ],
            "temperature": [
                [expected_obs[0]["temperature"], 0],
                [0, expected_obs[1]["temperature"]],
            ],
        },
        {
            "lon": 0,
            "lat": np.array([expected_obs[0]["lat"], expected_obs[1]["lat"]]),
            "time": np.array([expected_obs[0]["time"], expected_obs[1]["time"]]),
        },
    )

    out_file_name = tmp_dir_factory(suffix=".zarr")

    simulate_ship_underwater_st(
        fieldset=fieldset,
        out_file_name=out_file_name,
        depth=DEPTH,
        sample_points=sample_points,
    )

    results = xr.open_zarr(out_file_name)

    assert len(results.trajectory) == 1
    assert len(results.sel(trajectory=0).obs) == len(sample_points)

    for i, (obs_i, exp) in enumerate(
        zip(results.sel(trajectory=0).obs, expected_obs, strict=True)
    ):
        obs = results.sel(trajectory=0, obs=obs_i)
        for var in variables:
            obs_value = obs[var].values.item()
            exp_value = exp[var]
            assert np.isclose(
                obs_value, exp_value
            ), f"Observation incorrect {i=} {var=} {obs_value=} {exp_value=}."
