"""sailship function."""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Generator

import pyproj
from parcels import FieldSet
from sortedcontainers import SortedList

from .costs import costs
from .instrument_type import InstrumentType
from .instruments.adcp import simulate_adcp
from .instruments.argo_float import ArgoFloat, simulate_argo_floats
from .instruments.ctd import CTD, simulate_ctd
from .instruments.drifter import Drifter, simulate_drifters
from .instruments.ship_underwater_st import simulate_ship_underwater_st
from .location import Location
from .planning_error import PlanningError
from .spacetime import Spacetime
from .virtual_ship_config import VirtualShipConfig
from .waypoint import Waypoint


def sailship(config: VirtualShipConfig):
    """
    Use Parcels to simulate a virtual ship expedition.

    :param config: The expedition configuration.
    """
    config.verify()

    # projection used to sail between waypoints
    projection = pyproj.Geod(ellps="WGS84")

    _verify_waypoints(projection=projection, config=config)

    # simulate the sailing and aggregate what measurements should be simulated
    schedule_results = _simulate_schedule(
        waypoints=config.waypoints,
        projection=projection,
        config=config,
    )

    # simulate the measurements

    if config.ship_underwater_st_config is not None:
        print("Simulating onboard salinity and temperature measurements.")
        simulate_ship_underwater_st(
            fieldset=config.ship_underwater_st_config.fieldset,
            out_path=os.path.join("results", "ship_underwater_st.zarr"),
            depth=-2,
            sample_points=schedule_results.measurements_to_simulate.ship_underwater_sts,
        )

    if config.adcp_config is not None:
        print("Simulating onboard ADCP.")
        simulate_adcp(
            fieldset=config.adcp_config.fieldset,
            out_path=os.path.join("results", "adcp.zarr"),
            max_depth=config.adcp_config.max_depth,
            min_depth=-5,
            num_bins=(-5 - config.adcp_config.max_depth)
            // config.adcp_config.bin_size_m,
            sample_points=schedule_results.measurements_to_simulate.adcps,
        )

    print("Simulating CTD casts.")
    simulate_ctd(
        out_path=os.path.join("results", "ctd.zarr"),
        fieldset=config.ctd_config.fieldset,
        ctds=schedule_results.measurements_to_simulate.ctds,
        outputdt=timedelta(seconds=10),
    )

    print("Simulating drifters")
    simulate_drifters(
        out_path=os.path.join("results", "drifters.zarr"),
        fieldset=config.drifter_config.fieldset,
        drifters=schedule_results.measurements_to_simulate.drifters,
        outputdt=timedelta(hours=5),
        dt=timedelta(minutes=5),
        endtime=None,
    )

    print("Simulating argo floats")
    simulate_argo_floats(
        out_path=os.path.join("results", "argo_floats.zarr"),
        argo_floats=schedule_results.measurements_to_simulate.argo_floats,
        fieldset=config.argo_float_config.fieldset,
        outputdt=timedelta(minutes=5),
        endtime=None,
    )

    # calculate cruise cost
    assert (
        config.waypoints[0].time is not None
    ), "First waypoints cannot have None time as this has been verified before during config verification."
    time_past = schedule_results.end_spacetime.time - config.waypoints[0].time
    cost = costs(config, time_past)
    print(f"This cruise took {time_past} and would have cost {cost:,.0f} euros.")


