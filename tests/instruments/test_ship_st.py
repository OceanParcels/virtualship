"""Test the simulation of ship salinity temperature measurements."""

import numpy as np
from parcels import FieldSet

from virtual_ship import Location, Spacetime
from virtual_ship.instruments.ship_st import simulate_ship_st


def test_simulate_argo_floats() -> None:
    DEPTH = -2

    fieldset = FieldSet.from_data(
        {"U": 0, "V": 0, "S": 0, "T": 0},
        {
            "lon": 0,
            "lat": 0,
            "time": [np.datetime64("1950-01-01") + np.timedelta64(632160, "h")],
        },
    )

    sample_points = [Spacetime(Location(0, 0), 0)]

    simulate_ship_st(
        fieldset=fieldset,
        out_file_name="test",
        depth=DEPTH,
        sample_points=sample_points,
    )
