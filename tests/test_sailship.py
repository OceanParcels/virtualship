"""Performs a complete cruise with virtual ship."""

import datetime

import numpy as np
from parcels import Field, FieldSet

from virtual_ship import Location
from virtual_ship.sailship import sailship
from virtual_ship.virtual_ship_configuration import (
    ADCPConfig,
    ArgoFloatConfig,
    VirtualShipConfiguration,
)


def _make_ctd_fieldset(base_time: datetime) -> FieldSet:
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


def _make_drifter_fieldset(base_time: datetime) -> FieldSet:
    v = np.full((2, 2, 2), 1.0)
    u = np.full((2, 2, 2), 1.0)
    t = np.full((2, 2, 2), 1.0)

    fieldset = FieldSet.from_data(
        {"V": v, "U": u, "T": t},
        {
            "time": [
                np.datetime64(base_time + datetime.timedelta(seconds=0)),
                np.datetime64(base_time + datetime.timedelta(weeks=10)),
            ],
            "lat": [-40, 90],
            "lon": [-90, 90],
        },
    )
    return fieldset


def test_sailship() -> None:
    # arbitrary time offset for the dummy fieldsets
    base_time = datetime.datetime.strptime("2022-01-01T00:00:00", "%Y-%m-%dT%H:%M:%S")

    adcp_fieldset = FieldSet.from_data(
        {"U": 0, "V": 0},
        {"lon": 0, "lat": 0},
    )

    ship_underwater_st_fieldset = FieldSet.from_data(
        {"U": 0, "V": 0, "S": 0, "T": 0},
        {"lon": 0, "lat": 0},
    )

    ctd_fieldset = _make_ctd_fieldset(base_time)

    drifter_fieldset = _make_drifter_fieldset(base_time)

    argo_float_fieldset = FieldSet.from_data(
        {"U": 0, "V": 0, "T": 0, "S": 0},
        {
            "lon": 0,
            "lat": 0,
            "time": [np.datetime64("1950-01-01") + np.timedelta64(632160, "h")],
        },
    )

    argo_float_config = ArgoFloatConfig(
        fieldset=argo_float_fieldset,
        max_depth=-2000,
        drift_depth=-1000,
        vertical_speed=-0.10,
        cycle_days=10,
        drift_days=9,
    )

    adcp_config = ADCPConfig(max_depth=-1000, bin_size_m=24)

    config = VirtualShipConfiguration(
        start_time=datetime.datetime.strptime(
            "2022-01-01T00:00:00", "%Y-%m-%dT%H:%M:%S"
        ),
        route_coordinates=[
            Location(latitude=-23.071289, longitude=63.743631),
            # Location(latitude=-23.081289, longitude=63.743631),
            Location(latitude=-23.191289, longitude=63.743631),
        ],
        adcp_fieldset=adcp_fieldset,
        ship_underwater_st_fieldset=ship_underwater_st_fieldset,
        ctd_fieldset=ctd_fieldset,
        drifter_fieldset=drifter_fieldset,
        argo_float_deploy_locations=[
            Location(latitude=-23.081289, longitude=63.743631)
        ],
        drifter_deploy_locations=[Location(latitude=-23.081289, longitude=63.743631)],
        ctd_deploy_locations=[Location(latitude=-23.081289, longitude=63.743631)],
        argo_float_config=argo_float_config,
        adcp_config=adcp_config,
    )

    sailship(config)
