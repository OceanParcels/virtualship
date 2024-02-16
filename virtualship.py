import json
import os
import math
import numpy as np
import xarray as xr
import pyproj
from datetime import timedelta
from shapely.geometry import Point, Polygon
from scipy.ndimage import uniform_filter1d
from parcels import Field, FieldSet, JITParticle, Variable, ParticleSet, AdvectionRK4, StatusCode


class VirtualShipConfiguration:
    def __init__(self, json_file):
        with open(os.path.join(os.path.dirname(__file__), json_file), 'r') as file:
            json_input = json.loads(file.read())
            for key in json_input:
                setattr(self, key, json_input[key])

        # Create a polygon from the region of interest to check coordinates
        north = self.region_of_interest["North"]
        east = self.region_of_interest["East"]
        south = self.region_of_interest["South"]
        west = self.region_of_interest["West"]
        poly = Polygon([(west, north), (west, south), (east, south), (east, north)])
        # validate input, raise ValueErrors if invalid
        if self.region_of_interest["North"] > 90 or self.region_of_interest["South"] < -90 or self.region_of_interest["East"] > 180 or self.region_of_interest["West"] < -180:
            raise ValueError("Invalid coordinates in region of interest")
        if len(self.route_coordinates) < 2:
            raise ValueError("Route needs to consist of at least 2 longitude-latitude coordinate sets")
        for coord in self.route_coordinates:
            if coord[1] > 90 or coord[1] < -90 or coord[0] > 180 or coord[0] < -180:
                raise ValueError("Invalid coordinates in route")
            if not poly.contains(Point(coord)):
                raise ValueError("Route coordinates need to be within the region of interest")
        if not len(self.CTD_locations) == 0:
            for coord in self.CTD_locations:
                if coord not in self.route_coordinates:
                    raise ValueError("CTD coordinates should be on the route")
                if coord[1] > 90 or coord[1] < -90 or coord[0] > 180 or coord[0] < -180:
                    raise ValueError("Invalid coordinates in route")
                if not poly.contains(Point(coord)):
                    raise ValueError("CTD coordinates need to be within the region of interest")
        if not len(self.drifter_deploylocations) == 0:
            for coord in self.drifter_deploylocations:
                if coord not in self.route_coordinates:
                    raise ValueError("Drifter coordinates should be on the route")
                if coord[1] > 90 or coord[1] < -90 or coord[0] > 180 or coord[0] < -180:
                    raise ValueError("Invalid coordinates in route")
                if not poly.contains(Point(coord)):
                    raise ValueError("Drifter coordinates need to be within the region of interest")
        if not len(self.argo_deploylocations) == 0:
            for coord in self.argo_deploylocations:
                if coord not in self.route_coordinates:
                    raise ValueError("argo coordinates should be on the route")
                if coord[1] > 90 or coord[1] < -90 or coord[0] > 180 or coord[0] < -180:
                    raise ValueError("Invalid coordinates in route")
                if not poly.contains(Point(coord)):
                    raise ValueError("argo coordinates need to be within the region of interest")
        if not isinstance(self.underway_data, bool):
            raise ValueError("Underway data needs to be true or false")
        if not isinstance(self.ADCP_data, bool):
            raise ValueError("ADCP data needs to be true or false")
        if self.ADCP_settings['bin_size_m'] < 0 or self.ADCP_settings['bin_size_m'] > 24:
            raise ValueError("Invalid bin size for ADCP")
        if self.ADCP_settings['max_depth'] > 0:
            raise ValueError("Invalid depth for ADCP")
        if self.argo_characteristics['driftdepth'] > 0 or self.argo_characteristics['driftdepth'] < -2000:
            raise ValueError("Invalid drift depth for argo")
        if self.argo_characteristics['maxdepth'] > 0 or self.argo_characteristics['maxdepth'] < -2000:
            raise ValueError("Invalid max depth for argo")
        if self.argo_characteristics['vertical_speed'] > 0:
            raise ValueError("Specify a negative vertical speed for argo")
        if self.argo_characteristics['cycle_days'] < 0:
            raise ValueError("Specify a postitive number of cycle days for argo")
        if self.argo_characteristics['drift_days'] < 0:
            raise ValueError("Specify a postitive number of drift days for argo")


