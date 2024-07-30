"""sailship function."""

import os
from datetime import timedelta

import numpy as np
import pyproj

from .costs import costs
from .instruments.adcp import simulate_adcp
from .instruments.argo_float import ArgoFloat, simulate_argo_floats
from .instruments.ctd import CTD, simulate_ctd
from .instruments.drifter import Drifter, simulate_drifters
from .instruments.ship_underwater_st import simulate_ship_underwater_st
from .location import Location
from .postprocess import postprocess
from .spacetime import Spacetime
from .virtual_ship_configuration import VirtualShipConfig
from .waypoint import Waypoint
from .instrument_type import InstrumentType


def sailship(config: VirtualShipConfig):
    """
    Use parcels to simulate the ship, take ctd_instruments and measure ADCP and underwaydata.

    :param config: The cruise configuration.
    """
    config.verify()

    verify_waypoints(config.waypoints, config.ship_speed)

    # lists of instrument deployments to be simulated
    adcps: list[Spacetime] = []
    ship_underwater_sts: list[Spacetime] = []
    argo_floats: list[ArgoFloat] = []
    drifters: list[Drifter] = []
    ctds: list[CTD] = []

    # projection used to sail between waypoints
    geod = pyproj.Geod(ellps="WGS84")

    time = config.waypoints[0].time
    assert time is not None  # cannot happen as verify_waypoints checks this

    for wp, wp_next in zip(config.waypoints, config.waypoints[1:] + [None]):
        spacetime = Spacetime(location=wp.location, time=time)

        match wp.instrument:
            case None:
                pass
            case InstrumentType.CTD:
                ctds.append(
                    CTD(
                        spacetime=spacetime,
                        min_depth=config.ctd_fieldset.U.depth[0],
                        max_depth=config.ctd_fieldset.U.depth[-1],
                    )
                )
                # use 20 minutes to case the CTD
                time += timedelta(minutes=20)
            case InstrumentType.DRIFTER:
                drifters.append(
                    Drifter(
                        spacetime=spacetime,
                        depth=-config.drifter_fieldset.U.depth[0],
                        lifetime=timedelta(weeks=4),
                    )
                )
            case InstrumentType.ARGO_FLOAT:
                argo_floats.append(
                    ArgoFloat(
                        spacetime=spacetime,
                        min_depth=-config.argo_float_config.fieldset.U.depth[0],
                        max_depth=config.argo_float_config.max_depth,
                        drift_depth=config.argo_float_config.drift_depth,
                        vertical_speed=config.argo_float_config.vertical_speed,
                        cycle_days=config.argo_float_config.cycle_days,
                        drift_days=config.argo_float_config.drift_days,
                    )
                )
            case _:
                raise NotImplementedError()

        if wp_next is None:
            break

        geodinv: tuple[float, float, float] = geod.inv(
            wp.location.lon, wp.location.lat, wp_next.location.lon, wp_next.location.lat
        )
        distance = geodinv[2]

        time_to_reach = timedelta(seconds=distance / config.ship_speed)
        arrival_time = time + time_to_reach

        if wp_next.time is None:
            time = arrival_time
        elif arrival_time > wp_next.time:
            raise RuntimeError(
                "Arrived too late at the next waypoint. This error should never happen because the schedule should have been verified beforehand in this function."
            )
        else:
            time = wp_next.time

    print("Simulating onboard salinity and temperature measurements.")
    simulate_ship_underwater_st(
        fieldset=config.ship_underwater_st_fieldset,
        out_path=os.path.join("results", "ship_underwater_st.zarr"),
        depth=-2,
        sample_points=ship_underwater_sts,
    )

    print("Simulating onboard ADCP.")
    simulate_adcp(
        fieldset=config.adcp_fieldset,
        out_path=os.path.join("results", "adcp.zarr"),
        max_depth=config.adcp_config.max_depth,
        min_depth=-5,
        num_bins=(-5 - config.adcp_config.max_depth) // config.adcp_config.bin_size_m,
        sample_points=adcps,
    )

    print("Simulating CTD casts.")
    simulate_ctd(
        out_path=os.path.join("results", "ctd.zarr"),
        fieldset=config.ctd_fieldset,
        ctds=ctds,
        outputdt=timedelta(seconds=10),
    )

    print("Simulating drifters")
    simulate_drifters(
        out_path=os.path.join("results", "drifters.zarr"),
        fieldset=config.drifter_fieldset,
        drifters=drifters,
        outputdt=timedelta(hours=5),
        dt=timedelta(minutes=5),
        endtime=None,
    )

    print("Simulating argo floats")
    simulate_argo_floats(
        out_path=os.path.join("results", "argo_floats.zarr"),
        argo_floats=argo_floats,
        fieldset=config.argo_float_config.fieldset,
        outputdt=timedelta(minutes=5),
        endtime=None,
    )

    # # iterate over each discrete route point, find deployment and measurement locations and times, and measure how much time this took
    # # TODO between drifters, argo floats, ctd there is quite some repetition
    # print("Traversing ship route.")
    # time_past = timedelta()
    # for i, route_point in enumerate(route_points):
    #     if i % 96 == 0:
    #         print(f"Gathered data {time_past} hours since start.")

    # # remove the last one, because no sailing to the next point was needed
    # time_past -= route_dt

    # print("Simulating onboard salinity and temperature measurements.")
    # simulate_ship_underwater_st(
    #     fieldset=config.ship_underwater_st_fieldset,
    #     out_path=os.path.join("results", "ship_underwater_st.zarr"),
    #     depth=-2,
    #     sample_points=ship_underwater_sts,
    # )

    # print("Simulating onboard ADCP.")
    # simulate_adcp(
    #     fieldset=config.adcp_fieldset,
    #     out_path=os.path.join("results", "adcp.zarr"),
    #     max_depth=config.adcp_config.max_depth,
    #     min_depth=-5,
    #     num_bins=(-5 - config.adcp_config.max_depth) // config.adcp_config.bin_size_m,
    #     sample_points=adcps,
    # )

    # # convert CTD data to CSV
    # print("Postprocessing..")
    # postprocess()

    # print("All data has been gathered and postprocessed, returning home.")

    # cost = costs(config, time_past)
    # print(f"This cruise took {time_past} and would have cost {cost:,.0f} euros.")


