"""Test the simulation of drifters."""

import datetime
from datetime import timedelta

import numpy as np
import py
import xarray as xr
from parcels import FieldSet

from virtual_ship import Location, Spacetime
from virtual_ship.instruments.drifter import Drifter, simulate_drifters


def test_simulate_drifters(tmpdir: py.path.LocalPath) -> None:
    # arbitrary time offset for the dummy fieldset
    base_time = datetime.datetime.strptime("1950-01-01", "%Y-%m-%d")

    CONST_TEMPERATURE = 1.0  # constant temperature in fieldset

    v = np.full((2, 2, 2), 1.0)
    u = np.full((2, 2, 2), 1.0)
    t = np.full((2, 2, 2), CONST_TEMPERATURE)

    fieldset = FieldSet.from_data(
        {"V": v, "U": u, "T": t},
        {
            "lon": np.array([0.0, 10.0]),
            "lat": np.array([0.0, 10.0]),
            "time": [
                np.datetime64(base_time + datetime.timedelta(seconds=0)),
                np.datetime64(base_time + datetime.timedelta(hours=4)),
            ],
        },
    )

    # drifters to deploy
    drifters = [
        Drifter(
            spacetime=Spacetime(
                location=Location(latitude=0, longitude=0),
                time=base_time + datetime.timedelta(days=0),
            ),
            depth=0.0,
            lifetime=datetime.timedelta(hours=2),
        ),
        Drifter(
            spacetime=Spacetime(
                location=Location(latitude=1, longitude=1),
                time=base_time + datetime.timedelta(hours=1),
            ),
            depth=0.0,
            lifetime=None,
        ),
    ]

    # perform simulation
    out_path = tmpdir.join("out.zarr")

    simulate_drifters(
        fieldset=fieldset,
        out_path=out_path,
        drifters=drifters,
        outputdt=timedelta(hours=1),
        dt=timedelta(minutes=5),
        endtime=None,
    )

    # test if output is as expected
    results = xr.open_zarr(out_path)

    assert len(results.trajectory) == len(drifters)

    for ctd_i, traj in enumerate(results.trajectory):
        # Check if drifters are moving
        # lat, lon, should be increasing values (with the above positive VU fieldset)
        assert np.all(
            np.diff(results.sel(trajectory=traj)["lat"].values) > 0
        ), "Drifter is not moving over y"
        assert np.all(
            np.diff(results.sel(trajectory=traj)["lon"].values) > 0
        ), "Drifter is not mvoing over x"

        assert np.all(
            results.sel(trajectory=traj)["temperature"] == CONST_TEMPERATURE
        ), "measured temperature does not match"
