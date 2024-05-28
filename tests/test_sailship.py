"""Performs a complete cruise with virtual ship."""

from virtual_ship.virtual_ship_configuration import VirtualShipConfiguration
from virtual_ship.sailship import sailship
from parcels import FieldSet
import numpy as np


def test_sailship() -> None:
    ctd_fieldset = FieldSet.from_data(
        {"U": 0, "V": 0, "S": 0, "T": 0, "bathymetry": 0},
        {"lon": 0, "lat": 0},
    )
    ctd_fieldset.add_constant("maxtime", ctd_fieldset.U.grid.time_full[-1])
    ctd_fieldset.add_constant("mindepth", -ctd_fieldset.U.depth[0])
    ctd_fieldset.add_constant("max_depth", -ctd_fieldset.U.depth[-1])

    drifter_fieldset = FieldSet.from_data(
        {
            "U": 0,
            "V": 0,
        },
        {"lon": 0, "lat": 0},
    )

    argo_float_fieldset = FieldSet.from_data(
        {"U": 0, "V": 0, "T": 0, "S": 0},
        {
            "lon": 0,
            "lat": 0,
            "time": [np.datetime64("1950-01-01") + np.timedelta64(632160, "h")],
        },
    )

    config = VirtualShipConfiguration(
        "sailship_config.json",
        ctd_fieldset=ctd_fieldset,
        drifter_fieldset=drifter_fieldset,
        argo_float_fieldset=argo_float_fieldset,
    )

    sailship(config)
