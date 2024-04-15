import json
import os
import math
import numpy as np
import xarray as xr
import shutil
import datetime
from datetime import timedelta
from scipy.ndimage import uniform_filter1d
from virtual_ship.virtual_ship_configuration import VirtualShipConfiguration
from virtual_ship.costs import costs
from parcels import Field, FieldSet, JITParticle, Variable, ParticleSet, AdvectionRK4, StatusCode

def create_drifter_fieldset(config):
    '''Creates fieldset from netcdf files for drifters, returns fieldset with negative depth values'''

    datadirname = os.path.dirname(__file__)
    filenames = {
        "U": os.path.join(datadirname, "drifterdata_UV.nc"),
        "V": os.path.join(datadirname, "drifterdata_UV.nc"),
        "T": os.path.join(datadirname, "drifterdata_T.nc")}
    variables = {'U': 'uo', 'V': 'vo', 'T': 'thetao'}
    dimensions = {'lon': 'longitude', 'lat': 'latitude', 'time': 'time', 'depth': 'depth'}

    # create the fieldset and set interpolation methods
    fieldset = FieldSet.from_netcdf(filenames, variables, dimensions, allow_time_extrapolation=False)
    fieldset.T.interp_method = "linear_invdist_land_tracer"
    for g in fieldset.gridset.grids:
        if max(g.depth) > 0:
            g.depth = -g.depth  # make depth negative
    fieldset.mindepth = -fieldset.U.depth[0]  # uppermost layer in the hydrodynamic data
    return fieldset

def create_argo_fieldset(config):
    '''Creates fieldset from netcdf files for argo floats, returns fieldset with negative depth values'''

    datadirname = os.path.dirname(__file__)
    filenames = {
        "U": os.path.join(datadirname, "argodata_UV.nc"),
        "V": os.path.join(datadirname, "argodata_UV.nc"),
        "S": os.path.join(datadirname, "argodata_S.nc"),
        "T": os.path.join(datadirname, "argodata_T.nc")}
    variables = {'U': 'uo', 'V': 'vo', 'S': 'so', 'T': 'thetao'}
    dimensions = {'lon': 'longitude', 'lat': 'latitude', 'time': 'time', 'depth': 'depth'}

    # create the fieldset and set interpolation methods
    fieldset = FieldSet.from_netcdf(filenames, variables, dimensions, allow_time_extrapolation=False)
    fieldset.T.interp_method = "linear_invdist_land_tracer"
    for g in fieldset.gridset.grids:
        if max(g.depth) > 0:
            g.depth = -g.depth  # make depth negative
    fieldset.mindepth = -fieldset.U.depth[0]  # uppermost layer in the hydrodynamic data
    fieldset.add_constant('driftdepth', config.argo_characteristics["driftdepth"])
    fieldset.add_constant('maxdepth', config.argo_characteristics["maxdepth"])
    fieldset.add_constant('vertical_speed', config.argo_characteristics["vertical_speed"])
    fieldset.add_constant('cycle_days', config.argo_characteristics["cycle_days"])
    fieldset.add_constant('drift_days', config.argo_characteristics["drift_days"])
    return fieldset


def drifter_deployments(config, drifter_time):

    if len(config.drifter_deploylocations) > 0:

        fieldset = create_drifter_fieldset(config)

        # Create particle to sample water underway
        class DrifterParticle(JITParticle):
            """Define a new particle class that samples Temperature as a surface drifter"""
            temperature = Variable("temperature", initial=np.nan)

        # define function sampling Temperature
        def SampleT(particle, fieldset, time):
            particle.temperature = fieldset.T[time, particle.depth, particle.lat, particle.lon]

        def CheckError(particle, fieldset, time):
            if particle.state >= 50:  # This captures all Errors
                particle.delete()

        # initialize drifters
        lon = []
        lat = []
        for i in range(len(config.drifter_deploylocations)):
            lon.append(config.drifter_deploylocations[i][0])
            lat.append(config.drifter_deploylocations[i][1])
        time = drifter_time

        # Create and execute drifter particles
        pset = ParticleSet(fieldset=fieldset, pclass=DrifterParticle, lon=lon, lat=lat, depth=np.repeat(fieldset.mindepth,len(time)), time=time)
        output_file = pset.ParticleFile(name=os.path.join("results","Drifters.zarr"), outputdt=timedelta(hours=1))

        fieldset_endtime = fieldset.time_origin.fulltime(fieldset.U.grid.time_full[-1])
        drifter_endtime = np.array((datetime.datetime.strptime(config.requested_ship_time["start"],"%Y-%m-%dT%H:%M:%S") + timedelta(weeks=6))).astype('datetime64[ms]')

        pset.execute(
            [AdvectionRK4, SampleT, CheckError],
            endtime=min(fieldset_endtime, drifter_endtime), dt=timedelta(minutes=5),
            output_file=output_file
        )


