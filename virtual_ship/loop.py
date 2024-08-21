# from datetime import datetime
from .schedule import Schedule
from pathlib import Path

import pyproj
from .ship_config import ShipConfig


def loop(expedition_dir: str | Path) -> None:
    if isinstance(expedition_dir, str):
        expedition_dir = Path(expedition_dir)

    ship_config = _get_ship_config(expedition_dir)
    if ship_config is None:
        return

    schedule = _get_schedule(expedition_dir)
    if schedule is None:
        return

    # projection used to sail between waypoints
    projection = pyproj.Geod(ellps="WGS84")

    # simulate_schedule(projection=projection, config=config)


def print_and_wait_for_user(message: str) -> None:
    print(message)
    input()


def _get_ship_config(expedition_dir: Path) -> ShipConfig | None:
    schedule_path = expedition_dir.joinpath("ship_config.yaml")
    try:
        return ShipConfig.from_yaml(schedule_path)
    except FileNotFoundError:
        print(f'Schedule not found. Save it to "{schedule_path}".')
        return None


def _get_schedule(expedition_dir: Path) -> Schedule | None:
    schedule_path = expedition_dir.joinpath("schedule.yaml")
    try:
        return Schedule.from_yaml(schedule_path)
    except FileNotFoundError:
        print(f'Schedule not found. Save it to "{schedule_path}".')
        return None


# def simulate_schedule(
#     projection: pyproj.Geod,
#     config: VirtualShipConfig,
# ) -> _ScheduleResults:
#     """
#     Simulate the sailing and aggregate the virtual measurements that should be taken.

#     :param projection: Projection used to sail between waypoints.
#     :param config: The cruise configuration.
#     :returns: Results from the simulation.
#     :raises NotImplementedError: When unsupported instruments are encountered.
#     :raises RuntimeError: When schedule appears infeasible. This should not happen in this version of virtual ship as the schedule is verified beforehand.
#     """
#     cruise = _Cruise(
#         Spacetime(
#             config.schedule.waypoints[0].location, config.schedule.waypoints[0].time
#         )
#     )
#     measurements = _MeasurementsToSimulate()

#     # add recurring tasks to task list
#     waiting_tasks = SortedList[_WaitingTask]()
#     if config.ship_underwater_st_config is not None:
#         waiting_tasks.add(
#             _WaitingTask(
#                 task=_ship_underwater_st_loop(
#                     config.ship_underwater_st_config.period, cruise, measurements
#                 ),
#                 wait_until=cruise.spacetime.time,
#             )
#         )
#     if config.adcp_config is not None:
#         waiting_tasks.add(
#             _WaitingTask(
#                 task=_adcp_loop(config.adcp_config.period, cruise, measurements),
#                 wait_until=cruise.spacetime.time,
#             )
#         )

#     # sail to each waypoint while executing tasks
#     for waypoint in config.schedule.waypoints:
#         if waypoint.time is not None and cruise.spacetime.time > waypoint.time:
#             raise RuntimeError(
#                 "Could not reach waypoint in time. This should not happen in this version of virtual ship as the schedule is verified beforehand."
#             )

#         # add task to the task queue for the instrument at the current waypoint
#         if waypoint.instrument is InstrumentType.ARGO_FLOAT:
#             _argo_float_task(cruise, measurements, config=config)
#         elif waypoint.instrument is InstrumentType.DRIFTER:
#             _drifter_task(cruise, measurements, config=config)
#         elif waypoint.instrument is InstrumentType.CTD:
#             waiting_tasks.add(
#                 _WaitingTask(
#                     _ctd_task(
#                         config.ctd_config.stationkeeping_time,
#                         config.ctd_config.min_depth,
#                         config.ctd_config.max_depth,
#                         cruise,
#                         measurements,
#                     ),
#                     cruise.spacetime.time,
#                 )
#             )
#         elif waypoint.instrument is None:
#             pass
#         else:
#             raise NotImplementedError()

#         # sail to the next waypoint
#         waypoint_reached = False
#         while not waypoint_reached:
#             # execute all tasks planned for current time
#             while (
#                 len(waiting_tasks) > 0
#                 and waiting_tasks[0].wait_until <= cruise.spacetime.time
#             ):
#                 task = waiting_tasks.pop(0)
#                 try:
#                     wait_for = next(task.task)
#                     waiting_tasks.add(
#                         _WaitingTask(task.task, cruise.spacetime.time + wait_for.time)
#                     )
#                 except StopIteration:
#                     pass

#             # if sailing is prevented by a current task, just let time pass until the next task
#             if cruise.sail_is_locked:
#                 cruise.spacetime = Spacetime(
#                     cruise.spacetime.location, waiting_tasks[0].wait_until
#                 )
#             # else, let time pass while sailing
#             else:
#                 # calculate time at which waypoint would be reached if simply sailing
#                 geodinv: tuple[float, float, float] = projection.inv(
#                     lons1=cruise.spacetime.location.lon,
#                     lats1=cruise.spacetime.location.lat,
#                     lons2=waypoint.location.lon,
#                     lats2=waypoint.location.lat,
#                 )
#                 azimuth1 = geodinv[0]
#                 distance_to_next_waypoint = geodinv[2]
#                 time_to_reach = timedelta(
#                     seconds=distance_to_next_waypoint / config.ship_speed
#                 )
#                 arrival_time = cruise.spacetime.time + time_to_reach

#                 # if waypoint is reached before next task, sail to the waypoint
#                 if (
#                     len(waiting_tasks) == 0
#                     or arrival_time <= waiting_tasks[0].wait_until
#                 ):
#                     cruise.spacetime = Spacetime(waypoint.location, arrival_time)
#                     waypoint_reached = True
#                 # else, sail until task starts
#                 else:
#                     time_to_sail = waiting_tasks[0].wait_until - cruise.spacetime.time
#                     distance_to_move = config.ship_speed * time_to_sail.total_seconds()
#                     geodfwd: tuple[float, float, float] = projection.fwd(
#                         lons=cruise.spacetime.location.lon,
#                         lats=cruise.spacetime.location.lat,
#                         az=azimuth1,
#                         dist=distance_to_move,
#                     )
#                     lon = geodfwd[0]
#                     lat = geodfwd[1]
#                     cruise.spacetime = Spacetime(
#                         Location(latitude=lat, longitude=lon),
#                         cruise.spacetime.time + time_to_sail,
#                     )

#     cruise.finish()

#     # don't sail anymore, but let tasks finish
#     while len(waiting_tasks) > 0:
#         task = waiting_tasks.pop(0)
#         try:
#             wait_for = next(task.task)
#             waiting_tasks.add(
#                 _WaitingTask(task.task, cruise.spacetime.time + wait_for.time)
#             )
#         except StopIteration:
#             pass

#     return _ScheduleResults(
#         measurements_to_simulate=measurements, end_spacetime=cruise.spacetime
#     )