def shiproute(config):
    '''Takes in route coordinates and returns lat and lon points within region of interest to sample'''

    # Initialize lists to store intermediate points
    lons = []
    lats = []

    # Loop over station coordinates and calculate intermediate points along great circle path
    for i in (range(len(config.route_coordinates)-1)):
        startlong = config.route_coordinates[i][0]
        startlat = config.route_coordinates[i][1]
        endlong = config.route_coordinates[i+1][0]
        endlat = config.route_coordinates[i+1][1]

        # calculate line string along path with segments every 5 min = 1545 m for ADCP measurements
        geod = pyproj.Geod(ellps='WGS84')
        azimuth1, azimuth2, distance = geod.inv(startlong, startlat, endlong, endlat)
        if distance > 1545:
            r = geod.inv_intermediate(startlong, startlat, endlong, endlat, del_s=1545, initial_idx=0, return_back_azimuth=False)
            lons = np.append(lons, r.lons) # stored as a list of arrays
            lats = np.append(lats, r.lats)

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

def create_fieldset():
    datadirname = os.path.dirname(__file__)
    filenames = {
        "U": f"{datadirname}studentdata_UV.nc",
        "V": f"{datadirname}studentdata_UV.nc",
        "S": f"{datadirname}studentdata_S.nc",
        "T": f"{datadirname}studentdata_T.nc"}
    variables = {'U': 'uo', 'V': 'vo', 'S': 'so', 'T': 'thetao'}
    dimensions = {'lon': 'longitude', 'lat': 'latitude', 'time': 'time', 'depth': 'depth'}

    # create the fieldset and set interpolation methods
    fieldset = FieldSet.from_netcdf(filenames, variables, dimensions)
    fieldset.T.interp_method = "linear_invdist_land_tracer"
    fieldset.S.interp_method = "linear_invdist_land_tracer"
    for g in fieldset.gridset.grids:
        if max(g.depth) > 0:
            g.depth = -g.depth  # make depth negative

    # add bathymetry data to the fieldset for CTD cast
    bathymetry_file = f"{datadirname}GLO-MFC_001_024_mask_bathy.nc"
    bathymetry_variables = ('bathymetry', 'deptho')
    bathymetry_dimensions = {'lon': 'longitude', 'lat': 'latitude'}
    bathymetry_field = Field.from_netcdf(bathymetry_file, bathymetry_variables, bathymetry_dimensions)
    fieldset.add_field(bathymetry_field)
    # read in data already
    fieldset.computeTimeChunk(0,1)
    return fieldset

