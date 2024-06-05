"""Test the simulation of ship salinity temperature measurements."""

from typing import Callable

import numpy as np
import xarray as xr
from parcels import FieldSet

from virtual_ship import Location, Spacetime
from virtual_ship.instruments.ship_underwater_st import simulate_ship_underwater_st


def test_simulate_ship_underwater_st(tmp_dir_factory: Callable[[str], str]) -> None:
    # depth at which the sampling will be done
    DEPTH = -2

    # arbitrary time offset for the dummy fieldset
    base_time = np.datetime64("1950-01-01")

    # variabes we are going to compare between expected and actual observations
    variables = ["salinity", "temperature", "lat", "lon"]

    # were to sample
    sample_points = [
        Spacetime(Location(3, 0), base_time + np.timedelta64(0, "s")),
        Spacetime(Location(7, 0), base_time + np.timedelta64(1, "s")),
    ]

    # expected observations at sample points
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

    # create fieldset based on the expected observations
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

    # below we assert if output makes sense
    assert len(results.trajectory) == 1  # expect a singe trajectory
    traj = results.trajectory.item()
    assert len(results.sel(trajectory=traj).obs) == len(
        sample_points
    )  # expect as many obs as sample points

    # for every obs, check if the variables match the expected observations
    for i, (obs_i, exp) in enumerate(
        zip(results.sel(trajectory=traj).obs, expected_obs, strict=True)
    ):
        obs = results.sel(trajectory=traj, obs=obs_i)
        for var in variables:
            obs_value = obs[var].values.item()
            exp_value = exp[var]
            assert np.isclose(
                obs_value, exp_value
            ), f"Observation incorrect {i=} {var=} {obs_value=} {exp_value=}."
