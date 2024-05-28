"""sailship function."""

import os
from datetime import timedelta

import numpy as np
import pyproj
from parcels import Field, FieldSet, JITParticle, ParticleSet, Variable
from shapely.geometry import Point, Polygon

from .costs import costs
from .drifter_deployments import drifter_deployments
from .instruments.argo_float import ArgoFloat, simulate_argo_floats
from .instruments.location import Location
from .postprocess import postprocess
from .virtual_ship_configuration import VirtualShipConfiguration


def sailship(config: VirtualShipConfiguration):
    """
    Use parcels to simulate the ship, take CTDs and measure ADCP and underwaydata.

    :param config: The cruise configuration.
    :raises NotImplementedError: TODO
    """
    # Create fieldset and retreive final schip route as sample_lons and sample_lats
    fieldset = config.ctd_fieldset  # create_fieldset(config, data_dir)

    sample_lons, sample_lats = shiproute(config)
    print("Arrived in region of interest, starting to gather data.")

    # Create Vessel Mounted ADCP like particles to sample the ocean
    class VM_ADCPParticle(JITParticle):
        """Define a new particle class that does Vessel Mounted ADCP like measurements."""

        U = Variable("U", dtype=np.float32, initial=0.0)
        V = Variable("V", dtype=np.float32, initial=0.0)

    # Create particle to sample water underway
    class UnderwayDataParticle(JITParticle):
        """Define a new particle class that samples water directly under the hull."""

        salinity = Variable("salinity", initial=np.nan)
        temperature = Variable("temperature", initial=np.nan)

    # Create CTD like particles to sample the ocean
    class CTDParticle(JITParticle):
        """Define a new particle class that does CTD like measurements."""

        salinity = Variable("salinity", initial=np.nan)
        temperature = Variable("temperature", initial=np.nan)
        raising = Variable("raising", dtype=np.int32, initial=0.0)

    # define ADCP sampling function without conversion (because of A grid)
    def SampleVel(particle, fieldset, time):
        particle.U, particle.V = fieldset.UV.eval(
            time, particle.depth, particle.lat, particle.lon, applyConversion=False
        )

    # define function lowering and raising CTD
    def CTDcast(particle, fieldset, time):
        # TODO question: if is executed every time... move outside function? Not if "drifting" now possible
        if (
            -fieldset.bathymetry[time, particle.depth, particle.lat, particle.lon]
            > fieldset.max_depth
        ):
            maxdepth = (
                -fieldset.bathymetry[time, particle.depth, particle.lat, particle.lon]
                + 20
            )
        else:
            maxdepth = fieldset.max_depth
        winch_speed = -1.0  # sink and rise speed in m/s

        if particle.raising == 0:
            # Sinking with winch_speed until near seafloor
            particle_ddepth = winch_speed * particle.dt
            if particle.depth <= maxdepth:
                particle.raising = 1

        if particle.raising == 1:
            # Rising with winch_speed until depth is -2 m
            if particle.depth < -2:
                particle_ddepth = -winch_speed * particle.dt
                if particle.depth + particle_ddepth >= -2:
                    # to break the loop ...
                    particle.state = 41
                    print("CTD cast finished.")

    # define function sampling Salinity
    def SampleS(particle, fieldset, time):
        particle.salinity = fieldset.S[time, particle.depth, particle.lat, particle.lon]

    # define function sampling Temperature
    def SampleT(particle, fieldset, time):
        particle.temperature = fieldset.T[
            time, particle.depth, particle.lat, particle.lon
        ]

    # Create ADCP like particleset and output file
    ADCP_bins = np.arange(
        config.ADCP_settings["max_depth"], -5, config.ADCP_settings["bin_size_m"]
    )
    vert_particles = len(ADCP_bins)
    pset_ADCP = ParticleSet.from_list(
        fieldset=fieldset,
        pclass=VM_ADCPParticle,
        lon=np.full(vert_particles, sample_lons[0]),
        lat=np.full(vert_particles, sample_lats[0]),
        depth=ADCP_bins,
        time=0,
    )
    adcp_output_file = pset_ADCP.ParticleFile(name=os.path.join("results", "ADCP.zarr"))
    adcp_dt = timedelta(
        minutes=5
    ).total_seconds()  # timestep of ADCP output, every 5 min

    # Create underway particle
    pset_UnderwayData = ParticleSet.from_list(
        fieldset=fieldset,
        pclass=UnderwayDataParticle,
        lon=sample_lons[0],
        lat=sample_lats[0],
        depth=-2,
        time=0,
    )
    UnderwayData_output_file = pset_UnderwayData.ParticleFile(
        name=os.path.join("results", "UnderwayData.zarr")
    )

    # initialize CTD station number and time
    total_time = timedelta(hours=0).total_seconds()
    ctd = 0
    ctd_dt = timedelta(
        seconds=10
    )  # timestep of CTD output reflecting post-process binning into 10m bins

    # initialize drifters and argo floats
    drifter = 0
    drifter_time = []
    argo = 0
    argo_floats: list[ArgoFloat] = []

    ARGO_MIN_DEPTH = -config.argo_float_fieldset.U.depth[0]

    # run the model for the length of the sample_lons list
    for i in range(len(sample_lons) - 1):

        if i % 96 == 0:
            print(f"Gathered data {timedelta(seconds=total_time)} hours since start.")

        # execute the ADCP kernels to sample U and V and underway T and S
        if config.ADCP_data:
            pset_ADCP.execute(
                [SampleVel], dt=adcp_dt, runtime=1, verbose_progress=False
            )
            adcp_output_file.write(pset_ADCP, time=pset_ADCP[0].time)
        if config.underway_data:
            pset_UnderwayData.execute(
                [SampleS, SampleT], dt=adcp_dt, runtime=1, verbose_progress=False
            )
            UnderwayData_output_file.write(pset_UnderwayData, time=pset_ADCP[0].time)
        if pset_ADCP[0].time > fieldset.maxtime:
            print(
                "Ship time is over, waiting for drifters and/or Argo floats to finish."
            )
            raise NotImplementedError()
            # return drifter_time, argo_time

        # check if virtual ship is at a CTD station
        if ctd < len(config.CTD_locations):
            if (
                abs(sample_lons[i] - config.CTD_locations[ctd][0]) < 0.001
                and abs(sample_lats[i] - config.CTD_locations[ctd][1]) < 0.001
            ):
                ctd += 1

                # release CTD particle
                pset_CTD = ParticleSet(
                    fieldset=fieldset,
                    pclass=CTDParticle,
                    lon=sample_lons[i],
                    lat=sample_lats[i],
                    depth=fieldset.mindepth,
                    time=total_time,
                )

                # create a ParticleFile to store the CTD output
                ctd_output_file = pset_CTD.ParticleFile(
                    name=f"{os.path.join('results', 'CTDs', 'CTD_')}{ctd:03d}.zarr",
                    outputdt=ctd_dt,
                )

                # record the temperature and salinity of the particle
                pset_CTD.execute(
                    [SampleS, SampleT, CTDcast],
                    runtime=timedelta(hours=8),
                    dt=ctd_dt,
                    output_file=ctd_output_file,
                    verbose_progress=False,
                )
                total_time = (
                    pset_CTD.time[0] + timedelta(minutes=20).total_seconds()
                )  # add CTD time and 20 minutes for deployment

        # check if we are at a drifter deployment location
        if drifter < len(config.drifter_deploylocations):
            while (
                abs(sample_lons[i] - config.drifter_deploylocations[drifter][0]) < 0.01
                and abs(sample_lats[i] - config.drifter_deploylocations[drifter][1])
                < 0.01
            ):
                drifter_time.append(total_time)
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
                        min_depth=ARGO_MIN_DEPTH,
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

        # update the particle time and location
        pset_ADCP.lon_nextloop[:] = sample_lons[i + 1]
        pset_ADCP.lat_nextloop[:] = sample_lats[i + 1]
        pset_UnderwayData.lon_nextloop[:] = sample_lons[i + 1]
        pset_UnderwayData.lat_nextloop[:] = sample_lats[i + 1]

        total_time += adcp_dt
        pset_ADCP.time_nextloop[:] = total_time
        pset_UnderwayData.time_nextloop[:] = total_time

    # write the final locations of the ADCP and Underway data particles
    if config.ADCP_data:
        pset_ADCP.execute(SampleVel, dt=adcp_dt, runtime=1, verbose_progress=False)
        adcp_output_file.write_latest_locations(pset_ADCP, time=total_time)
    if config.underway_data:
        pset_UnderwayData.execute(
            [SampleS, SampleT], dt=adcp_dt, runtime=1, verbose_progress=False
        )
        UnderwayData_output_file.write_latest_locations(
            pset_UnderwayData, time=total_time
        )
    print("Cruise has ended. Please wait for drifters and/or Argo floats to finish.")

    # simulate drifter deployments
    drifter_deployments(config, drifter_time)

    # simulate argo deployments
    simulate_argo_floats(
        argo_floats=argo_floats,
        fieldset=config.argo_float_fieldset,
        out_file_name=os.path.join("results", "argo_floats.zarr"),
    )

    # convert CTD data to CSV
    postprocess()

    print("All data has been gathered and postprocessed, returning home.")

    cost = costs(config, total_time)
    print(
        f"This cruise took {timedelta(seconds=total_time)} and would have cost {cost:,.0f} euros."
    )


