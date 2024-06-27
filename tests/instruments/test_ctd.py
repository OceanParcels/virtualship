"""Test the simulation of CTD instruments."""

from datetime import timedelta

import numpy as np
import py
from parcels import FieldSet, Field

from virtual_ship import Location, Spacetime
from virtual_ship.instruments.ctd import CTD, simulate_ctd
import datetime
import xarray as xr


def test_simulate_ctds(tmpdir: py.path.LocalPath) -> None:
    # arbitrary time offset for the dummy fieldset
    base_time = datetime.datetime.strptime("1950-01-01", "%Y-%m-%d")

    ctds = [
        CTD(
            spacetime=Spacetime(
                location=Location(latitude=0, longitude=0),
                time=base_time + datetime.timedelta(seconds=0),
            ),
            min_depth=0,
            max_depth=-500,
        )
    ]

    u = np.zeros((2, 2, 2, 2))
    v = np.zeros((2, 2, 2, 2))
    t = np.zeros((2, 2, 2, 2))
    s = np.zeros((2, 2, 2, 2))

    fieldset = FieldSet.from_data(
        {"V": v, "U": u, "T": t, "S": s},
        {
            "time": [
                np.datetime64(base_time + datetime.timedelta(seconds=0)),
                np.datetime64(base_time + datetime.timedelta(minutes=60)),
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
    x = 3

    # assert len(results.trajectory) == 1  # expect a single trajectory
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