def _simulate_schedule(
    waypoints: list[Waypoint],
    projection: pyproj.Geod,
    config: VirtualShipConfig,
) -> _ScheduleResults:
    """
    Simulate the sailing and aggregate the virtual measurements that should be taken.

    :param waypoints: The waypoints.
    :param projection: Projection used to sail between waypoints.
    :param config: The cruise configuration.
    :returns: Results from the simulation.
    :raises NotImplementedError: When unsupported instruments are encountered.
    :raises RuntimeError: When schedule appears infeasible. This should not happen in this version of virtual ship as the schedule is verified beforehand.
    """
    cruise = _Cruise(Spacetime(waypoints[0].location, waypoints[0].time))
    measurements = _MeasurementsToSimulate()

    # add recurring tasks to task list
    waiting_tasks = SortedList[_WaitingTask]()
    if config.ship_underwater_st_config is not None:
        waiting_tasks.add(
            _WaitingTask(
                task=_ship_underwater_st_loop(
                    config.ship_underwater_st_config.period, cruise, measurements
                ),
                wait_until=cruise.spacetime.time,
            )
        )
    if config.adcp_config is not None:
        waiting_tasks.add(
            _WaitingTask(
                task=_adcp_loop(config.adcp_config.period, cruise, measurements),
                wait_until=cruise.spacetime.time,
            )
        )

    # sail to each waypoint while executing tasks
    for waypoint in waypoints:
        if waypoint.time is not None and cruise.spacetime.time > waypoint.time:
            raise RuntimeError(
                "Could not reach waypoint in time. This should not happen in this version of virtual ship as the schedule is verified beforehand."
            )

        # add task to the task queue for the instrument at the current waypoint
        if waypoint.instrument is InstrumentType.ARGO_FLOAT:
            _argo_float_task(cruise, measurements, config=config)
        elif waypoint.instrument is InstrumentType.DRIFTER:
            _drifter_task(cruise, measurements, config=config)
        elif waypoint.instrument is InstrumentType.CTD:
            waiting_tasks.add(
                _WaitingTask(
                    _ctd_task(
                        config.ctd_config.stationkeeping_time,
                        config.ctd_config.min_depth,
                        config.ctd_config.max_depth,
                        cruise,
                        measurements,
                    ),
                    cruise.spacetime.time,
                )
            )
        elif waypoint.instrument is None:
            pass
        else:
            raise NotImplementedError()

        # sail to the next waypoint
        waypoint_reached = False
        while not waypoint_reached:
            # execute all tasks planned for current time
            while (
                len(waiting_tasks) > 0
                and waiting_tasks[0].wait_until <= cruise.spacetime.time
            ):
                task = waiting_tasks.pop(0)
                try:
                    wait_for = next(task.task)
                    waiting_tasks.add(
                        _WaitingTask(task.task, cruise.spacetime.time + wait_for.time)
                    )
                except StopIteration:
                    pass

            # if sailing is prevented by a current task, just let time pass until the next task
            if cruise.sail_is_locked:
                cruise.spacetime = Spacetime(
                    cruise.spacetime.location, waiting_tasks[0].wait_until
                )
            # else, let time pass while sailing
            else:
                # calculate time at which waypoint would be reached if simply sailing
                geodinv: tuple[float, float, float] = projection.inv(
                    lons1=cruise.spacetime.location.lon,
                    lats1=cruise.spacetime.location.lat,
                    lons2=waypoint.location.lon,
                    lats2=waypoint.location.lat,
                )
                azimuth1 = geodinv[0]
                distance_to_next_waypoint = geodinv[2]
                time_to_reach = timedelta(
                    seconds=distance_to_next_waypoint / config.ship_speed
                )
                arrival_time = cruise.spacetime.time + time_to_reach

                # if waypoint is reached before next task, sail to the waypoint
                if (
                    len(waiting_tasks) == 0
                    or arrival_time <= waiting_tasks[0].wait_until
                ):
                    cruise.spacetime = Spacetime(waypoint.location, arrival_time)
                    waypoint_reached = True
                # else, sail until task starts
                else:
                    time_to_sail = waiting_tasks[0].wait_until - cruise.spacetime.time
                    distance_to_move = config.ship_speed * time_to_sail.total_seconds()
                    geodfwd: tuple[float, float, float] = projection.fwd(
                        lons=cruise.spacetime.location.lon,
                        lats=cruise.spacetime.location.lat,
                        az=azimuth1,
                        dist=distance_to_move,
                    )
                    lon = geodfwd[0]
                    lat = geodfwd[1]
                    cruise.spacetime = Spacetime(
                        Location(latitude=lat, longitude=lon),
                        cruise.spacetime.time + time_to_sail,
                    )

    cruise.finish()

    # don't sail anymore, but let tasks finish
    while len(waiting_tasks) > 0:
        task = waiting_tasks.pop(0)
        try:
            wait_for = next(task.task)
            waiting_tasks.add(
                _WaitingTask(task.task, cruise.spacetime.time + wait_for.time)
            )
        except StopIteration:
            pass

    return _ScheduleResults(
        measurements_to_simulate=measurements, end_spacetime=cruise.spacetime
    )


