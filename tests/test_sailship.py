"""Performs a complete cruise with virtual ship."""

import datetime
from datetime import timedelta

import numpy as np
import pyproj
import pytest
from parcels import Field, FieldSet

from virtual_ship import InstrumentType, Location, Waypoint
from virtual_ship.sailship import PlanningError, _verify_waypoints, sailship
from virtual_ship.virtual_ship_config import (
    ADCPConfig,
    ArgoFloatConfig,
    CTDConfig,
    DrifterConfig,
    ShipUnderwaterSTConfig,
    VirtualShipConfig,
)
from virtual_ship import Schedule


def _make_ctd_fieldset(base_time: datetime) -> FieldSet:
    u = np.full((2, 2, 2, 2), 1.0)
    v = np.full((2, 2, 2, 2), 1.0)
    t = np.full((2, 2, 2, 2), 1.0)
    s = np.full((2, 2, 2, 2), 1.0)

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
        {"U": 1, "V": 1},
        {"lon": 0, "lat": 0},
    )

    ship_underwater_st_fieldset = FieldSet.from_data(
        {"U": 1, "V": 1, "salinity": 0, "temperature": 0},
        {"lon": 0, "lat": 0},
    )

    ctd_fieldset = _make_ctd_fieldset(base_time)

    drifter_fieldset = _make_drifter_fieldset(base_time)

    argo_float_fieldset = FieldSet.from_data(
        {"U": 1, "V": 1, "T": 0, "S": 0},
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

    schedule = Schedule(waypoints=waypoints)

    config = VirtualShipConfig(
        ship_speed=5.14,
        schedule=schedule,
        argo_float_config=argo_float_config,
        adcp_config=adcp_config,
        ship_underwater_st_config=ship_underwater_st_config,
        ctd_config=ctd_config,
        drifter_config=drifter_config,
    )

    sailship(config)


def test_verify_waypoints() -> None:
    # arbitrary cruise start time
    BASE_TIME = datetime.datetime.strptime("2022-01-01T00:00:00", "%Y-%m-%dT%H:%M:%S")
    PROJECTION = pyproj.Geod(ellps="WGS84")

    # the sets of waypoints to test
    WAYPOINTS = [
        [],  # require at least one waypoint
        [Waypoint(Location(0.0, 0.0))],  # first waypoint must have time
        [
            Waypoint(Location(0.0, 0.0), BASE_TIME + datetime.timedelta(days=1)),
            Waypoint(Location(0.0, 0.0), BASE_TIME),
        ],  # waypoint times must be in ascending order
        [
            Waypoint(Location(0.0, 0.0), BASE_TIME),
        ],  # 0 uv points are on land
        [
            Waypoint(Location(0.1, 0.1), BASE_TIME),
            Waypoint(Location(1.0, 1.0), BASE_TIME + datetime.timedelta(seconds=1)),
        ],  # waypoints must be reachable in time
        [
            Waypoint(Location(0.1, 0.1), BASE_TIME),
            Waypoint(Location(1.0, 1.0), BASE_TIME + datetime.timedelta(days=1)),
        ],  # a valid schedule
    ]

    # the expected errors for the schedules, or None if expected to be valid
    EXPECT_MATCH = [
        "^At least one waypoint must be provided.$",
        "^First waypoint must have a specified time.$",
        "^Each waypoint should be timed after all previous waypoints$",
        "^The following waypoints are on land: .*$",
        "^Waypoint planning is not valid: would arrive too late at a waypoint number .*$",
        None,
    ]

    # create a fieldset matching the test waypoints
    u = np.full((1, 1, 2, 2), 1.0)
    v = np.full((1, 1, 2, 2), 1.0)
    u[0, 0, 0, 0] = 0.0
    v[0, 0, 0, 0] = 0.0

    fieldset = FieldSet.from_data(
        {"V": v, "U": u},
        {
            "time": [np.datetime64(BASE_TIME)],
            "depth": [0],
            "lat": [0, 1],
            "lon": [0, 1],
        },
    )

    # dummy configs
    ctd_config = CTDConfig(None, fieldset, None, None)
    drifter_config = DrifterConfig(None, None, None)
    argo_float_config = ArgoFloatConfig(None, None, None, None, None, None, None)

    # test each set of waypoints and verify the raised errors (or none if valid)
    for waypoints, expect_match in zip(WAYPOINTS, EXPECT_MATCH, strict=True):
        config = VirtualShipConfig(
            ship_speed=5.14,
            schedule=Schedule(waypoints),
            argo_float_config=argo_float_config,
            adcp_config=None,
            ship_underwater_st_config=None,
            ctd_config=ctd_config,
            drifter_config=drifter_config,
        )
        if expect_match is not None:
            with pytest.raises(PlanningError, match=expect_match):
                _verify_waypoints(PROJECTION, config)
        else:
            _verify_waypoints(PROJECTION, config)