def verify_waypoints(waypoints: list[Waypoint], ship_speed: float) -> None:
    # check first waypoint has a time
    if waypoints[0].time is None:
        raise ValueError("First waypoint must have a specified time.")

    # check waypoint times are in ascending order
    timed_waypoints = [wp for wp in waypoints if wp.time is not None]
    if not all(
        [
            next.time >= cur.time
            for cur, next in zip(timed_waypoints, timed_waypoints[1:])
        ]
    ):
        raise ValueError("Each waypoint should be timed after all previous waypoints")

    # projection used to sail between waypoints
    geod = pyproj.Geod(ellps="WGS84")

    # check that ship will arrive on time at each waypoint (in case nothing goes wrong)
    time = waypoints[0].time
    for wp, wp_next in zip(waypoints, waypoints[1:]):
        match wp.instrument:
            case InstrumentType.CTD:
                time += timedelta(minutes=20)

        geodinv: tuple[float, float, float] = geod.inv(
            wp.location.lon, wp.location.lat, wp_next.location.lon, wp_next.location.lat
        )
        distance = geodinv[2]

        time_to_reach = timedelta(seconds=distance / ship_speed)
        arrival_time = time + time_to_reach

        if wp_next.time is None:
            time = arrival_time
        elif arrival_time > wp_next.time:
            raise RuntimeError(
                "Waypoint planning is not valid: would arrive too late a waypoint."
            )
        else:
            time = wp_next.time
