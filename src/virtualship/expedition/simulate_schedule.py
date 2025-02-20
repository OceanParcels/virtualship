"""simulate_schedule function and supporting classes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pyproj

from ..instruments.argo_float import ArgoFloat
from ..instruments.ctd import CTD
from ..instruments.drifter import Drifter
from ..instruments.xbt import XBT
from ..location import Location
from ..spacetime import Spacetime
from .instrument_type import InstrumentType
from .schedule import Schedule
from .ship_config import ShipConfig
from .waypoint import Waypoint


@dataclass
class ScheduleOk:
    """Result of schedule that could be completed."""

    time: datetime
    measurements_to_simulate: MeasurementsToSimulate


@dataclass
class ScheduleProblem:
    """Result of schedule that could not be fully completed."""

    time: datetime
    failed_waypoint_i: int


@dataclass
class MeasurementsToSimulate:
    """The measurements to simulate, as concluded from schedule simulation."""

    adcps: list[Spacetime] = field(default_factory=list, init=False)
    ship_underwater_sts: list[Spacetime] = field(default_factory=list, init=False)
    argo_floats: list[ArgoFloat] = field(default_factory=list, init=False)
    drifters: list[Drifter] = field(default_factory=list, init=False)
    ctds: list[CTD] = field(default_factory=list, init=False)
    xbts: list[XBT] = field(default_factory=list, init=False)


def simulate_schedule(
    projection: pyproj.Geod, ship_config: ShipConfig, schedule: Schedule
) -> ScheduleOk | ScheduleProblem:
    """
    Simulate a schedule.

    :param projection: The projection to use for sailing.
    :param ship_config: Ship configuration.
    :param schedule: The schedule to simulate.
    :returns: Either the results of a successfully simulated schedule, or information on where the schedule became infeasible.
    """
    return _ScheduleSimulator(projection, ship_config, schedule).simulate()


class _ScheduleSimulator:
    _projection: pyproj.Geod
    _ship_config: ShipConfig
    _schedule: Schedule

    _time: datetime
    """Current time."""
    _location: Location
    """Current ship location."""

    _measurements_to_simulate: MeasurementsToSimulate

    _next_adcp_time: datetime
    """Next moment ADCP measurement will be done."""
    _next_ship_underwater_st_time: datetime
    """Next moment ship underwater ST measurement will be done."""

    def __init__(
        self, projection: pyproj.Geod, ship_config: ShipConfig, schedule: Schedule
    ) -> None:
        self._projection = projection
        self._ship_config = ship_config
        self._schedule = schedule

        assert self._schedule.waypoints[0].time is not None, (
            "First waypoint must have a time. This should have been verified before calling this function."
        )
        self._time = schedule.waypoints[0].time
        self._location = schedule.waypoints[0].location

        self._measurements_to_simulate = MeasurementsToSimulate()

        self._next_adcp_time = self._time
        self._next_ship_underwater_st_time = self._time

    def simulate(self) -> ScheduleOk | ScheduleProblem:
        for wp_i, waypoint in enumerate(self._schedule.waypoints):
            # sail towards waypoint
            self._progress_time_traveling_towards(waypoint.location)

            # check if waypoint was reached in time
            if waypoint.time is not None and self._time > waypoint.time:
                print(
                    f"Waypoint {wp_i} could not be reached in time. Current time: {self._time}. Waypoint time: {waypoint.time}."
                )
                return ScheduleProblem(self._time, wp_i)

            # note measurements made at waypoint
            time_passed = self._make_measurements(waypoint)

            # wait while measurements are being done
            self._progress_time_stationary(time_passed)
        return ScheduleOk(self._time, self._measurements_to_simulate)

    def _progress_time_traveling_towards(self, location: Location) -> None:
        geodinv: tuple[float, float, float] = self._projection.inv(
            lons1=self._location.lon,
            lats1=self._location.lat,
            lons2=location.lon,
            lats2=location.lat,
        )
        ship_speed_meter_per_second = self._ship_config.ship_speed_knots * 3600 / 1852
        azimuth1 = geodinv[0]
        distance_to_next_waypoint = geodinv[2]
        time_to_reach = timedelta(
            seconds=distance_to_next_waypoint / ship_speed_meter_per_second
        )
        end_time = self._time + time_to_reach

        # note all ADCP measurements
        if self._ship_config.adcp_config is not None:
            location = self._location
            time = self._time
            while self._next_adcp_time <= end_time:
                time_to_sail = self._next_adcp_time - time
                distance_to_move = (
                    ship_speed_meter_per_second * time_to_sail.total_seconds()
                )
                geodfwd: tuple[float, float, float] = self._projection.fwd(
                    lons=location.lon,
                    lats=location.lat,
                    az=azimuth1,
                    dist=distance_to_move,
                )
                location = Location(latitude=geodfwd[1], longitude=geodfwd[0])
                time = time + time_to_sail

                self._measurements_to_simulate.adcps.append(
                    Spacetime(location=location, time=time)
                )

                self._next_adcp_time = (
                    self._next_adcp_time + self._ship_config.adcp_config.period
                )

        # note all ship underwater ST measurements
        if self._ship_config.ship_underwater_st_config is not None:
            location = self._location
            time = self._time
            while self._next_ship_underwater_st_time <= end_time:
                time_to_sail = self._next_ship_underwater_st_time - time
                distance_to_move = (
                    ship_speed_meter_per_second * time_to_sail.total_seconds()
                )
                geodfwd: tuple[float, float, float] = self._projection.fwd(
                    lons=location.lon,
                    lats=location.lat,
                    az=azimuth1,
                    dist=distance_to_move,
                )
                location = Location(latitude=geodfwd[1], longitude=geodfwd[0])
                time = time + time_to_sail

                self._measurements_to_simulate.ship_underwater_sts.append(
                    Spacetime(location=location, time=time)
                )

                self._next_ship_underwater_st_time = (
                    self._next_ship_underwater_st_time
                    + self._ship_config.ship_underwater_st_config.period
                )

        self._time = end_time
        self._location = location

    def _progress_time_stationary(self, time_passed: timedelta) -> None:
        end_time = self._time + time_passed

        # note all ADCP measurements
        if self._ship_config.adcp_config is not None:
            while self._next_adcp_time <= end_time:
                self._measurements_to_simulate.adcps.append(
                    Spacetime(self._location, self._next_adcp_time)
                )
                self._next_adcp_time = (
                    self._next_adcp_time + self._ship_config.adcp_config.period
                )

        # note all ship underwater ST measurements
        if self._ship_config.ship_underwater_st_config is not None:
            while self._next_ship_underwater_st_time <= end_time:
                self._measurements_to_simulate.ship_underwater_sts.append(
                    Spacetime(self._location, self._next_ship_underwater_st_time)
                )
                self._next_ship_underwater_st_time = (
                    self._next_ship_underwater_st_time
                    + self._ship_config.ship_underwater_st_config.period
                )

        self._time = end_time

    def _make_measurements(self, waypoint: Waypoint) -> timedelta:
        # if there are no instruments, there is no time cost
        if waypoint.instrument is None:
            return timedelta()

        # make instruments a list even if it's only a single one
        instruments = (
            waypoint.instrument
            if isinstance(waypoint.instrument, list)
            else [waypoint.instrument]
        )

        # time costs of each measurement
        time_costs = [timedelta()]

        for instrument in instruments:
            if instrument is InstrumentType.ARGO_FLOAT:
                self._measurements_to_simulate.argo_floats.append(
                    ArgoFloat(
                        spacetime=Spacetime(self._location, self._time),
                        min_depth=self._ship_config.argo_float_config.min_depth_meter,
                        max_depth=self._ship_config.argo_float_config.max_depth_meter,
                        drift_depth=self._ship_config.argo_float_config.drift_depth_meter,
                        vertical_speed=self._ship_config.argo_float_config.vertical_speed_meter_per_second,
                        cycle_days=self._ship_config.argo_float_config.cycle_days,
                        drift_days=self._ship_config.argo_float_config.drift_days,
                    )
                )
            elif instrument is InstrumentType.CTD:
                self._measurements_to_simulate.ctds.append(
                    CTD(
                        spacetime=Spacetime(self._location, self._time),
                        min_depth=self._ship_config.ctd_config.min_depth_meter,
                        max_depth=self._ship_config.ctd_config.max_depth_meter,
                    )
                )
                time_costs.append(self._ship_config.ctd_config.stationkeeping_time)
            elif instrument is InstrumentType.DRIFTER:
                self._measurements_to_simulate.drifters.append(
                    Drifter(
                        spacetime=Spacetime(self._location, self._time),
                        depth=self._ship_config.drifter_config.depth_meter,
                        lifetime=self._ship_config.drifter_config.lifetime,
                    )
                )
            elif instrument is InstrumentType.XBT:
                self._measurements_to_simulate.xbts.append(
                    XBT(
                        spacetime=Spacetime(self._location, self._time),
                        min_depth=self._ship_config.xbt_config.min_depth_meter,
                        max_depth=self._ship_config.xbt_config.max_depth_meter,
                        fall_speed=self._ship_config.xbt_config.fall_speed_meter_per_second,
                        deceleration_coefficient=self._ship_config.xbt_config.deceleration_coefficient,
                    )
                )
            else:
                raise NotImplementedError("Instrument type not supported.")

        # measurements are done in parallel, so return time of longest one
        return max(time_costs)
