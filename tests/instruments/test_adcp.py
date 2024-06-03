"""Test the simulation of Argo floats."""

import numpy as np
from parcels import FieldSet

from virtual_ship.instruments import Location
from virtual_ship.instruments.adcp import simulate_adcp, SamplePoint


def test_simulate_argo_floats() -> None:
    MAX_DEPTH = -1000
    MIN_DEPTH = -5
    BIN_SIZE = 24

    fieldset = FieldSet.from_data(
        {"U": 0, "V": 0},
        {
            "lon": 0,
            "lat": 0,
            "time": [np.datetime64("1950-01-01") + np.timedelta64(632160, "h")],
        },
    )

    sample_points = [SamplePoint(Location(0, 0), 0)]

    simulate_adcp(
        fieldset=fieldset,
        out_file_name="test",
        max_depth=MAX_DEPTH,
        min_depth=MIN_DEPTH,
        bin_size=BIN_SIZE,
        sample_points=sample_points,
    )
