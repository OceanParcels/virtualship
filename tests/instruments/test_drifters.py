"""Test the simulation of drifters."""

from datetime import timedelta

import numpy as np
from parcels import FieldSet

from virtual_ship.instruments import Location
from virtual_ship.instruments.drifter import Drifter, simulate_drifters


def test_simulate_drifters() -> None:
    fieldset = FieldSet.from_data(
        {"U": 0, "V": 0, "T": 0},
        {
            "lon": 0,
            "lat": 0,
            "time": [np.datetime64("1950-01-01") + np.timedelta64(632160, "h")],
        },
    )

    min_depth = -fieldset.U.depth[0]

    drifters = [
        Drifter(
            location=Location(latitude=0, longitude=0),
            deployment_time=0,
            min_depth=min_depth,
        )
    ]

    simulate_drifters(
        drifters=drifters,
        fieldset=fieldset,
        out_file_name="test",
        outputdt=timedelta(minutes=5),
    )
