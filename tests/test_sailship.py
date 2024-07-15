"""Performs a complete cruise with virtual ship."""

import datetime

import numpy as np
from parcels import Field, FieldSet

from virtual_ship.sailship import sailship
from virtual_ship.virtual_ship_configuration import VirtualShipConfiguration


def _make_ctd_fieldset() -> FieldSet:
    # arbitrary time offset for the dummy fieldset
    base_time = datetime.datetime.strptime("2022-01-01T00:00:00", "%Y-%m-%dT%H:%M:%S")

    u = np.zeros((2, 2, 2, 2))
    v = np.zeros((2, 2, 2, 2))
    t = np.zeros((2, 2, 2, 2))
    s = np.zeros((2, 2, 2, 2))

    fieldset = FieldSet.from_data(
        {"V": v, "U": u, "T": t, "S": s},
        {
            "time": [
                np.datetime64(base_time + datetime.timedelta(seconds=0)),
                np.datetime64(base_time + datetime.timedelta(minutes=200)),
            ],
            "depth": [0, -1000],
            "lat": [-40, 90],
            "lon": [-90, 90],
        },
    )
    fieldset.add_field(Field("bathymetry", [-1000], lon=0, lat=0))
    return fieldset


def test_sailship() -> None:
    adcp_fieldset = FieldSet.from_data(
        {"U": 0, "V": 0},
        {"lon": 0, "lat": 0},
    )

    ship_underwater_st_fieldset = FieldSet.from_data(
        {"U": 0, "V": 0, "S": 0, "T": 0},
        {"lon": 0, "lat": 0},
    )

    ctd_fieldset = _make_ctd_fieldset()

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
        ship_underwater_st_fieldset=ship_underwater_st_fieldset,
        ctd_fieldset=ctd_fieldset,
        drifter_fieldset=drifter_fieldset,
        argo_float_fieldset=argo_float_fieldset,
    )

    sailship(config)