def create_fieldset(config, data_dir: str):
    """
    Create fieldset from netcdf files and adds bathymetry data for CTD cast, returns fieldset with negative depth values.

    :param config: The cruise configuration.
    :param data_dir: TODO
    :returns: The fieldset.
    :raises ValueError: If downloaded data is not as expected.
    """
    filenames = {
        "U": os.path.join(data_dir, "studentdata_UV.nc"),
        "V": os.path.join(data_dir, "studentdata_UV.nc"),
        "S": os.path.join(data_dir, "studentdata_S.nc"),
        "T": os.path.join(data_dir, "studentdata_T.nc"),
    }
    variables = {"U": "uo", "V": "vo", "S": "so", "T": "thetao"}
    dimensions = {
        "lon": "longitude",
        "lat": "latitude",
        "time": "time",
        "depth": "depth",
    }

    # create the fieldset and set interpolation methods
    fieldset = FieldSet.from_netcdf(
        filenames, variables, dimensions, allow_time_extrapolation=True
    )
    fieldset.T.interp_method = "linear_invdist_land_tracer"
    fieldset.S.interp_method = "linear_invdist_land_tracer"
    for g in fieldset.gridset.grids:
        if max(g.depth) > 0:
            g.depth = -g.depth  # make depth negative
    fieldset.mindepth = -fieldset.U.depth[0]  # uppermost layer in the hydrodynamic data
    if config.CTD_settings["max_depth"] == "max":
        fieldset.add_constant("max_depth", -fieldset.U.depth[-1])
    else:
        fieldset.add_constant("max_depth", config.CTD_settings["max_depth"])
    fieldset.add_constant("maxtime", fieldset.U.grid.time_full[-1])

    # add bathymetry data to the fieldset for CTD cast
    bathymetry_file = os.path.join(data_dir, "GLO-MFC_001_024_mask_bathy.nc")
    bathymetry_variables = ("bathymetry", "deptho")
    bathymetry_dimensions = {"lon": "longitude", "lat": "latitude"}
    bathymetry_field = Field.from_netcdf(
        bathymetry_file, bathymetry_variables, bathymetry_dimensions
    )
    fieldset.add_field(bathymetry_field)
    # read in data already
    fieldset.computeTimeChunk(0, 1)

    if fieldset.U.lon.min() > config.region_of_interest["West"]:
        raise ValueError(
            "FieldSet western boundary is outside region of interest. Please run download_data.py again."
        )
    if fieldset.U.lon.max() < config.region_of_interest["East"]:
        raise ValueError(
            "FieldSet eastern boundary is outside region of interest. Please run download_data.py again."
        )
    if fieldset.U.lat.min() > config.region_of_interest["South"]:
        raise ValueError(
            "FieldSet southern boundary is outside region of interest. Please run download_data.py again."
        )
    if fieldset.U.lat.max() < config.region_of_interest["North"]:
        raise ValueError(
            "FieldSet northern boundary is outside region of interest. Please run download_data.py again."
        )
    return fieldset


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
