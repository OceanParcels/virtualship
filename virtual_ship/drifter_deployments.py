import os
import numpy as np
import datetime
from datetime import timedelta
from parcels import FieldSet, JITParticle, Variable, ParticleSet, AdvectionRK4

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