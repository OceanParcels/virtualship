"""Test the simulation of Argo floats."""

from datetime import timedelta

import numpy as np
from parcels import FieldSet

from virtual_ship.instruments import Location
from virtual_ship.instruments.argo_float import ArgoFloat, simulate_argo_floats


def test_simulate_argo_floats() -> None:
    DRIFT_DEPTH = -1000
    MAX_DEPTH = -2000
    VERTICLE_SPEED = -0.10
    CYCLE_DAYS = 10
    DRIFT_DAYS = 9

    fieldset = FieldSet.from_data(
        {"U": 0, "V": 0, "T": 0, "S": 0},
        {
            "lon": 0,
            "lat": 0,
            "time": [np.datetime64("1950-01-01") + np.timedelta64(632160, "h")],
        },
    )

    min_depth = -fieldset.U.depth[0]

    argo_floats = [
        ArgoFloat(
            location=Location(latitude=0, longitude=0),
            deployment_time=0,
            min_depth=min_depth,
            max_depth=MAX_DEPTH,
            drift_depth=DRIFT_DEPTH,
            vertical_speed=VERTICLE_SPEED,
            cycle_days=CYCLE_DAYS,
            drift_days=DRIFT_DAYS,
        )
    ]

    simulate_argo_floats(
        argo_floats=argo_floats,
        fieldset=fieldset,
        out_file_name="test",
        outputdt=timedelta(minutes=5),
    )
