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
    MAX_DEPTH = -1000  # -1000
    # minimum depth the ADCP can measure
    MIN_DEPTH = -5  # -5
    # How many samples to take in the complete range between max_depth and min_depth.
    NUM_BINS = 40

    # arbitrary time offset for the dummy fieldset
    base_time = datetime.datetime.strptime("1950-01-01", "%Y-%m-%d")

    # where to sample
    sample_points = [
        Spacetime(Location(0, 1), base_time + datetime.timedelta(seconds=0)),
        Spacetime(Location(2, 3), base_time + datetime.timedelta(seconds=1)),
    ]

    # expected observations at sample points
    expected_obs = [
        {
            "U": {"surface": 4, "max_depth": 5},
            "V": {"surface": 6, "max_depth": 7},
            "lon": sample_points[0].location.lon,
            "lat": sample_points[0].location.lat,
            "time": base_time + datetime.timedelta(seconds=0),
        },
        {
            "U": {"surface": 8, "max_depth": 9},
            "V": {"surface": 10, "max_depth": 11},
            "lon": sample_points[1].location.lon,
            "lat": sample_points[1].location.lat,
            "time": base_time + datetime.timedelta(seconds=1),
        },
    ]

    # create fieldset based on the expected observations
    # indices are time, depth, latitude, longitude
    u = np.zeros((2, 2, 2, 2))
    u[0, 0, 0, 0] = expected_obs[0]["U"]["max_depth"]
    u[0, 1, 0, 0] = expected_obs[0]["U"]["surface"]
    u[1, 0, 1, 1] = expected_obs[1]["U"]["max_depth"]
    u[1, 1, 1, 1] = expected_obs[1]["U"]["surface"]

    v = np.zeros((2, 2, 2, 2))
    v[0, 0, 0, 0] = expected_obs[0]["V"]["max_depth"]
    v[0, 1, 0, 0] = expected_obs[0]["V"]["surface"]
    v[1, 0, 1, 1] = expected_obs[1]["V"]["max_depth"]
    v[1, 1, 1, 1] = expected_obs[1]["V"]["surface"]

    fieldset = FieldSet.from_data(
        {
            "U": u,
            "V": v,
        },
        {
            "lon": np.array([expected_obs[0]["lon"], expected_obs[1]["lon"]]),
            "lat": np.array([expected_obs[0]["lat"], expected_obs[1]["lat"]]),
            "depth": np.array([MAX_DEPTH, MIN_DEPTH]),
            "time": np.array(
                [
                    np.datetime64(expected_obs[0]["time"]),
                    np.datetime64(expected_obs[1]["time"]),
                ]
            ),
        },
    )

    # perform simulation
    out_path = tmpdir.join("out.zarr")

    simulate_adcp(
        fieldset=fieldset,
        out_path=out_path,
        max_depth=MAX_DEPTH,
        min_depth=MIN_DEPTH,
        num_bins=NUM_BINS,
        sample_points=sample_points,
    )

    results = xr.open_zarr(out_path)

    # test if output is as expected
    assert len(results.trajectory) == NUM_BINS

    # for every obs, check if the variables match the expected observations
    # we only verify at the surface and max depth of the adcp, because in between is tricky
    for traj, vert_loc in [
        (results.trajectory[0], "max_depth"),
        (results.trajectory[-1], "surface"),
    ]:
        obs_all = results.sel(trajectory=traj).obs
        assert len(obs_all) == len(sample_points)
        for i, (obs_i, exp) in enumerate(zip(obs_all, expected_obs, strict=True)):
            obs = results.sel(trajectory=traj, obs=obs_i)
            for var in ["lat", "lon"]:
                obs_value = obs[var].values.item()
                exp_value = exp[var]
                assert np.isclose(
                    obs_value, exp_value
                ), f"Observation incorrect {vert_loc=} {obs_i=} {var=} {obs_value=} {exp_value=}."
            for var in ["U", "V"]:
                obs_value = obs[var].values.item()
                exp_value = exp[var][vert_loc]
                assert np.isclose(
                    obs_value, exp_value
                ), f"Observation incorrect {vert_loc=} {i=} {var=} {obs_value=} {exp_value=}."
