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
from .virtual_ship_configuration import VirtualShipConfiguration


def sailship(config: VirtualShipConfiguration):
    """
    Use parcels to simulate the ship, take ctd_instruments and measure ADCP and underwaydata.

    :param config: The cruise configuration.
    """
    config.verify()

    # combine identical instrument deploy location
    argo_locations = set(config.argo_float_deploy_locations)
    if len(argo_locations) != len(config.argo_float_deploy_locations):
        print(
            "WARN: Some argo float deployment locations are identical and have been combined."
        )

    drifter_locations = set(config.drifter_deploy_locations)
    if len(drifter_locations) != len(config.drifter_deploy_locations):
        print(
            "WARN: Some drifter deployment locations are identical and have been combined."
        )

    ctd_locations = set(config.ctd_deploy_locations)
    if len(drifter_locations) != len(config.ctd_deploy_locations):
        print("WARN: Some CTD locations are identical and have been combined.")

    # get discrete points along the ships route were sampling and deployments will be performed
    route_dt = timedelta(minutes=5)
    route_points = shiproute(config=config, dt=route_dt)

    # adcp objects to be used in simulation
    adcps: list[Spacetime] = []

    # ship st objects to be used in simulation
    ship_underwater_sts: list[Spacetime] = []

    # argo float deployment locations that have been visited
    argo_locations_visited: set[Location] = set()
    # argo float objects to be used in simulation
    argo_floats: list[ArgoFloat] = []

    # drifter deployment locations that have been visited
    drifter_locations_visited: set[Location] = set()
    # drifter objects to be used in simulation
    drifters: list[Drifter] = []

    # ctd cast locations that have been visited
    ctd_locations_visited: set[Location] = set()
    # ctd cast objects to be used in simulation
    ctds: list[CTD] = []

    # iterate over each discrete route point, find deployment and measurement locations and times, and measure how much time this took
    # TODO between drifters, argo floats, ctd there is quite some repetition
    print("Traversing ship route.")
    time_past = timedelta()
    for i, route_point in enumerate(route_points):
        if i % 96 == 0:
            print(f"Gathered data {time_past} hours since start.")

        # find drifter deployments to be done at this location
        drifters_here = set(
            [
                drifter
                for drifter in drifter_locations - drifter_locations_visited
                if all(
                    np.isclose(
                        [drifter.lat, drifter.lon], [route_point.lat, route_point.lon]
                    )
                )
            ]
        )
        if len(drifters_here) > 1:
            print(
                "WARN: Multiple drifter deployments match the current location. Only a single deployment will be performed."
            )
        drifters.append(
            Drifter(
                spacetime=Spacetime(
                    location=route_point, time=time_past.total_seconds()
                ),
                depth=-config.drifter_fieldset.U.depth[0],
                lifetime=timedelta(weeks=4),
            )
        )
        drifter_locations_visited = drifter_locations_visited.union(drifters_here)

        # find argo float deployments to be done at this location
        argos_here = set(
            [
                argo
                for argo in argo_locations - argo_locations_visited
                if all(
                    np.isclose([argo.lat, argo.lon], [route_point.lat, route_point.lon])
                )
            ]
        )
        if len(argos_here) > 1:
            print(
                "WARN: Multiple argo float deployments match the current location. Only a single deployment will be performed."
            )
        argo_floats.append(
            ArgoFloat(
                spacetime=Spacetime(
                    location=route_point, time=time_past.total_seconds()
                ),
                min_depth=-config.argo_float_config.fieldset.U.depth[0],
                max_depth=config.argo_float_config.max_depth,
                drift_depth=config.argo_float_config.drift_depth,
                vertical_speed=config.argo_float_config.vertical_speed,
                cycle_days=config.argo_float_config.cycle_days,
                drift_days=config.argo_float_config.drift_days,
            )
        )
        argo_locations_visited = argo_locations_visited.union(argos_here)

        # find CTD casts to be done at this location
        ctds_here = set(
            [
                ctd
                for ctd in ctd_locations - ctd_locations_visited
                if all(
                    np.isclose([ctd.lat, ctd.lon], [route_point.lat, route_point.lon])
                )
            ]
        )
        if len(ctds_here) > 1:
            print(
                "WARN: Multiple CTD casts match the current location. Only a single cast will be performed."
            )

        ctds.append(
            CTD(
                spacetime=Spacetime(
                    location=route_point,
                    time=config.start_time + time_past,
                ),
                min_depth=config.ctd_fieldset.U.depth[0],
                max_depth=config.ctd_fieldset.U.depth[-1],
            )
        )
        ctd_locations_visited = ctd_locations_visited.union(ctds_here)
        # add 20 minutes to sailing time for deployment
        if len(ctds_here) != 0:
            time_past += timedelta(minutes=20)

        # add time it takes to move to the next route point
        time_past += route_dt
    # remove the last one, because no sailing to the next point was needed
    time_past -= route_dt

    # check if all drifter, argo float, ctd locations were visited
    if len(drifter_locations_visited) != len(drifter_locations):
        print(
            "WARN: some drifter deployments were not planned along the route and have not been performed."
        )

    if len(argo_locations_visited) != len(argo_locations):
        print(
            "WARN: some argo float deployments were not planned along the route and have not been performed."
        )

    if len(ctd_locations_visited) != len(ctd_locations):
        print(
            "WARN: some CTD casts were not planned along the route and have not been performed."
        )

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

    # convert CTD data to CSV
    print("Postprocessing..")
    postprocess()

    print("All data has been gathered and postprocessed, returning home.")

    cost = costs(config, time_past)
    print(f"This cruise took {time_past} and would have cost {cost:,.0f} euros.")


def shiproute(config: VirtualShipConfiguration, dt: timedelta) -> list[Location]:
    """
    Take in route coordinates and return lat and lon points within region of interest to sample.

    :param config: The cruise configuration.
    :param dt: Sailing time between each discrete route point.
    :returns: lat and lon points within region of interest to sample.
    """
    CRUISE_SPEED = 5.14

    # discrete points the ship will pass
    sample_points: list[Location] = []

    # projection used to get discrete locations
    geod = pyproj.Geod(ellps="WGS84")

    # loop over station coordinates and calculate intermediate points along great circle path
    for startloc, endloc in zip(config.route_coordinates, config.route_coordinates[1:]):
        # iterate over each coordinate and the next coordinate
        # last coordinate has no next coordinate and is skipped

        # get locations between start and end, seperate by 5 minutes of cruising
        # excludes final point, but this is added explicitly after this loop
        int_points = geod.inv_intermediate(
            startloc.lon,
            startloc.lat,
            endloc.lon,
            endloc.lat,
            del_s=CRUISE_SPEED * dt.total_seconds(),
            initial_idx=0,
            return_back_azimuth=False,
        )

        sample_points.extend(
            [
                Location(latitude=lat, longitude=lon)
                for lat, lon in zip(int_points.lats, int_points.lons, strict=True)
            ]
        )

    # explitly include final points which is not added by the previous loop
    sample_points.append(
        Location(
            latitude=config.route_coordinates[-1].lat,
            longitude=config.route_coordinates[-1].lon,
        )
    )

    return sample_points
