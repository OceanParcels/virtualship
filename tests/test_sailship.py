"""Performs a complete cruise with virtual ship."""

import numpy as np
from parcels import FieldSet

from virtual_ship.sailship import sailship
from virtual_ship.virtual_ship_configuration import VirtualShipConfiguration


def test_sailship() -> None:
    adcp_fieldset = FieldSet.from_data(
        {"U": 0, "V": 0},
        {"lon": 0, "lat": 0},
    )

    ship_st_fieldset = FieldSet.from_data(
        {"U": 0, "V": 0, "S": 0, "T": 0},
        {"lon": 0, "lat": 0},
    )

    ctd_fieldset = FieldSet.from_data(
        {"U": 0, "V": 0, "S": 0, "T": 0, "bathymetry": 0},
        {"lon": 0, "lat": 0},
    )

    drifter_fieldset = FieldSet.from_data(
        {"U": 0, "V": 0, "T": 0},
        {
            "lon": 0,
            "lat": 0,
            "time": [np.datetime64("1950-01-01") + np.timedelta64(632160, "h")],
        },
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
        adcp_fieldset=adcp_fieldset,
        ship_st_fieldset=ship_st_fieldset,
        ctd_fieldset=ctd_fieldset,
        drifter_fieldset=drifter_fieldset,
        argo_float_fieldset=argo_float_fieldset,
    )

    sailship(config)
