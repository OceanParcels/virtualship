"""sailship function."""

from __future__ import annotations
import os
from datetime import timedelta

import pyproj

from .instrument_type import InstrumentType
from .instruments.adcp import simulate_adcp
from .instruments.argo_float import ArgoFloat, simulate_argo_floats
from .instruments.ctd import CTD, simulate_ctd
from .instruments.drifter import Drifter, simulate_drifters
from .instruments.ship_underwater_st import simulate_ship_underwater_st
from .planning_error import PlanningError
from .spacetime import Spacetime
from .virtual_ship_config import VirtualShipConfig
from .waypoint import Waypoint
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Generator, Callable
from collections import deque
from .location import Location
from contextlib import contextmanager
from .sorted_queue import SortedQueue


class Cruise:
    _finished: bool
    _sail_lock_count: int
    spacetime: Spacetime

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


@dataclass
class ScheduleResults:
    adcps: list[Spacetime] = field(default_factory=list, init=False)
    ship_underwater_sts: list[Spacetime] = field(default_factory=list, init=False)
    argo_floats: list[ArgoFloat] = field(default_factory=list, init=False)
    drifters: list[Drifter] = field(default_factory=list, init=False)
    ctds: list[CTD] = field(default_factory=list, init=False)


@dataclass
class WaitFor:
    time: timedelta


TaskGenerator = Generator[WaitFor, None, None]
Task = Callable[[Cruise, ScheduleResults], TaskGenerator]


class WaitingTask:
    _task: TaskGenerator
    _wait_until: datetime

    def __init__(self, task: TaskGenerator, wait_until: datetime) -> None:
        self._task = task
        self._wait_until = wait_until

    def __lt__(self, other: WaitingTask):
        return self._wait_until < other._wait_until

    @property
    def task(self) -> TaskGenerator:
        return self._task

    @property
    def wait_until(self) -> datetime:
        return self._wait_until


def simulate_schedule(
    tasks: list[Task],
    waypoints: list[Waypoint],
    projection: pyproj.Geod,
    ship_speed: float,
    ctd_stationkeeping_time: timedelta,
    ctd_min_depth: float,
    ctd_max_depth: float,
) -> ScheduleResults:
    # TODO verify waypoint reached in time

    cruise = Cruise(Spacetime(waypoints[0].location, waypoints[0].time))
    results = ScheduleResults()

    waiting_tasks = SortedQueue[WaitingTask]()
    for task in tasks:
        waiting_tasks.push(
            WaitingTask(task=task(cruise, results), wait_until=cruise.spacetime.time)
        )

    for waypoint in waypoints:
        match waypoint.instrument:
            case InstrumentType.ARGO_FLOAT:
                waiting_tasks.push(
                    WaitingTask(
                        ArgoFloatTask()(cruise, results),
                        wait_until=cruise.spacetime.time,
                    )
                )
            case InstrumentType.DRIFTER:
                waiting_tasks.push(
                    WaitingTask(
                        DrifterTask()(cruise, results), wait_until=cruise.spacetime.time
                    )
                )
            case InstrumentType.CTD:
                waiting_tasks.push(
                    WaitingTask(
                        CTDTask(ctd_stationkeeping_time, ctd_min_depth, ctd_max_depth)(
                            cruise, results
                        ),
                        cruise.spacetime.time,
                    )
                )
            case None:
                pass
            case _:
                raise NotImplementedError()

        waypoint_reached = False
        while not waypoint_reached:
            # execute all tasks planned for current time
            while (
                not waiting_tasks.is_empty()
                and waiting_tasks.peek().wait_until <= cruise.spacetime.time
            ):
                task = waiting_tasks.pop()
                try:
                    wait_for = next(task.task)
                    waiting_tasks.push(
                        WaitingTask(task.task, cruise.spacetime.time + wait_for.time)
                    )
                except StopIteration:
                    pass

            # get time of next waiting task
            next_task_at = waiting_tasks.peek().wait_until

            # calculate time at which waypoint would be reached if simply sailing
            geodinv: tuple[float, float, float] = projection.inv(
                lons1=cruise.spacetime.location.lon,
                lats1=cruise.spacetime.location.lat,
                lons2=waypoint.location.lon,
                lats2=waypoint.location.lat,
            )
            azimuth1 = geodinv[0]
            distance_to_next_waypoint = geodinv[2]
            time_to_reach = timedelta(seconds=distance_to_next_waypoint / ship_speed)
            arrival_time = cruise.spacetime.time + time_to_reach

            # if waypoint is reached before task starts, sail to the waypoint
            if arrival_time <= next_task_at:
                cruise.spacetime = Spacetime(waypoint.location, arrival_time)
                waypoint_reached = True
            # else, sail until task starts
            else:
                time_to_sail = next_task_at - cruise.spacetime.time
                distance_to_move = ship_speed * time_to_sail.total_seconds()
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

    while len(waiting_tasks) > 0:
        task = waiting_tasks.pop()
        try:
            wait_for = next(task.task)
            waiting_tasks.push(
                WaitingTask(task.task, cruise.spacetime.time + wait_for.time)
            )
        except StopIteration:
            pass

    return results


class ShipUnderwaterStLoop:
    _sample_period: timedelta

    def __init__(self, sample_period: timedelta) -> None:
        self._sample_period = sample_period

    def __call__(
        self, cruise: Cruise, schedule_results: ScheduleResults
    ) -> Generator[WaitFor, None, None]:
        while not cruise.finished:
            schedule_results.ship_underwater_sts.append(cruise.spacetime)
            yield WaitFor(self._sample_period)


