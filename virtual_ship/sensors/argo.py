from .location import Location
from dataclasses import dataclass
from parcels import (
    ParticleSet,
    JITParticle,
    Variable,
    FieldSet,
    AdvectionRK4,
    StatusCode,
)
import math
import numpy as np
from datetime import timedelta


@dataclass
class Argo:
    location: Location
    deployment_time: float


class _ArgoParticle(JITParticle):
    cycle_phase = Variable("cycle_phase", dtype=np.int32, initial=0.0)
    cycle_age = Variable("cycle_age", dtype=np.float32, initial=0.0)
    drift_age = Variable("drift_age", dtype=np.float32, initial=0.0)
    salinity = Variable("salinity", initial=np.nan)
    temperature = Variable("temperature", initial=np.nan)


def _argo_vertical_movement(particle, fieldset, time):

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
        if particle.depth + particle_ddepth >= fieldset.min_depth:
            particle_ddepth = fieldset.min_depth - particle.depth
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


def _keep_at_surface(particle, fieldset, time):
    # Prevent error when float reaches surface
    if particle.state == StatusCode.ErrorThroughSurface:
        particle.depth = fieldset.min_depth
        particle.state = StatusCode.Success


def _check_error(particle, fieldset, time):
    if particle.state >= 50:  # This captures all Errors
        particle.delete()


def simulate_argos(
    argos: list[Argo],
    environment: FieldSet,
    out_file_name: str,
    max_depth: float,
    drift_depth: float,
    verticle_speed: float,
    cycle_days: float,
    drift_days: float,
) -> None:
    """
    Use parcels to simulate a set of argos in a fieldset.

    :param argos: The argos to simulate.
    :param environment: The environment to simulate the argos in.
    :param out_file_name: The file to write the results to.
    :param max_depth: TODO
    :param drift_depth: TODO
    :param verticle_speed: TODO
    :param cycle_days: TODO
    :param drift_days: TODO
    """

    lon = [argo.location.lon for argo in argos]
    lat = [argo.location.lat for argo in argos]
    time = [argo.deployment_time for argo in argos]

    min_depth = -environment.U.depth[0]

    # define the parcels simulation
    argoset = ParticleSet(
        fieldset=environment,
        pclass=_ArgoParticle,
        lon=lon,
        lat=lat,
        depth=np.repeat(min_depth, len(argos)),
        time=time,
    )

    # define output file for the simulation
    out_file = argoset.ParticleFile(
        name=out_file_name,
        outputdt=timedelta(minutes=5),
        chunks=(1, 500),
    )

    # get time when the fieldset ends
    fieldset_endtime = environment.time_origin.fulltime(
        environment.U.grid.time_full[-1]
    )

    # set constants on environment fieldset required by kernels.
    # sadly we must change the fieldset parameter to pass this information
    environment.add_constant("min_depth", min_depth)
    environment.add_constant("maxdepth", max_depth)
    environment.add_constant("driftdepth", drift_depth)
    environment.add_constant("vertical_speed", verticle_speed)
    environment.add_constant("cycle_days", cycle_days)
    environment.add_constant("drift_days", drift_days)

    # execute simulation
    argoset.execute(
        [
            _argo_vertical_movement,
            AdvectionRK4,
            _keep_at_surface,
            _check_error,
        ],
        endtime=fieldset_endtime,
        dt=timedelta(minutes=5),
        output_file=out_file,
    )