def sailship(config):
    '''Uses parcels to simulate the ship, take CTDs and measure ADCP and underwaydata, returns results folder'''

    # Create fieldset and retreive final schip route as sample_lons and sample_lats
    fieldset = create_fieldset()
    sample_lons, sample_lats = shiproute(config)
    print("Arrived in region of interest, starting to gather data")

    # Create ADCP like particles to sample the ocean
    class ADCPParticle(JITParticle):
        """Define a new particle class that does ADCP like measurements"""
        U = Variable('U', dtype=np.float32, initial=0.0)
        V = Variable('V', dtype=np.float32, initial=0.0)

    # define ADCP sampling function without conversion (because of A grid)
    def SampleVel(particle, fieldset, time):
        particle.U, particle.V = fieldset.UV.eval(time, particle.depth, particle.lat, particle.lon, applyConversion=False)
        # particle.V = fieldset.V.eval(time, particle.depth, particle.lat, particle.lon, applyConversion=False)

    # Create particle to sample water underway
    class UnderwayDataParticle(JITParticle):
        """Define a new particle class that samples water directly under the hull"""
        salinity = Variable("salinity", initial=np.nan)
        temperature = Variable("temperature", initial=np.nan)

    # Create CTD like particles to sample the ocean
    class CTDParticle(JITParticle):
        """Define a new particle class that does CTD like measurements"""
        salinity = Variable("salinity", initial=np.nan)
        temperature = Variable("temperature", initial=np.nan)
        # pressure = Variable("pressure", initial=np.nan)
        raising = Variable("raising", dtype=np.int32, initial=0.0)

    # define function lowering and raising CTD
    def CTDcast(particle, fieldset, time):
        seafloor = fieldset.bathymetry[time, particle.depth, particle.lat, particle.lon]
        vertical_speed = 1.0  # sink and rise speed in m/s

        if particle.raising == 0:
            # Sinking with vertical_speed until near seafloor
            particle_ddepth = vertical_speed * particle.dt
            if particle.depth >= 200: #TODO remove 200: (seafloor - 20):
                particle.raising = 1

        if particle.raising == 1:
            # Rising with vertical_speed until depth is 2 m
            if particle.depth > 2:
                particle_ddepth = -vertical_speed * particle.dt
                if particle.depth + particle_ddepth <= 2:
                    # to break the loop ...
                    particle.state = 41
                    print("CTD cast finished")

    # define function sampling Salinity
    def SampleS(particle, fieldset, time):
        particle.salinity = fieldset.S[time, particle.depth, particle.lat, particle.lon]

    # define function sampling Temperature
    def SampleT(particle, fieldset, time):
        particle.temperature = fieldset.T[time, particle.depth, particle.lat, particle.lon]

    # # define function sampling Pressure
    # def SampleP(particle, fieldset, time):
    #     particle.pressure = fieldset.P[time, particle.depth, particle.lat, particle.lon]

    # Create ADCP like particleset and output file
    ADCP_bins = np.arange(config.ADCP_settings["max_depth"], -5, config.ADCP_settings["bin_size_m"])
    vert_particles = len(ADCP_bins)
    pset_ADCP = ParticleSet.from_list(
        fieldset=fieldset, pclass=ADCPParticle, lon=np.full(vert_particles,sample_lons[0]), lat=np.full(vert_particles,sample_lats[0]), depth=ADCP_bins, time=0
    )
    adcp_output_file = pset_ADCP.ParticleFile(name="./results/sailship_ADCP.zarr")
    adcp_dt = timedelta(minutes=5).total_seconds() # timestep of ADCP output, every 5 min

    # Create underway particle
    pset_UnderwayData = ParticleSet.from_list(
        fieldset=fieldset, pclass=UnderwayDataParticle, lon=sample_lons[0], lat=sample_lats[0], depth=-2, time=0
    )
    UnderwayData_output_file = pset_UnderwayData.ParticleFile(name="./results/sailship_UnderwayData.zarr")

    # initialize CTD station number and time
    total_time = timedelta(hours=0).total_seconds()
    ctd = 0
    ctd_dt = timedelta(seconds=10) # timestep of CTD output reflecting post-process binning into 10m bins

    # initialize drifters and argo floats
    drifter = 0
    drifter_time = []
    argo = 0
    argo_time = []

    # run the model for the length of the sample_lons list
    for i in range(len(sample_lons)-1):

        # execute the ADCP kernels to sample U and V and underway T and S
        pset_ADCP.execute(SampleVel, dt=adcp_dt, runtime=1, verbose_progress=False)
        adcp_output_file.write(pset_ADCP, time=pset_ADCP[0].time)
        pset_UnderwayData.execute([SampleS, SampleT], dt=adcp_dt, runtime=1, verbose_progress=False)
        UnderwayData_output_file.write(pset_UnderwayData, time=pset_ADCP[0].time)

        # check if virtual ship is at a CTD station
        if ctd < len(config.CTD_locations):
            if (sample_lons[i] - config.CTD_locations[ctd][0]) < 0.001 and (sample_lats[i] - config.CTD_locations[ctd][1]) < 0.001:
                ctd += 1

                # release CTD particle
                pset_CTD = ParticleSet(fieldset=fieldset, pclass=CTDParticle, lon=sample_lons[i], lat=sample_lats[i], depth=-2, time=total_time)

                # create a ParticleFile to store the CTD output
                ctd_output_file = pset_CTD.ParticleFile(name=f"./results/CTD_{ctd}.zarr", outputdt=ctd_dt)

                # record the temperature and salinity of the particle
                pset_CTD.execute([SampleS, SampleT, CTDcast], runtime=timedelta(hours=4), dt=ctd_dt, output_file=ctd_output_file, verbose_progress=False)
                total_time = pset_CTD.time[0] + timedelta(minutes=20).total_seconds() # add CTD time and 20 minutes for deployment

        # check if we are at a drifter deployment location
        if drifter < len(config.drifter_deploylocations):
            while (sample_lons[i] - config.drifter_deploylocations[drifter][0]) < 0.01 and (sample_lats[i] - config.drifter_deploylocations[drifter][1]) < 0.01:
                drifter_time.append(total_time)
                drifter += 1
                if drifter == len(config.drifter_deploylocations):
                    break

        # check if we are at a argo deployment location
        if argo < len(config.argo_deploylocations):
            while (sample_lons[i] - config.argo_deploylocations[argo][0]) < 0.01 and (sample_lats[i] - config.argo_deploylocations[argo][1]) < 0.01:
                argo_time.append(total_time)
                argo += 1
                if argo == len(config.argo_deploylocations):
                    break

        # update the particle time and location
        pset_ADCP.lon_nextloop[:] = sample_lons[i+1]
        pset_ADCP.lat_nextloop[:] = sample_lats[i+1]
        pset_UnderwayData.lon_nextloop[:] = sample_lons[i+1]
        pset_UnderwayData.lat_nextloop[:] = sample_lats[i+1]

        total_time += adcp_dt
        pset_ADCP.time_nextloop[:] = total_time
        pset_UnderwayData.time_nextloop[:] = total_time
        if i % 24 == 0:
            print(f"Gathered data {total_time/3600:.2f} hours since start")

    # write the final locations of the ADCP and Underway data particles
    pset_ADCP.execute(SampleVel, dt=adcp_dt, runtime=1, verbose_progress=False)
    adcp_output_file.write_latest_locations(pset_ADCP, time=total_time)
    pset_UnderwayData.execute([SampleS, SampleT], dt=adcp_dt, runtime=1, verbose_progress=False)
    UnderwayData_output_file.write_latest_locations(pset_UnderwayData, time=total_time)
    print("Cruise has ended. Please wait for drifters and/or Argo floats to finish.")

    return drifter_time, argo_time

