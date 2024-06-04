"""sailship function."""

import os
from datetime import timedelta

import numpy as np
import pyproj
from shapely.geometry import Point, Polygon

from .costs import costs
from .instruments import Location, Spacetime
from .instruments.adcp import simulate_adcp
from .instruments.argo_float import ArgoFloat, simulate_argo_floats
from .instruments.ctd import CTD, simulate_ctd
from .instruments.drifter import Drifter, simulate_drifters
from .instruments.ship_st import simulate_ship_st
from .postprocess import postprocess
from .virtual_ship_configuration import VirtualShipConfiguration


def sailship(config: VirtualShipConfiguration):
    """
    Use parcels to simulate the ship, take ctd_instruments and measure ADCP and underwaydata.

    :param config: The cruise configuration.
    """
    # TODO this will be in the config later, but for now we don't change the config structure
    # from here -----
    argo_locations_list = [
        Location(latitude=argo[1], longitude=argo[0])
        for argo in config.argo_deploylocations
    ]
    argo_locations = set(argo_locations_list)
    if len(argo_locations) != len(argo_locations_list):
        print(
            "WARN: Some argo float deployment locations are identical and have been combined."
        )

    drifter_locations_list = [
        Location(latitude=drifter[1], longitude=drifter[0])
        for drifter in config.drifter_deploylocations
    ]
    drifter_locations = set(drifter_locations_list)
    if len(drifter_locations) != len(drifter_locations_list):
        print(
            "WARN: Some drifter deployment locations are identical and have been combined."
        )

    ctd_locations_list = [
        Location(latitude=ctd[1], longitude=ctd[0]) for ctd in config.CTD_locations
    ]
    ctd_locations = set(ctd_locations_list)
    if len(ctd_locations) != len(ctd_locations_list):
        print("WARN: Some CTD locations are identical and have been combined.")
    # until here ----

    # get discrete points along the ships route were sampling and deployments will be performed
    route_dt = timedelta(minutes=5)
    route_points = shiproute(config=config, dt=route_dt)

    # adcp objects to be used in simulation
    adcps: list[Spacetime] = []

    # ship st objects to be used in simulation
    ship_sts: list[Spacetime] = []

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
                location=route_point,
                deployment_time=time_past.total_seconds(),
                min_depth=-config.drifter_fieldset.U.depth[0],
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
                location=route_point,
                deployment_time=time_past.total_seconds(),
                min_depth=-config.argo_float_fieldset.U.depth[0],
                max_depth=config.argo_characteristics["maxdepth"],
                drift_depth=config.argo_characteristics["driftdepth"],
                vertical_speed=config.argo_characteristics["vertical_speed"],
                cycle_days=config.argo_characteristics["cycle_days"],
                drift_days=config.argo_characteristics["drift_days"],
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
                location=route_point,
                deployment_time=time_past.total_seconds(),
                min_depth=-config.ctd_fieldset.U.depth[0],
                max_depth=-config.ctd_fieldset.U.depth[-1],
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
    simulate_ship_st(
        fieldset=config.ship_st_fieldset,
        out_file_name=os.path.join("results", "ship_st.zarr"),
        depth=-2,
        sample_points=ship_sts,
    )

    print("Simulating onboard ADCP.")
    simulate_adcp(
        fieldset=config.adcp_fieldset,
        out_file_name=os.path.join("results", "adcp.zarr"),
        max_depth=config.ADCP_settings["max_depth"],
        min_depth=-5,
        bin_size=config.ADCP_settings["bin_size_m"],
        sample_points=adcps,
    )

    print("Simulating CTD casts.")
    simulate_ctd(
        ctds=ctds,
        fieldset=config.ctd_fieldset,
        out_file_name=os.path.join("results", "ctd.zarr"),
        outputdt=timedelta(seconds=10),
    )

    print("Simulating drifters")
    simulate_drifters(
        drifters=drifters,
        fieldset=config.drifter_fieldset,
        out_file_name=os.path.join("results", "drifters.zarr"),
        outputdt=timedelta(minutes=5),
    )

    print("Simulating argo floats")
    simulate_argo_floats(
        argo_floats=argo_floats,
        fieldset=config.argo_float_fieldset,
        out_file_name=os.path.join("results", "argo_floats.zarr"),
        outputdt=timedelta(minutes=5),
    )

    # convert CTD data to CSV
    print("Postprocessing..")
    postprocess()

    print("All data has been gathered and postprocessed, returning home.")

    cost = costs(config, time_past)
    print(f"This cruise took {time_past} and would have cost {cost:,.0f} euros.")


# def create_fieldset(config, data_dir: str):
#     """
#     Create fieldset from netcdf files and adds bathymetry data for CTD cast, returns fieldset with negative depth values.

