"""Test the simulation of CTD instruments."""

import datetime
from datetime import timedelta

import numpy as np
import py
import xarray as xr
from parcels import Field, FieldSet

from virtual_ship import Location, Spacetime
from virtual_ship.instruments.ctd import CTD, simulate_ctd


def test_simulate_ctds(tmpdir: py.path.LocalPath) -> None:
    # arbitrary time offset for the dummy fieldset
    base_time = datetime.datetime.strptime("1950-01-01", "%Y-%m-%d")

    # where to cast CTDs
    ctds = [
        CTD(
            spacetime=Spacetime(
                location=Location(latitude=0, longitude=1),
                time=base_time + datetime.timedelta(hours=0),
            ),
            min_depth=0,
            max_depth=float("-inf"),
        ),
        CTD(
            spacetime=Spacetime(
                location=Location(latitude=1, longitude=0),
                time=base_time + datetime.timedelta(hours=5),
            ),
            min_depth=0,
            max_depth=float("-inf"),
        ),
    ]

    # expected observations for ctds at surface and at maximum depth
    ctds_obs = [
        {
            "surface": {
                "salinity": 5,
                "temperature": 6,
                "lat": ctds[0].spacetime.location.lat,
                "lon": ctds[0].spacetime.location.lon,
            },
            "maxdepth": {
                "salinity": 7,
                "temperature": 8,
                "lat": ctds[0].spacetime.location.lat,
                "lon": ctds[0].spacetime.location.lon,
            },
        },
        {
            "surface": {
                "salinity": 9,
                "temperature": 10,
                "lat": ctds[0].spacetime.location.lat,
                "lon": ctds[0].spacetime.location.lon,
            },
            "maxdepth": {
                "salinity": 11,
                "temperature": 12,
                "lat": ctds[0].spacetime.location.lat,
                "lon": ctds[0].spacetime.location.lon,
            },
        },
    ]

    u = np.zeros((2, 2, 2, 2))
    v = np.zeros((2, 2, 2, 2))
    t = np.zeros((2, 2, 2, 2))
    s = np.zeros((2, 2, 2, 2))

    t[0, 0, 0, 1] = ctds_obs[0]["surface"]["temperature"]
    t[0, 1, 0, 1] = ctds_obs[0]["maxdepth"]["temperature"]
    t[1, 0, 1, 0] = ctds_obs[1]["surface"]["temperature"]
    t[1, 1, 1, 0] = ctds_obs[1]["maxdepth"]["temperature"]

    fieldset = FieldSet.from_data(
        {"V": v, "U": u, "T": t, "S": s},
        {
            "time": [
                np.datetime64(base_time + datetime.timedelta(hours=0)),
                np.datetime64(base_time + datetime.timedelta(days=1)),
            ],
            "depth": [0, -1000],
            "lat": [0, 1],
            "lon": [0, 1],
        },
    )
    fieldset.add_field(Field("bathymetry", [-1000], lon=0, lat=0))

    out_path = tmpdir.join("out.zarr")

    simulate_ctd(
        ctds=ctds,
        fieldset=fieldset,
        out_path=out_path,
        outputdt=timedelta(seconds=10),
    )

    # test if output is as expected
    results = xr.open_zarr(out_path)

    # test if output is as expected
    assert len(results.trajectory) == len(ctds)

    # TODO
    # traj = results.trajectory.item()
    # assert len(results.sel(trajectory=traj).obs) == len(
    #     sample_points
    # )  # expect as many obs as sample points

    # # for every obs, check if the variables match the expected observations
    # for i, (obs_i, exp) in enumerate(
    #     zip(results.sel(trajectory=traj).obs, expected_obs, strict=True)
    # ):
    #     obs = results.sel(trajectory=traj, obs=obs_i)
    #     for var in ["salinity", "temperature", "lat", "lon"]:
    #         obs_value = obs[var].values.item()
    #         exp_value = exp[var]
    #         assert np.isclose(
    #             obs_value, exp_value
    #         ), f"Observation incorrect {i=} {var=} {obs_value=} {exp_value=}."