def deployments(config, difter_time, argo_time):
    '''Deploys drifters and argo floats, returns results folder'''

    fieldset = create_fieldset()

    # Create particle to sample water underway
    class DrifterParticle(JITParticle):
        """Define a new particle class that samples Temperature as a surface drifter"""
        temperature = Variable("temperature", initial=np.nan)

    # define function sampling Temperature
    def SampleT(particle, fieldset, time):
        particle.temperature = fieldset.T[time, particle.depth, particle.lat, particle.lon]

    # Define the new Kernel that mimics Argo vertical movement
    def ArgoVerticalMovement(particle, fieldset, time):
        driftdepth = config.driftdepth  # maximum depth in m
        maxdepth = config.maxdepth  # maximum depth in m
        vertical_speed = config.vertical_speed  # sink and rise speed in m/s
        cycletime = config.cycle_days * 86400  # total time of cycle in seconds
        drifttime = config.drift_days * 86400  # time of deep drift in seconds

        if particle.cycle_phase == 0:
            # Phase 0: Sinking with vertical_speed until depth is driftdepth
            particle_ddepth += vertical_speed * particle.dt
            if particle.depth >= driftdepth:
                particle.cycle_phase = 1

        elif particle.cycle_phase == 1:
            # Phase 1: Drifting at depth for drifttime seconds
            particle.drift_age += particle.dt
            if particle.drift_age >= drifttime:
                particle.drift_age = 0  # reset drift_age for next cycle
                particle.cycle_phase = 2

        elif particle.cycle_phase == 2:
            # Phase 2: Sinking further to maxdepth
            particle_ddepth += vertical_speed * particle.dt
            if particle.depth >= maxdepth:
                particle.cycle_phase = 3

        elif particle.cycle_phase == 3:
            # Phase 3: Rising with vertical_speed until at surface
            particle_ddepth -= vertical_speed * particle.dt
            particle.cycle_age += particle.dt # solve issue of not updating cycle_age during ascent
            if particle.depth <= fieldset.mindepth:
                particle.depth = fieldset.mindepth
                particle.temp = math.nan  # reset temperature to NaN at end of sampling cycle
                particle.salt = math.nan  # idem
                particle.cycle_phase = 4
            else:
                particle.temp = fieldset.T[time, particle.depth, particle.lat, particle.lon]
                particle.salt = fieldset.S[time, particle.depth, particle.lat, particle.lon]

        elif particle.cycle_phase == 4:
            # Phase 4: Transmitting at surface until cycletime is reached
            if particle.cycle_age > cycletime:
                particle.cycle_phase = 0
                particle.cycle_age = 0

        if particle.state == StatusCode.Evaluate:
            particle.cycle_age += particle.dt  # update cycle_age


    def KeepAtSurface(particle, fieldset, time):
        # Prevent error when float reaches surface
        if particle.state == StatusCode.ErrorThroughSurface:
            particle.depth = fieldset.mindepth
            particle.state = StatusCode.Success

    class ArgoParticle(JITParticle):
        cycle_phase = Variable("cycle_phase", dtype=np.int32, initial=0.0)
        cycle_age = Variable("cycle_age", dtype=np.float32, initial=0.0)
        drift_age = Variable("drift_age", dtype=np.float32, initial=0.0)
        salinity = Variable("salinity", initial=np.nan)
        temperature = Variable("temperature", initial=np.nan)

    # initialize drifters and argo floats
    lon = []
    lat = []
    for i in range(len(config.drifter_deploylocations)):
        lon.append(config.drifter_deploylocations[i][0])
        lat.append(config.drifter_deploylocations[i][1])
    time = drifter_time

    # Create and execute drifter particles
    pset = ParticleSet(fieldset=fieldset, pclass=DrifterParticle, lon=lon, lat=lat, time=time)
    output_file = pset.ParticleFile(name="./results/Drifters.zarr", outputdt=timedelta(hours=1))
    pset.execute([AdvectionRK4, SampleT], runtime=timedelta(hours=24), dt=timedelta(minutes=5), output_file=output_file)

    # initialize drifters and argo floats
    lon = []
    lat = []
    for i in range(len(config.argo_deploylocations)):
        lon.append(config.argo_deploylocations[i][0])
        lat.append(config.argo_deploylocations[i][1])
    time = argo_time

    # Create and execute argo particles
    argoset = ParticleSet(fieldset=fieldset, pclass=ArgoParticle, lon=lon, lat=lat, time=time)
    argo_output_file = argoset.ParticleFile(name="./results/Argo.zarr", outputdt=timedelta(minutes=5), chunks=(1,500))
    argoset.execute(
        [ArgoVerticalMovement, AdvectionRK4, KeepAtSurface],  # list of kernels to be executed
        runtime=timedelta(weeks=6), dt=timedelta(minutes=5),
        output_file=argo_output_file
    )



