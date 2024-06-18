"""Test the simulation of ADCP instruments."""

import numpy as np
import py
from parcels import FieldSet

from virtual_ship import Location, Spacetime
from virtual_ship.instruments.adcp import simulate_adcp
import datetime
import xarray as xr


def test_simulate_adcp(tmpdir: py.path.LocalPath) -> None:
    # maximum depth the ADCP can measure
    MAX_DEPTH = -1000
    # minimum depth the ADCP can measure
    MIN_DEPTH = -5
    # how many samples to take in the complete range between max_depth and min_depth
    BIN_SIZE = 24

    # arbitrary time offset for the dummy fieldset
    base_time = datetime.datetime.strptime("1950-01-01", "%Y-%m-%d")

    # where to sample
    sample_points = [
        Spacetime(Location(0, 0), base_time + datetime.timedelta(seconds=0)),
        Spacetime(Location(1, 0), base_time + datetime.timedelta(seconds=1)),
    ]

    # expected observations at sample points
    expected_obs = [
        {
            "U": {"surface": 2, "max_depth": 3},
            "V": {"surface": 4, "max_depth": 5},
            "lat": sample_points[0].location.lat,
            "lon": sample_points[0].location.lon,
            "time": base_time + datetime.timedelta(seconds=0),
        },
        {
            "U": {"surface": 6, "max_depth": 7},
            "V": {"surface": 8, "max_depth": 9},
            "lat": sample_points[1].location.lat,
            "lon": sample_points[1].location.lon,
            "time": base_time + datetime.timedelta(seconds=1),
        },
    ]

    # create fieldset based on the expected observations
    fieldset = FieldSet.from_data(
        {
            "U": [
                [expected_obs[0]["U"]["surface"], 0],
                [0, expected_obs[1]["U"]["surface"]],
            ],
            "V": [
                [expected_obs[0]["V"]["surface"], 0],
                [0, expected_obs[1]["V"]["surface"]],
            ],
        },
        {
            "lon": 0,
            "lat": np.array([expected_obs[0]["lat"], expected_obs[1]["lat"]]),
            "time": np.array(
                [
                    np.datetime64(expected_obs[0]["time"]),
                    np.datetime64(expected_obs[1]["time"]),
                ]
            ),
        },
    )

    out_path = tmpdir.join("out.zarr")

    simulate_adcp(
        fieldset=fieldset,
        out_path=out_path,
        max_depth=MAX_DEPTH,
        min_depth=MIN_DEPTH,
        bin_size=BIN_SIZE,
        sample_points=sample_points,
    )

    results = xr.open_zarr(out_path)

    # below we assert if output makes sense
    EXPECTED_NUM_BINS = len(np.arange(MAX_DEPTH, MIN_DEPTH, BIN_SIZE))
    assert len(results.trajectory) == EXPECTED_NUM_BINS  # expect a single trajectory

    # for every obs, check if the variables match the expected observations
    # we only verify at the surface and max depth of the adcp, because the other locations are tricky
    for traj, vert_loc in [
        (results.trajectory[0], "surface"),
        (results.trajectory[-1], "max_depth"),
    ]:
        obs_all = results.sel(trajectory=traj).obs
        assert len(obs_all) == len(sample_points)
        for obs_i, exp in zip(obs_all, expected_obs, strict=True):
            obs = results.sel(trajectory=traj, obs=obs_i)
            for var in ["lat", "lon"]:
                obs_value = obs[var].values.item()
                exp_value = exp[var]
                assert np.isclose(
                    obs_value, exp_value
                ), f"Observation incorrect {obs_i=} {var=} {obs_value=} {exp_value=}."
            for var in ["U", "V"]:
                obs_value = obs[var].values.item()
                exp_value = exp[var][vert_loc]
                assert np.isclose(
                    obs_value, exp_value
                ), f"Observation incorrect {obs_i=} {var=} {obs_value=} {exp_value=}."
