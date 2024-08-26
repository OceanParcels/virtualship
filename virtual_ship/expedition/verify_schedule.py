"""verify_schedule function and supporting classes."""

from datetime import timedelta

import pyproj
from parcels import FieldSet

from .input_data import InputData
from .instrument_type import InstrumentType
from .schedule import Schedule
from .ship_config import ShipConfig
from .waypoint import Waypoint


def verify_schedule(
    projection: pyproj.Geod,
    ship_config: ShipConfig,
    schedule: Schedule,
    input_data: InputData,
) -> None:
    """
    Verify waypoints are ordered by time, first waypoint has a start time, and that schedule is feasible in terms of time if no unexpected events happen.

    :param projection: projection used to sail between waypoints.
    :param ship_config: The cruise ship_configuration.
    :param schedule: The schedule to verify.
    :param input_data: Fieldsets that can be used to check for zero UV condition (is waypoint on land).
    :raises PlanningError: If waypoints are not feasible or incorrect.
    """
    if len(schedule.waypoints) == 0:
        raise PlanningError("At least one waypoint must be provided.")

    # check first waypoint has a time
    if schedule.waypoints[0].time is None:
        raise PlanningError("First waypoint must have a specified time.")

    # check waypoint times are in ascending order
    timed_waypoints = [wp for wp in schedule.waypoints if wp.time is not None]
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

    print("Verifying all waypoints are on water..")

    # get all available fieldsets
    available_fieldsets = [
        fs
        for fs in [
            input_data.adcp_fieldset,
            input_data.argo_float_fieldset,
            input_data.ctd_fieldset,
            input_data.drifter_fieldset,
            input_data.ship_underwater_st_fieldset,
        ]
        if fs is not None
    ]

    # check if there are any fieldsets, else its an error
    if len(available_fieldsets) == 0:
        print(
            "Cannot verify because no fieldsets have been loaded. This is probably because you are not using any instruments in your schedule. This is not a problem, but carefully check your waypoint locations manually.."
        )

    else:
        # pick any
        fieldset = available_fieldsets[0]
        # get waypoints with 0 UV
        land_waypoints = [
            (wp_i, wp)
            for wp_i, wp in enumerate(schedule.waypoints)
            if _is_on_land_zero_uv(fieldset, wp)
        ]
        # raise an error if there are any
        if len(land_waypoints) > 0:
            raise PlanningError(
                f"The following waypoints are on land: {['#' + str(wp_i) + ' ' + str(wp) for (wp_i, wp) in land_waypoints]}"
            )
        print("Good, all waypoints are on water.")

    # check that ship will arrive on time at each waypoint (in case no unexpected event happen)
    time = schedule.waypoints[0].time
    for wp_i, (wp, wp_next) in enumerate(
        zip(schedule.waypoints, schedule.waypoints[1:])
    ):
        if wp.instrument is InstrumentType.CTD:
            time += timedelta(minutes=20)

        geodinv: tuple[float, float, float] = projection.inv(
            wp.location.lon, wp.location.lat, wp_next.location.lon, wp_next.location.lat
        )
        distance = geodinv[2]

        time_to_reach = timedelta(
            seconds=distance / ship_config.ship_speed_meter_per_second
        )
        arrival_time = time + time_to_reach

        if wp_next.time is None:
            time = arrival_time
        elif arrival_time > wp_next.time:
            raise PlanningError(
                f"Waypoint planning is not valid: would arrive too late at a waypoint number {wp_i + 1}. location: {wp_next.location} time: {wp_next.time} instrument: {wp_next.instrument}"
            )
        else:
            time = wp_next.time

    # verify instruments in schedule have configuration
    for wp in schedule.waypoints:
        if wp.instrument is not None:
            for instrument in (
                wp.instrument if isinstance(wp.instrument, list) else [wp.instrument]
            ):
                if (
                    instrument == InstrumentType.ARGO_FLOAT
                    and ship_config.argo_float_config is None
                ):
                    raise PlanningError(
                        "Planning has waypoint with Argo float instrument, but configuration does not configure Argo floats."
                    )
                elif (
                    instrument == InstrumentType.CTD
                    and ship_config.argo_float_config is None
                ):
                    raise PlanningError(
                        "Planning has waypoint with CTD instrument, but configuration does not configure CTDs."
                    )
                elif (
                    instrument == InstrumentType.DRIFTER
                    and ship_config.argo_float_config is None
                ):
                    raise PlanningError(
                        "Planning has waypoint with drifter instrument, but configuration does not configure drifters."
                    )
                else:
                    raise RuntimeError("Instrument not supported.")


class PlanningError(RuntimeError):
    """An error in the schedule."""

    pass


def _is_on_land_zero_uv(fieldset: FieldSet, waypoint: Waypoint) -> bool:
    """
    Check if waypoint is on land by assuming zero velocity means land.

    :param fieldset: The fieldset to sample the velocity from.
    :param waypoint: The waypoint to check.
    :returns: If the waypoint is on land.
    """
    return fieldset.UV.eval(
        0,
        fieldset.gridset.grids[0].depth[0],
        waypoint.location.lat,
        waypoint.location.lon,
        applyConversion=False,
    ) == (0.0, 0.0)