def postprocess(ctd):

    # rewrite CTD data to cvs
    for i in range(1, ctd+1):

        # Open output and read to x, y, z
        ds = xr.open_zarr(f"./results/CTD_{i}.zarr")
        x = ds["lon"][:].squeeze()
        y = ds["lat"][:].squeeze()
        z = ds["z"][:].squeeze()
        time = ds["time"][:].squeeze()
        T = ds["temperature"][:].squeeze()
        S = ds["salinity"][:].squeeze()
        ds.close()

        # add some noise
        random_walk = np.random.random()/10
        z_norm = (z-np.min(z))/(np.max(z)-np.min(z))
        t_norm = np.linspace(0, 1, num=len(time))
        # dS = abs(np.append(0, np.diff(S))) # scale noise with gradient
        # for j in range(5, 0, -1):
        #     dS[dS<1*10**-j] = 0.5-j/10
        # add smoothed random noise scaled with depth (and OPTIONAL with gradient for S)
        # and random (reversed) diversion from initial through time scaled with depth
        S = S + uniform_filter1d(
            np.random.random(S.shape)/5*(1-z_norm) +
            random_walk*(np.max(S).values - np.min(S).values)*(1-z_norm)*t_norm/10,
            max(int(len(time)/40), 1))
        T = T + uniform_filter1d(
            np.random.random(T.shape)*5*(1-z_norm) -
            random_walk/2*(np.max(T).values - np.min(T).values)*(1-z_norm)*t_norm/10,
            max(int(len(time)/20), 1))

        # reshaping data to export to csv
        header = f"'pressure [hPa]','temperature [degC]', 'salinity [g kg-1]'"
        data = np.column_stack([(z/10), T, S])
        new_line = '\n'
        np.savetxt(f"./results/CTD_station_{i}.csv", data, fmt="%.4f", header=header, delimiter=',',
                comments=f'{x.attrs} {x[0].values}{new_line}{y.attrs}{y[0].values}{new_line}start time: {time[0].values}{new_line}end time: {time[-1].values}{new_line}')


if __name__ == '__main__':
    config = VirtualShipConfiguration('student_input.json')
    # drifter_time, argo_time = sailship(config)
    # #tmp
    drifter_time = []
    argo_time = [0, 1]
    deployments(config, drifter_time, argo_time)