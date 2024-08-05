"""Performs a complete cruise with virtual ship."""

import datetime
from datetime import timedelta

import numpy as np
from parcels import Field, FieldSet

from virtual_ship import InstrumentType, Location, Waypoint
from virtual_ship.sailship import sailship
from virtual_ship.virtual_ship_config import (
    ADCPConfig,
    ArgoFloatConfig,
    CTDConfig,
    DrifterConfig,
    ShipUnderwaterSTConfig,
    VirtualShipConfig,
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
        {"U": 0, "V": 0, "salinity": 0, "temperature": 0},
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
        min_depth=-argo_float_fieldset.U.depth[0],
        max_depth=-2000,
        drift_depth=-1000,
        vertical_speed=-0.10,
        cycle_days=10,
        drift_days=9,
    )

    adcp_config = ADCPConfig(
        max_depth=-1000,
        bin_size_m=24,
        period=timedelta(minutes=5),
        fieldset=adcp_fieldset,
    )

    ship_underwater_st_config = ShipUnderwaterSTConfig(
        period=timedelta(minutes=5), fieldset=ship_underwater_st_fieldset
    )

    ctd_config = CTDConfig(
        stationkeeping_time=timedelta(minutes=20),
        fieldset=ctd_fieldset,
        min_depth=ctd_fieldset.U.depth[0],
        max_depth=ctd_fieldset.U.depth[-1],
    )

    drifter_config = DrifterConfig(
        fieldset=drifter_fieldset,
        depth=-drifter_fieldset.U.depth[0],
        lifetime=timedelta(weeks=4),
    )

    waypoints = [
        Waypoint(
            location=Location(latitude=-23.071289, longitude=63.743631),
            time=base_time,
        ),
        Waypoint(
            location=Location(latitude=-23.081289, longitude=63.743631),
            instrument=InstrumentType.CTD,
        ),
        Waypoint(
            location=Location(latitude=-23.181289, longitude=63.743631),
            time=base_time + datetime.timedelta(hours=1),
            instrument=InstrumentType.CTD,
        ),
        Waypoint(
            location=Location(latitude=-23.281289, longitude=63.743631),
            instrument=InstrumentType.DRIFTER,
        ),
        Waypoint(
            location=Location(latitude=-23.381289, longitude=63.743631),
            instrument=InstrumentType.ARGO_FLOAT,
        ),
    ]

    config = VirtualShipConfig(
        ship_speed=5.14,
        waypoints=waypoints,
        argo_float_config=argo_float_config,
        adcp_config=adcp_config,
        ship_underwater_st_config=ship_underwater_st_config,
        ctd_config=ctd_config,
        drifter_config=drifter_config,
    )

    sailship(config)