class _Cruise:
    _finished: bool  # if last waypoint has been reached
    _sail_lock_count: int  # if sailing should be paused because of tasks; number of tasks that requested a pause; 0 means good to go sail
    spacetime: Spacetime  # current location and time

    def __init__(self, spacetime: Spacetime) -> None:
        self._finished = False
        self._sail_lock_count = 0
        self.spacetime = spacetime

    @property
    def finished(self) -> bool:
        return self._finished

    @contextmanager
    def do_not_sail(self) -> Generator[None, None, None]:
        try:
            self._sail_lock_count += 1
            yield
        finally:
            self._sail_lock_count -= 1

    def finish(self) -> None:
        self._finished = True

    @property
    def sail_is_locked(self) -> bool:
        return self._sail_lock_count > 0


@dataclass
class _MeasurementsToSimulate:
    adcps: list[Spacetime] = field(default_factory=list, init=False)
    ship_underwater_sts: list[Spacetime] = field(default_factory=list, init=False)
    argo_floats: list[ArgoFloat] = field(default_factory=list, init=False)
    drifters: list[Drifter] = field(default_factory=list, init=False)
    ctds: list[CTD] = field(default_factory=list, init=False)


@dataclass
class _ScheduleResults:
    measurements_to_simulate: _MeasurementsToSimulate
    end_spacetime: Spacetime


@dataclass
class _WaitFor:
    time: timedelta


class _WaitingTask:
    _task: Generator[_WaitFor, None, None]
    _wait_until: datetime

    def __init__(
        self, task: Generator[_WaitFor, None, None], wait_until: datetime
    ) -> None:
        self._task = task
        self._wait_until = wait_until

    def __lt__(self, other: _WaitingTask):
        return self._wait_until < other._wait_until

    @property
    def task(self) -> Generator[_WaitFor, None, None]:
        return self._task

    @property
    def wait_until(self) -> datetime:
        return self._wait_until


def _ship_underwater_st_loop(
    sample_period: timedelta, cruise: _Cruise, measurements: _MeasurementsToSimulate
) -> Generator[_WaitFor, None, None]:
    while not cruise.finished:
        measurements.ship_underwater_sts.append(cruise.spacetime)
        yield _WaitFor(sample_period)


def _adcp_loop(
    sample_period: timedelta, cruise: _Cruise, measurements: _MeasurementsToSimulate
) -> Generator[_WaitFor, None, None]:
    while not cruise.finished:
        measurements.adcps.append(cruise.spacetime)
        yield _WaitFor(sample_period)


def _ctd_task(
    stationkeeping_time: timedelta,
    min_depth: float,
    max_depth: float,
    cruise: _Cruise,
    measurements: _MeasurementsToSimulate,
) -> Generator[_WaitFor, None, None]:
    with cruise.do_not_sail():
        measurements.ctds.append(
            CTD(
                spacetime=cruise.spacetime,
                min_depth=min_depth,
                max_depth=max_depth,
            )
        )
        yield _WaitFor(stationkeeping_time)


def _drifter_task(
    cruise: _Cruise, measurements: _MeasurementsToSimulate, config: VirtualShipConfig
) -> None:
    measurements.drifters.append(
        Drifter(
            cruise.spacetime,
            depth=config.drifter_config.depth,
            lifetime=config.drifter_config.lifetime,
        )
    )


def _argo_float_task(
    cruise: _Cruise, measurements: _MeasurementsToSimulate, config: VirtualShipConfig
) -> None:
    measurements.argo_floats.append(
        ArgoFloat(
            spacetime=cruise.spacetime,
            min_depth=config.argo_float_config.min_depth,
            max_depth=config.argo_float_config.max_depth,
            drift_depth=config.argo_float_config.drift_depth,
            vertical_speed=config.argo_float_config.vertical_speed,
            cycle_days=config.argo_float_config.cycle_days,
            drift_days=config.argo_float_config.drift_days,
        )
    )