#     :param config: The cruise configuration.
#     :param data_dir: TODO
#     :returns: The fieldset.
#     :raises ValueError: If downloaded data is not as expected.
#     """
#     filenames = {
#         "U": os.path.join(data_dir, "studentdata_UV.nc"),
#         "V": os.path.join(data_dir, "studentdata_UV.nc"),
#         "S": os.path.join(data_dir, "studentdata_S.nc"),
#         "T": os.path.join(data_dir, "studentdata_T.nc"),
#     }
#     variables = {"U": "uo", "V": "vo", "S": "so", "T": "thetao"}
#     dimensions = {
#         "lon": "longitude",
#         "lat": "latitude",
#         "time": "time",
#         "depth": "depth",
#     }

#     # create the fieldset and set interpolation methods
#     fieldset = FieldSet.from_netcdf(
#         filenames, variables, dimensions, allow_time_extrapolation=True
#     )
#     fieldset.T.interp_method = "linear_invdist_land_tracer"
#     fieldset.S.interp_method = "linear_invdist_land_tracer"
#     for g in fieldset.gridset.grids:
#         if max(g.depth) > 0:
#             g.depth = -g.depth  # make depth negative
#     fieldset.mindepth = -fieldset.U.depth[0]  # uppermost layer in the hydrodynamic data
#     if config.CTD_settings["max_depth"] == "max":
#         fieldset.add_constant("max_depth", -fieldset.U.depth[-1])
#     else:
#         fieldset.add_constant("max_depth", config.CTD_settings["max_depth"])
#     fieldset.add_constant("maxtime", fieldset.U.grid.time_full[-1])

#     # add bathymetry data to the fieldset for CTD cast
#     bathymetry_file = os.path.join(data_dir, "GLO-MFC_001_024_mask_bathy.nc")
#     bathymetry_variables = ("bathymetry", "deptho")
#     bathymetry_dimensions = {"lon": "longitude", "lat": "latitude"}
#     bathymetry_field = Field.from_netcdf(
#         bathymetry_file, bathymetry_variables, bathymetry_dimensions
#     )
#     fieldset.add_field(bathymetry_field)
#     # read in data already
#     fieldset.computeTimeChunk(0, 1)

#     if fieldset.U.lon.min() > config.region_of_interest["West"]:
#         raise ValueError(
#             "FieldSet western boundary is outside region of interest. Please run download_data.py again."
#         )
#     if fieldset.U.lon.max() < config.region_of_interest["East"]:
#         raise ValueError(
#             "FieldSet eastern boundary is outside region of interest. Please run download_data.py again."
#         )
#     if fieldset.U.lat.min() > config.region_of_interest["South"]:
#         raise ValueError(
#             "FieldSet southern boundary is outside region of interest. Please run download_data.py again."
#         )
#     if fieldset.U.lat.max() < config.region_of_interest["North"]:
#         raise ValueError(
#             "FieldSet northern boundary is outside region of interest. Please run download_data.py again."
#         )
#     return fieldset


def shiproute(config: VirtualShipConfiguration, dt: timedelta) -> list[Location]:
    """
    Take in route coordinates and return lat and lon points within region of interest to sample.

    :param config: The cruise configuration.
    :param dt: Sailing time between each discrete route point.
    :returns: lat and lon points within region of interest to sample.
    """
    # Initialize lists to store intermediate points
    lons = []
    lats = []

    # Loop over station coordinates and calculate intermediate points along great circle path
    for i in range(len(config.route_coordinates) - 1):
        startlong = config.route_coordinates[i][0]
        startlat = config.route_coordinates[i][1]
        endlong = config.route_coordinates[i + 1][0]
        endlat = config.route_coordinates[i + 1][1]

        # calculate line string along path with segments every 5 min for ADCP measurements
        # current cruise speed is 10knots = 5.14 m/s * 60*5 = 1542 m every 5 min
        # Realistic time between measurements is 2 min on Pelagia according to Floran
        cruise_speed = 5.14
        geod = pyproj.Geod(ellps="WGS84")
        azimuth1, azimuth2, distance = geod.inv(startlong, startlat, endlong, endlat)
        if distance > (cruise_speed * dt.total_seconds()):
            r = geod.inv_intermediate(
                startlong,
                startlat,
                endlong,
                endlat,
                del_s=1545,
                initial_idx=0,
                return_back_azimuth=False,
            )
            lons = np.append(lons, r.lons)  # stored as a list of arrays
            lats = np.append(lats, r.lats)
        else:
            lons = np.append(lons, endlong)
            lats = np.append(lats, endlat)

    # initial_idx will add begin point to each list (but not end point to avoid doubling) so add final endpoint manually
    lons = np.append(np.hstack(lons), endlong)
    lats = np.append(np.hstack(lats), endlat)

    # check if input sample locations are within data availability area, only save if so
    north = config.region_of_interest["North"]
    east = config.region_of_interest["East"]
    south = config.region_of_interest["South"]
    west = config.region_of_interest["West"]
    poly = Polygon([(west, north), (west, south), (east, south), (east, north)])
    sample_lons = []
    sample_lats = []
    for i in range(len(lons)):
        if poly.contains(Point(lons[i], lats[i])):
            sample_lons.append(lons[i])
            sample_lats.append(lats[i])
    points = [
        Location(latitude=lat, longitude=lon)
        for lat, lon in zip(sample_lats, sample_lons, strict=True)
    ]
    return points
