"""Test the simulation of drifters."""

import datetime
from datetime import timedelta

import numpy as np
import py
from parcels import FieldSet

from virtual_ship import Location, Spacetime
from virtual_ship.instruments.drifter import Drifter, simulate_drifters


def test_simulate_drifters(tmpdir: py.path.LocalPath) -> None:
    # arbitrary time offset for the dummy fieldset
    base_time = datetime.datetime.strptime("1950-01-01", "%Y-%m-%d")

    v = np.full((2, 2, 2), 1.0)
    u = np.full((2, 2, 2), 1.0)
    t = np.full((2, 2, 2), 1.0)

    fieldset = FieldSet.from_data(
        {"V": v, "U": u, "T": t},
        {
            "lon": np.array([0.0, 10.0]),
            "lat": np.array([0.0, 10.0]),
            "time": [
                np.datetime64(base_time + datetime.timedelta(seconds=0)),
                np.datetime64(base_time + datetime.timedelta(weeks=10)),
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
            lifetime=datetime.timedelta(hours=2),  # TODO choose this
            asd
        )
    ]
    # TODO more drifters?
    asdas

    # perform simulation
    out_path = tmpdir.join("out.zarr")

    simulate_drifters(
        fieldset=fieldset,
        out_path=out_path,
        drifters=drifters,
        outputdt=timedelta(minutes=5),
        endtime=None,
    )

    asdasd
    # test ouput