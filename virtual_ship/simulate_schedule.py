from __future__ import annotations
import pyproj
from .ship_config import ShipConfig
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from .instruments.argo_float import ArgoFloat
from .instruments.ctd import CTD
from .instruments.drifter import Drifter
from .spacetime import Spacetime
from sortedcontainers import SortedList
from .instrument_type import InstrumentType
from .location import Location
from contextlib import contextmanager
from typing import Generator
from .schedule import Schedule


def simulate_schedule(
    projection: pyproj.Geod, ship_config: ShipConfig, schedule: Schedule
) -> _ScheduleResults:
    """
    Simulate the expedition schedule and aggregate the virtual measurements that should be taken.

    :param projection: Projection used to sail between waypoints.
    :param ship_config: The ship configuration.
    :returns: Results from the simulation.
    :raises NotImplementedError: When unsupported instruments are encountered.
    :raises RuntimeError: When schedule appears infeasible. This should not happen in this version of virtual ship as the schedule is verified beforehand.
    """
    cruise = _SimulationState(
        Spacetime(
            schedule.waypoints[0].location,
            schedule.waypoints[0].time,
        )
    )
    measurements = _MeasurementsToSimulate()

    # add recurring tasks to task list
    waiting_tasks = SortedList[_WaitingTask]()
    if ship_config.ship_underwater_st_config is not None:
        waiting_tasks.add(
            _WaitingTask(
                task=_ship_underwater_st_loop(
                    ship_config.ship_underwater_st_config.period, cruise, measurements
                ),
                wait_until=cruise.spacetime.time,
            )
        )
    if ship_config.adcp_config is not None:
        waiting_tasks.add(
            _WaitingTask(
                task=_adcp_loop(ship_config.adcp_config.period, cruise, measurements),
                wait_until=cruise.spacetime.time,
            )
        )

    # sail to each waypoint while executing tasks
    for waypoint in schedule.waypoints:
        if waypoint.time is not None and cruise.spacetime.time > waypoint.time:
            raise RuntimeError(
                "Could not reach waypoint in time. This should not happen in this version of virtual ship as the schedule is verified beforehand."
            )

        # add task to the task queue for the instrument at the current waypoint
        if waypoint.instrument is InstrumentType.ARGO_FLOAT:
            _argo_float_task(cruise, measurements, config=ship_config)
        elif waypoint.instrument is InstrumentType.DRIFTER:
            _drifter_task(cruise, measurements, config=ship_config)
        elif waypoint.instrument is InstrumentType.CTD:
            waiting_tasks.add(
                _WaitingTask(
                    _ctd_task(
                        ship_config.ctd_config.stationkeeping_time,
                        ship_config.ctd_config.min_depth,
                        ship_config.ctd_config.max_depth,
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
                    seconds=distance_to_next_waypoint / ship_config.ship_speed
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
                    distance_to_move = (
                        ship_config.ship_speed * time_to_sail.total_seconds()
                    )
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


class _SimulationState:
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
    sample_period: timedelta,
    cruise: _SimulationState,
    measurements: _MeasurementsToSimulate,
) -> Generator[_WaitFor, None, None]:
    while not cruise.finished:
        measurements.ship_underwater_sts.append(cruise.spacetime)
        yield _WaitFor(sample_period)


def _adcp_loop(
    sample_period: timedelta,
    cruise: _SimulationState,
    measurements: _MeasurementsToSimulate,
) -> Generator[_WaitFor, None, None]:
    while not cruise.finished:
        measurements.adcps.append(cruise.spacetime)
        yield _WaitFor(sample_period)


def _ctd_task(
    stationkeeping_time: timedelta,
    min_depth: float,
    max_depth: float,
    cruise: _SimulationState,
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
    cruise: _SimulationState,
    measurements: _MeasurementsToSimulate,
    config: ShipConfig,
) -> None:
    measurements.drifters.append(
        Drifter(
            cruise.spacetime,
            depth=config.drifter_config.depth,
            lifetime=config.drifter_config.lifetime,
        )
    )


def _argo_float_task(
    cruise: _SimulationState,
    measurements: _MeasurementsToSimulate,
    config: ShipConfig,
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