class ADCPLoop:
    _sample_period: timedelta

    def __init__(self, sample_period: timedelta) -> None:
        self._sample_period = sample_period

    def __call__(
        self, cruise: Cruise, schedule_results: ScheduleResults
    ) -> Generator[WaitFor, None, None]:
        while not cruise.finished:
            schedule_results.adcps.append(cruise.spacetime)
            yield WaitFor(self._sample_period)


class CTDTask:
    _stationkeeping_time: timedelta
    _min_depth: float
    _max_depth: float

    def __init__(
        self, stationkeeping_time: timedelta, min_depth: float, max_depth: float
    ) -> None:
        self._stationkeeping_time = stationkeeping_time
        self._min_depth = min_depth
        self._max_depth = max_depth

    def __call__(
        self, cruise: Cruise, schedule_results: ScheduleResults
    ) -> Generator[WaitFor, None, None]:
        with cruise.do_not_sail():
            schedule_results.ctds.append(
                CTD(
                    spacetime=cruise.spacetime,
                    min_depth=self._min_depth,
                    max_depth=self._max_depth,
                )
            )
            yield WaitFor(self._stationkeeping_time)


class DrifterTask:
    def __call__(
        self, cruise: Cruise, schedule_results: ScheduleResults
    ) -> Generator[WaitFor, None, None]:
        # TODO add drifter to drifter list
        pass


class ArgoFloatTask:
    def __call__(
        self, cruise: Cruise, schedule_results: ScheduleResults
    ) -> Generator[WaitFor, None, None]:
        # TODO add argo float to argo float list
        pass


def sailship(config: VirtualShipConfig):
    """
    Use parcels to simulate the ship, take ctd_instruments and measure ADCP and underwaydata.

    :param config: The cruise configuration.
    :raises NotImplementedError: In case an instrument is not supported.
    :raises PlanningError: In case the schedule is not feasible when checking before sailing, or if it turns out not to be feasible during sailing.
    """
    config.verify()

    # projection used to sail between waypoints
    projection = pyproj.Geod(ellps="WGS84")

    _verify_waypoints(config.waypoints, config.ship_speed, projection=projection)

    schedule_results = simulate_schedule(
        [
            ShipUnderwaterStLoop(config.ship_underwater_st_period),
            ADCPLoop(config.adcp_period),
        ],
        waypoints=config.waypoints,
        projection=projection,
        ship_speed=config.ship_speed,
        ctd_stationkeeping_time=config.ctd_stationkeeping_time,
        ctd_min_depth=config.ctd_fieldset.U.depth[0],
        ctd_max_depth=config.ctd_fieldset.U.depth[-1],
    )

    print("Simulating onboard salinity and temperature measurements.")
    simulate_ship_underwater_st(
        fieldset=config.ship_underwater_st_fieldset,
        out_path=os.path.join("results", "ship_underwater_st.zarr"),
        depth=-2,
        sample_points=schedule_results.ship_underwater_sts,
    )

    print("Simulating onboard ADCP.")
    simulate_adcp(
        fieldset=config.adcp_fieldset,
        out_path=os.path.join("results", "adcp.zarr"),
        max_depth=config.adcp_config.max_depth,
        min_depth=-5,
        num_bins=(-5 - config.adcp_config.max_depth) // config.adcp_config.bin_size_m,
        sample_points=schedule_results.adcps,
    )

    print("Simulating CTD casts.")
    simulate_ctd(
        out_path=os.path.join("results", "ctd.zarr"),
        fieldset=config.ctd_fieldset,
        ctds=schedule_results.ctds,
        outputdt=timedelta(seconds=10),
    )

    print("Simulating drifters")
    simulate_drifters(
        out_path=os.path.join("results", "drifters.zarr"),
        fieldset=config.drifter_fieldset,
        drifters=schedule_results.drifters,
        outputdt=timedelta(hours=5),
        dt=timedelta(minutes=5),
        endtime=None,
    )

    print("Simulating argo floats")
    simulate_argo_floats(
        out_path=os.path.join("results", "argo_floats.zarr"),
        argo_floats=schedule_results.argo_floats,
        fieldset=config.argo_float_config.fieldset,
        outputdt=timedelta(minutes=5),
        endtime=None,
    )

    # convert CTD data to CSV
    # print("Postprocessing..")
    # postprocess()

    # print("All data has been gathered and postprocessed, returning home.")

    # time_past = time - config.waypoints[0].time
    # cost = costs(config, time_past)
    # print(f"This cruise took {time_past} and would have cost {cost:,.0f} euros.")


def _verify_waypoints(
    waypoints: list[Waypoint], ship_speed: float, projection: pyproj.Geod
) -> None:
    # check first waypoint has a time
    if waypoints[0].time is None:
        raise PlanningError("First waypoint must have a specified time.")

    # check waypoint times are in ascending order
    timed_waypoints = [wp for wp in waypoints if wp.time is not None]
    if not all(
        [
            next.time >= cur.time
            for cur, next in zip(timed_waypoints, timed_waypoints[1:])
        ]
    ):
        raise PlanningError(
            "Each waypoint should be timed after all previous waypoints"
        )

    # check that ship will arrive on time at each waypoint (in case nothing goes wrong)
    time = waypoints[0].time
    for wp, wp_next in zip(waypoints, waypoints[1:]):
        match wp.instrument:
            case InstrumentType.CTD:
                time += timedelta(minutes=20)

        geodinv: tuple[float, float, float] = projection.inv(
            wp.location.lon, wp.location.lat, wp_next.location.lon, wp_next.location.lat
        )
        distance = geodinv[2]

        time_to_reach = timedelta(seconds=distance / ship_speed)
        arrival_time = time + time_to_reach

        if wp_next.time is None:
            time = arrival_time
        elif arrival_time > wp_next.time:
            raise PlanningError(
                "Waypoint planning is not valid: would arrive too late a waypoint."
            )
        else:
            time = wp_next.time
