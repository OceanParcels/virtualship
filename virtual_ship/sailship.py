"""sailship function."""

import os
from datetime import timedelta

import numpy as np
import pyproj
from shapely.geometry import Point, Polygon

from .costs import costs
from .instruments.argo_float import ArgoFloat, simulate_argo_floats
from .instruments.ctd import CTD, simulate_ctd
from .instruments.drifter import Drifter, simulate_drifters
from .instruments.adcp import simulate_adcp, SamplePoint as ADCPSamplePoint
from .instruments.ship_st import simulate_ship_st, SamplePoint as ShipSTSamplePoint
from .instruments.location import Location
from .postprocess import postprocess
from .virtual_ship_configuration import VirtualShipConfiguration


def sailship(config: VirtualShipConfiguration):
    """
    Use parcels to simulate the ship, take ctd_instruments and measure ADCP and underwaydata.

    :param config: The cruise configuration.
    """
    # Create fieldset and retreive final schip route as sample_lons and sample_lats
    adcp_fieldset = config.ctd_fieldset
    ship_st_fieldset = config.ctd_fieldset

    sample_lons, sample_lats = shiproute(config)
    print("Arrived in region of interest, starting to gather data.")

    # initialize drifters and argo floats
    drifter = 0
    drifters: list[Drifter] = []
    argo = 0
    argo_floats: list[ArgoFloat] = []
    ctd = 0
    ctds: list[CTD] = []

    route_points_dt = timedelta(minutes=5).total_seconds()
    adcp_sample_points = [
        ADCPSamplePoint(Location(latitude=lat, longitude=lon), n * route_points_dt)
        for n, (lat, lon) in enumerate(zip(sample_lats, sample_lons))
    ]
    ship_st_sample_points = [
        ShipSTSamplePoint(Location(latitude=lat, longitude=lon), n * route_points_dt)
        for n, (lat, lon) in enumerate(zip(sample_lats, sample_lons))
    ]

    ctd_min_depth = -config.ctd_fieldset.U.depth[0]
    argo_min_depth = -config.argo_float_fieldset.U.depth[0]
    drifter_min_depth = -config.drifter_fieldset.U.depth[0]

    # run the model for the length of the sample_lons list
    total_time = timedelta(hours=0).total_seconds()
    for i in range(len(sample_lons) - 1):

        if i % 96 == 0:
            print(f"Gathered data {timedelta(seconds=total_time)} hours since start.")

        # check if virtual ship is at a CTD station
        if ctd < len(config.CTD_locations):
            if (
                abs(sample_lons[i] - config.CTD_locations[ctd][0]) < 0.01
                and abs(sample_lats[i] - config.CTD_locations[ctd][1]) < 0.01
            ):
                ctds.append(
                    CTD(
                        location=Location(
                            latitude=config.CTD_locations[ctd][0],
                            longitude=config.CTD_locations[ctd][1],
                        ),
                        deployment_time=total_time,
                        min_depth=ctd_min_depth,
                        max_depth=-config.ctd_fieldset.U.depth[-1],
                    )
                )
                ctd += 1

                total_time += timedelta(
                    minutes=20
                ).total_seconds()  # Add 20 minutes for deployment

        # check if we are at a `drifter` deployment location
        if drifter < len(config.drifter_deploylocations):
            while (
                abs(sample_lons[i] - config.drifter_deploylocations[drifter][0]) < 0.01
                and abs(sample_lats[i] - config.drifter_deploylocations[drifter][1])
                < 0.01
            ):
                drifters.append(
                    Drifter(
                        location=Location(
                            latitude=config.drifter_deploylocations[drifter][0],
                            longitude=config.drifter_deploylocations[drifter][1],
                        ),
                        deployment_time=total_time,
                        min_depth=drifter_min_depth,
                    )
                )
                drifter += 1
                print(
                    f"Drifter {drifter} deployed at {sample_lons[i]}, {sample_lats[i]}"
                )
                if drifter == len(config.drifter_deploylocations):
                    break

        # check if we are at a argo deployment location
        if argo < len(config.argo_deploylocations):
            while (
                abs(sample_lons[i] - config.argo_deploylocations[argo][0]) < 0.01
                and abs(sample_lats[i] - config.argo_deploylocations[argo][1]) < 0.01
            ):
                argo_floats.append(
                    ArgoFloat(
                        location=Location(
                            latitude=config.argo_deploylocations[argo][0],
                            longitude=config.argo_deploylocations[argo][1],
                        ),
                        deployment_time=total_time,
                        min_depth=argo_min_depth,
                        max_depth=config.argo_characteristics["maxdepth"],
                        drift_depth=config.argo_characteristics["driftdepth"],
                        vertical_speed=config.argo_characteristics["vertical_speed"],
                        cycle_days=config.argo_characteristics["cycle_days"],
                        drift_days=config.argo_characteristics["drift_days"],
                    )
                )
                argo += 1
                print(f"Argo {argo} deployed at {sample_lons[i]}, {sample_lats[i]}")
                if argo == len(config.argo_deploylocations):
                    break

        # update timey
        total_time += route_points_dt

    print("Cruise has ended. Please wait for drifters and/or Argo floats to finish.")

    print("Simulating onboard salinity and temperature measurements.")
    simulate_ship_st(
        fieldset=ship_st_fieldset,
        out_file_name=os.path.join("results", "ship_st.zarr"),
        depth=-2,
        sample_points=ship_st_sample_points,
    )

    print("Simulating onboard ADCP.")
    simulate_adcp(
        fieldset=adcp_fieldset,
        out_file_name=os.path.join("results", "adcp.zarr"),
        max_depth=config.ADCP_settings["max_depth"],
        min_depth=-5,
        bin_size=config.ADCP_settings["bin_size_m"],
        sample_points=adcp_sample_points,
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

    cost = costs(config, total_time)
    print(
        f"This cruise took {timedelta(seconds=total_time)} and would have cost {cost:,.0f} euros."
    )


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


def shiproute(config):
    """
    Take in route coordinates and return lat and lon points within region of interest to sample.

    :param config: The cruise configuration.
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
        if distance > (cruise_speed * 60 * 5):
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
    return sample_lons, sample_lats
