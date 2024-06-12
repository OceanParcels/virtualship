"""Test the simulation of ADCP instruments."""

import numpy as np
import py
from parcels import FieldSet

from virtual_ship import Location, Spacetime
from virtual_ship.instruments.adcp import simulate_adcp


def test_simulate_adcp(tmpdir: py.path.LocalPath) -> None:
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

    sample_points = [Spacetime(Location(0, 0), 0)]

    out_path = tmpdir.join("out.zarr")

    simulate_adcp(
        fieldset=fieldset,
        out_path=out_path,
        max_depth=MAX_DEPTH,
        min_depth=MIN_DEPTH,
        bin_size=BIN_SIZE,
        sample_points=sample_points,
    )
