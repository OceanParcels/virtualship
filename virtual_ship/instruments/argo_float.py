"""Argo float instrument."""

import math
from dataclasses import dataclass
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

from .location import Location


@dataclass
class ArgoFloat:
    """Configuration for a single Argo float."""

    location: Location
    deployment_time: float
    min_depth: float
    max_depth: float
    drift_depth: float
    vertical_speed: float
    cycle_days: float
    drift_days: float


_ArgoParticle = JITParticle.add_variables(
    [
        Variable("cycle_phase", dtype=np.int32, initial=0.0),
        Variable("cycle_age", dtype=np.float32, initial=0.0),
        Variable("drift_age", dtype=np.float32, initial=0.0),
        Variable("salinity", initial=np.nan),
        Variable("temperature", initial=np.nan),
        Variable("min_depth", dtype=np.float32),
        Variable("max_depth", dtype=np.float32),
        Variable("drift_depth", dtype=np.float32),
        Variable("vertical_speed", dtype=np.float32),
        Variable("cycle_days", dtype=np.int32),
        Variable("drift_days", dtype=np.int32),
    ]
)


def _argo_float_vertical_movement(particle, fieldset, time):
    if particle.cycle_phase == 0:
        # Phase 0: Sinking with vertical_speed until depth is drift_depth
        particle_ddepth += (  # noqa See comment above about particle_* variables.
            particle.vertical_speed * particle.dt
        )
        if particle.depth + particle_ddepth <= particle.drift_depth:
            particle_ddepth = particle.drift_depth - particle.depth
            particle.cycle_phase = 1

    elif particle.cycle_phase == 1:
        # Phase 1: Drifting at depth for drifttime seconds
        particle.drift_age += particle.dt
        if particle.drift_age >= particle.drift_days * 86400:
            particle.drift_age = 0  # reset drift_age for next cycle
            particle.cycle_phase = 2

    elif particle.cycle_phase == 2:
        # Phase 2: Sinking further to max_depth
        particle_ddepth += particle.vertical_speed * particle.dt
        if particle.depth + particle_ddepth <= particle.max_depth:
            particle_ddepth = particle.max_depth - particle.depth
            particle.cycle_phase = 3

    elif particle.cycle_phase == 3:
        # Phase 3: Rising with vertical_speed until at surface
        particle_ddepth -= particle.vertical_speed * particle.dt
        particle.cycle_age += (
            particle.dt
        )  # solve issue of not updating cycle_age during ascent
        if particle.depth + particle_ddepth >= particle.min_depth:
            particle_ddepth = particle.min_depth - particle.depth
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
        if particle.cycle_age > particle.cycle_days * 86400:
            particle.cycle_phase = 0
            particle.cycle_age = 0

    if particle.state == StatusCode.Evaluate:
        particle.cycle_age += particle.dt  # update cycle_age


def _keep_at_surface(particle, fieldset, time):
    # Prevent error when float reaches surface
    if particle.state == StatusCode.ErrorThroughSurface:
        particle.depth = particle.min_depth
        particle.state = StatusCode.Success


def _check_error(particle, fieldset, time):
    if particle.state >= 50:  # This captures all Errors
        particle.delete()


def simulate_argo_floats(
    argo_floats: list[ArgoFloat],
    fieldset: FieldSet,
    out_file_name: str,
    outputdt: timedelta,
) -> None:
    """
    Use parcels to simulate a set of Argo floats in a fieldset.

    :param argo_floats: A list of Argo floats to simulate.
    :param fieldset: The fieldset to simulate the Argo floats in.
    :param out_file_name: The file to write the results to.
    :param outputdt: Interval which dictates the update frequency of file output during simulation
    """
    lon = [argo.location.lon for argo in argo_floats]
    lat = [argo.location.lat for argo in argo_floats]
    time = [argo.deployment_time for argo in argo_floats]

    # define parcel particles
    argo_float_particleset = ParticleSet(
        fieldset=fieldset,
        pclass=_ArgoParticle,
        lon=lon,
        lat=lat,
        depth=[argo.min_depth for argo in argo_floats],
        time=time,
        min_depth=[argo.min_depth for argo in argo_floats],
        max_depth=[argo.max_depth for argo in argo_floats],
        drift_depth=[argo.drift_depth for argo in argo_floats],
        vertical_speed=[argo.vertical_speed for argo in argo_floats],
        cycle_days=[argo.cycle_days for argo in argo_floats],
        drift_days=[argo.drift_days for argo in argo_floats],
    )

    # define output file for the simulation
    out_file = argo_float_particleset.ParticleFile(
        name=out_file_name,
        outputdt=outputdt,
        chunks=(1, 500),
    )

    # get time when the fieldset ends
    fieldset_endtime = fieldset.time_origin.fulltime(fieldset.U.grid.time_full[-1])

    # execute simulation
    argo_float_particleset.execute(
        [
            _argo_float_vertical_movement,
            AdvectionRK4,
            _keep_at_surface,
            _check_error,
        ],
        endtime=fieldset_endtime,
        dt=outputdt,
        output_file=out_file,
    )