def _verify_waypoints(
    projection: pyproj.Geod,
    config: VirtualShipConfig,
) -> None:
    """
    Verify waypoints are ordered by time, first waypoint has a start time, and that schedule is feasible in terms of time if no unexpected events happen.

    :param projection: projection used to sail between waypoints.
    :param config: The cruise configuration.
    :raises PlanningError: If waypoints are not feasible or incorrect.
    :raises ValueError: If there are no fieldsets in the config, which are needed to verify all waypoints are on water.
    """
    if len(config.waypoints) == 0:
        raise PlanningError("At least one waypoint must be provided.")

    # check first waypoint has a time
    if config.waypoints[0].time is None:
        raise PlanningError("First waypoint must have a specified time.")

    # check waypoint times are in ascending order
    timed_waypoints = [wp for wp in config.waypoints if wp.time is not None]
    if not all(
        [
            next.time >= cur.time
            for cur, next in zip(timed_waypoints, timed_waypoints[1:])
        ]
    ):
        raise PlanningError(
            "Each waypoint should be timed after all previous waypoints"
        )

    # check if all waypoints are in water
    # this is done by picking an arbitrary provided fieldset and checking if UV is not zero

    # get all available fieldsets
    available_fieldsets = [
        fs
        for fs in [
            config.adcp_config.fieldset if config.adcp_config is not None else None,
            config.argo_float_config.fieldset,
            config.ctd_config.fieldset,
            config.drifter_config.fieldset,
            (
                config.ship_underwater_st_config.fieldset
                if config.ship_underwater_st_config is not None
                else None
            ),
        ]
        if fs is not None
    ]
    # check if there are any fieldsets, else its an error
    if len(available_fieldsets) == 0:
        raise ValueError(
            "No fieldsets provided to check if waypoints are on land. Assuming no provided fieldsets is an error."
        )
    # pick any
    fieldset = available_fieldsets[0]
    # get waypoints with 0 UV
    land_waypoints = [
        (wp_i, wp)
        for wp_i, wp in enumerate(config.waypoints)
        if _is_on_land_zero_uv(fieldset, wp)
    ]
    # raise an error if there are any
    if len(land_waypoints) > 0:
        raise PlanningError(
            f"The following waypoints are on land: {['#' + str(wp_i) + ' ' + str(wp) for (wp_i, wp) in land_waypoints]}"
        )

    # check that ship will arrive on time at each waypoint (in case no unexpected event happen)
    time = config.waypoints[0].time
    for wp_i, (wp, wp_next) in enumerate(zip(config.waypoints, config.waypoints[1:])):
        if wp.instrument is InstrumentType.CTD:
            time += timedelta(minutes=20)

        geodinv: tuple[float, float, float] = projection.inv(
            wp.location.lon, wp.location.lat, wp_next.location.lon, wp_next.location.lat
        )
        distance = geodinv[2]

        time_to_reach = timedelta(seconds=distance / config.ship_speed)
        arrival_time = time + time_to_reach

        if wp_next.time is None:
            time = arrival_time
        elif arrival_time > wp_next.time:
            raise PlanningError(
                f"Waypoint planning is not valid: would arrive too late at a waypoint number {wp_i}. location: {wp.location} time: {wp.time} instrument: {wp.instrument}"
            )
        else:
            time = wp_next.time


def _is_on_land_zero_uv(fieldset: FieldSet, waypoint: Waypoint) -> bool:
    """
    Check if waypoint is on land by assuming zero velocity means land.

    :param fieldset: The fieldset to sample the velocity from.
    :param waypoint: The waypoint to check.
    :returns: If the waypoint is on land.
    """
    return fieldset.UV.eval(
        0, 0, waypoint.location.lat, waypoint.location.lon, applyConversion=False
    ) == (0.0, 0.0)
