"""argo_deployments function."""

import datetime
import math
import os
from datetime import timedelta

import numpy as np
from parcels import (
    AdvectionRK4,
    FieldSet,
    JITParticle,
    ParticleSet,
    StatusCode,
    Variable,
)

from .virtual_ship_configuration import VirtualShipConfiguration


def argo_deployments(config: VirtualShipConfiguration, argo_time):
    """
    Deploy argo floats.

    :param config: The cruise configuration.
    :param argo_time: TODO
    """
    # particle_* such as particle_ddepth are local variables defined by parcels.
    # See https://docs.oceanparcels.org/en/latest/examples/tutorial_kernelloop.html#Background

    if len(config.argo_deploylocations) > 0:

        # fieldset = create_argo_fieldset(
        #     config, "/home/astuurman/projects/Virtual_ship_classroom/data"
        # )
        fieldset = config.argo_fieldset

        # Define the new Kernel that mimics Argo vertical movement
        def ArgoVerticalMovement(particle, fieldset, time):

            if particle.cycle_phase == 0:
                # Phase 0: Sinking with vertical_speed until depth is driftdepth
                particle_ddepth += (  # noqa See comment above about particle_* variables.
                    fieldset.vertical_speed * particle.dt
                )
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
                particle.cycle_age += (
                    particle.dt
                )  # solve issue of not updating cycle_age during ascent
                if particle.depth + particle_ddepth >= fieldset.mindepth:
                    particle_ddepth = fieldset.mindepth - particle.depth
                    particle.temperature = (
                        math.nan
                    )  # reset temperature to NaN at end of sampling cycle
                    particle.salinity = math.nan  # idem
                    particle.cycle_phase = 4
                else:
                    particle.temperature = fieldset.T[
                        time, particle.depth, particle.lat, particle.lon
                    ]
                    particle.salinity = fieldset.S[
                        time, particle.depth, particle.lat, particle.lon
                    ]

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
        argoset = ParticleSet(
            fieldset=fieldset,
            pclass=ArgoParticle,
            lon=lon,
            lat=lat,
            depth=np.repeat(fieldset.mindepth, len(time)),
            time=time,
        )
        argo_output_file = argoset.ParticleFile(
            name=os.path.join("results", "Argos.zarr"),
            outputdt=timedelta(minutes=5),
            chunks=(1, 500),
        )
        fieldset_endtime = fieldset.time_origin.fulltime(fieldset.U.grid.time_full[-1])
        argo_endtime = np.array(
            (
                datetime.datetime.strptime(
                    config.requested_ship_time["start"], "%Y-%m-%dT%H:%M:%S"
                )
                + timedelta(weeks=6)
            ),
            dtype="datetime64[ms]",
        )

        argoset.execute(
            [
                ArgoVerticalMovement,
                AdvectionRK4,
                KeepAtSurface,
                CheckError,
            ],  # list of kernels to be executed
            endtime=min(fieldset_endtime, argo_endtime),
            dt=timedelta(minutes=5),
            output_file=argo_output_file,
        )


def create_argo_fieldset(config, data_dir: str):
    """
    Create a fieldset from netcdf files for argo floats, return fieldset with negative depth values.

    :param config: The cruise configuration.
    :returns: The fieldset.
    """
    filenames = {
        "U": os.path.join(data_dir, "argodata_UV.nc"),
        "V": os.path.join(data_dir, "argodata_UV.nc"),
        "S": os.path.join(data_dir, "argodata_S.nc"),
        "T": os.path.join(data_dir, "argodata_T.nc"),
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
        filenames, variables, dimensions, allow_time_extrapolation=False
    )
    fieldset.T.interp_method = "linear_invdist_land_tracer"
    for g in fieldset.gridset.grids:
        if max(g.depth) > 0:
            g.depth = -g.depth  # make depth negative
    fieldset.mindepth = -fieldset.U.depth[0]  # uppermost layer in the hydrodynamic data
    fieldset.add_constant("driftdepth", config.argo_characteristics["driftdepth"])
    fieldset.add_constant("maxdepth", config.argo_characteristics["maxdepth"])
    fieldset.add_constant(
        "vertical_speed", config.argo_characteristics["vertical_speed"]
    )
    fieldset.add_constant("cycle_days", config.argo_characteristics["cycle_days"])
    fieldset.add_constant("drift_days", config.argo_characteristics["drift_days"])
    return fieldset
