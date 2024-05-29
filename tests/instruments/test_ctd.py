"""Test the simulation of CTD instruments."""

from datetime import timedelta

import numpy as np
from parcels import FieldSet

from virtual_ship.instruments import Location
from virtual_ship.instruments.ctd import CTDInstrument, simulate_ctd


def test_simulate_drifters() -> None:
    fieldset = FieldSet.from_data(
        {"U": 0, "V": 0, "T": 0, "S": 0, "bathymetry": 100},
        {
            "lon": 0,
            "lat": 0,
            "time": [np.datetime64("1950-01-01") + np.timedelta64(632160, "h")],
        },
    )

    min_depth = -fieldset.U.depth[0]
    max_depth = -fieldset.U.depth[-1]

    ctd_instruments = [
        CTDInstrument(
            location=Location(latitude=0, longitude=0),
            deployment_time=0,
            min_depth=min_depth,
            max_depth=max_depth,
        )
    ]

    simulate_ctd(
        ctd_instruments=ctd_instruments,
        fieldset=fieldset,
        out_file_name="test",
        outputdt=timedelta(seconds=10),
    )