def argo_deployments(config, argo_time):
    '''Deploys argo floats, returns results folder'''

    if len(config.argo_deploylocations) > 0:

        fieldset = create_argo_fieldset(config)

        # Define the new Kernel that mimics Argo vertical movement
        def ArgoVerticalMovement(particle, fieldset, time):

            if particle.cycle_phase == 0:
                # Phase 0: Sinking with vertical_speed until depth is driftdepth
                particle_ddepth += fieldset.vertical_speed * particle.dt
                if particle.depth + particle_ddepth <= fieldset.driftdepth:
                    particle_ddepth = fieldset.driftdepth - particle.depth
                    particle.cycle_phase = 1

            elif particle.cycle_phase == 1:
                # Phase 1: Drifting at depth for drifttime seconds
                particle.drift_age += particle.dt
                if particle.drift_age >= fieldset.drift_days * 86400:
                    particle.drift_age = 0  # reset drift_age for next cycle
                    particle.cycle_phase = 2

            elif particle.cycle_phase == 2:
                # Phase 2: Sinking further to maxdepth
                particle_ddepth += fieldset.vertical_speed * particle.dt
                if particle.depth + particle_ddepth <= fieldset.maxdepth:
                    particle_ddepth = fieldset.maxdepth - particle.depth
                    particle.cycle_phase = 3

            elif particle.cycle_phase == 3:
                # Phase 3: Rising with vertical_speed until at surface
                particle_ddepth -= fieldset.vertical_speed * particle.dt
                particle.cycle_age += particle.dt # solve issue of not updating cycle_age during ascent
                if particle.depth + particle_ddepth >= fieldset.mindepth:
                    particle_ddepth = fieldset.mindepth - particle.depth
                    particle.temperature = math.nan  # reset temperature to NaN at end of sampling cycle
                    particle.salinity = math.nan  # idem
                    particle.cycle_phase = 4
                else:
                    particle.temperature = fieldset.T[time, particle.depth, particle.lat, particle.lon]
                    particle.salinity = fieldset.S[time, particle.depth, particle.lat, particle.lon]

            elif particle.cycle_phase == 4:
                # Phase 4: Transmitting at surface until cycletime is reached
                if particle.cycle_age > fieldset.cycle_days * 86400:
                    particle.cycle_phase = 0
                    particle.cycle_age = 0

            if particle.state == StatusCode.Evaluate:
                particle.cycle_age += particle.dt  # update cycle_age

        def KeepAtSurface(particle, fieldset, time):
            # Prevent error when float reaches surface
            if particle.state == StatusCode.ErrorThroughSurface:
                particle.depth = fieldset.mindepth
                particle.state = StatusCode.Success

        def CheckError(particle, fieldset, time):
            if particle.state >= 50:  # This captures all Errors
                particle.delete()

        class ArgoParticle(JITParticle):
            cycle_phase = Variable("cycle_phase", dtype=np.int32, initial=0.0)
            cycle_age = Variable("cycle_age", dtype=np.float32, initial=0.0)
            drift_age = Variable("drift_age", dtype=np.float32, initial=0.0)
            salinity = Variable("salinity", initial=np.nan)
            temperature = Variable("temperature", initial=np.nan)

        # initialize argo floats
        lon = []
        lat = []
        for i in range(len(config.argo_deploylocations)):
            lon.append(config.argo_deploylocations[i][0])
            lat.append(config.argo_deploylocations[i][1])
        time = argo_time

        # Create and execute argo particles
        argoset = ParticleSet(fieldset=fieldset, pclass=ArgoParticle, lon=lon, lat=lat, depth=np.repeat(fieldset.mindepth,len(time)), time=time)
        argo_output_file = argoset.ParticleFile(name=os.path.join("results","Argos.zarr"), outputdt=timedelta(minutes=5), chunks=(1,500))
        fieldset_endtime = fieldset.time_origin.fulltime(fieldset.U.grid.time_full[-1])
        argo_endtime = np.array((datetime.datetime.strptime(config.requested_ship_time["start"],"%Y-%m-%dT%H:%M:%S") + timedelta(weeks=6))).astype('datetime64[ms]')

        argoset.execute(
            [ArgoVerticalMovement, AdvectionRK4, KeepAtSurface, CheckError],  # list of kernels to be executed
            endtime=min(fieldset_endtime, argo_endtime), dt=timedelta(minutes=5),
            output_file=argo_output_file
        )


def postprocess():
    '''Postprocesses CTD data and writes to csv files'''

    if os.path.isdir(os.path.join("results","CTDs")):
        i = 0
        filenames = os.listdir(os.path.join("results","CTDs"))
        for filename in sorted(filenames):
            if filename.endswith(".zarr"):
                try: #too many errors, just skip the faulty zarr files
                    i += 1
                    # Open output and read to x, y, z
                    ds = xr.open_zarr(os.path.join("results","CTDs",filename))
                    x = ds["lon"][:].squeeze()
                    y = ds["lat"][:].squeeze()
                    z = ds["z"][:].squeeze()
                    time = ds["time"][:].squeeze()
                    T = ds["temperature"][:].squeeze()
                    S = ds["salinity"][:].squeeze()
                    ds.close()

                    random_walk = np.random.random()/10
                    z_norm = (z-np.min(z))/(np.max(z)-np.min(z))
                    t_norm = np.linspace(0, 1, num=len(time))
                    # add smoothed random noise scaled with depth
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
                    header = f"pressure [dbar],temperature [degC],salinity [g kg-1]"
                    data = np.column_stack([-z, T, S])
                    new_line = '\n'
                    np.savetxt(f"{os.path.join('results','CTDs','CTD_station_')}{i}.csv", data, fmt="%.4f", header=header, delimiter=',',
                                comments=f'longitude,{x[0].values},"{x.attrs}"{new_line}latitude,{y[0].values},"{y.attrs}"{new_line}start time,{time[0].values}{new_line}end time,{time[-1].values}{new_line}')
                    shutil.rmtree(filename.path)
                except TypeError:
                    print(f"CTD file {filename} seems faulty, skipping.")
                    continue
        print("CTD data postprocessed.")