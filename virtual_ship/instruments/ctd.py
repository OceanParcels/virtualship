"""CTD instrument."""

from dataclasses import dataclass
from datetime import timedelta

import numpy as np
import py
from parcels import (
    FieldSet,
    ScipyParticle,
    JITParticle,
    ParticleSet,
    Variable,
    StatusCode,
)

from ..spacetime import Spacetime


@dataclass
class CTD:
    """Configuration for a single CTD."""

    spacetime: Spacetime
    min_depth: float
    max_depth: float


_CTDParticle = ScipyParticle.add_variables(
    [
        Variable("salinity", dtype=np.float32, initial=np.nan),
        Variable("temperature", dtype=np.float32, initial=np.nan),
        Variable("raising", dtype=np.bool_, initial=False),
        Variable("max_depth", dtype=np.float32),
        Variable("min_depth", dtype=np.float32),
        Variable("winch_speed", dtype=np.float32),
    ]
)


def _sample_temperature(particle, fieldset, time):
    particle.temperature = fieldset.T[time, particle.depth, particle.lat, particle.lon]


def _sample_salinity(particle, fieldset, time):
    particle.salinity = fieldset.S[time, particle.depth, particle.lat, particle.lon]


def _ctd_cast(particle, fieldset, time):
    if not particle.raising:
        particle_ddepth = -particle.winch_speed * particle.dt
        if particle.depth + particle_ddepth < particle.max_depth:
            particle.raising = True
            particle_ddepth = -particle_ddepth
    else:
        particle_ddepth = particle.winch_speed * particle.dt
        if particle.depth + particle_ddepth > -particle.min_depth:
            particle.delete()


def simulate_ctd(
    fieldset: FieldSet,
    out_path: str | py.path.LocalPath,
    ctds: list[CTD],
    outputdt: timedelta,
) -> None:
    """
    Use parcels to simulate a set of CTDs in a fieldset.

    :param fieldset: The fieldset to simulate the CTDs in.
    :param out_path: The path to write the results to.
    :param ctds: A list of CTDs to simulate.
    :param outputdt: Interval which dictates the update frequency of file output during simulation
    """
    WINCH_SPEED = 1.0  # sink and rise speed in m/s

    fieldset_starttime = fieldset.time_origin.fulltime(fieldset.U.grid.time_full[0])
    fieldset_endtime = fieldset.time_origin.fulltime(fieldset.U.grid.time_full[-1])

    # deploy time for all ctds should be later than fieldset start time
    if not all([ctd.spacetime.time <= fieldset_starttime for ctd in ctds]):
        raise RuntimeError("CTD deployed before fieldset starts.")

    # depth the ctd will go to. deepest between ctd max depth and bathymetry.
    max_depths = [
        min(
            ctd.max_depth,
            fieldset.bathymetry.eval(
                z=0, y=ctd.spacetime.location.lat, x=ctd.spacetime.location.lon, time=0
            ),
        )
        for ctd in ctds
    ]

    # define parcel particles
    ctd_particleset = ParticleSet(
        fieldset=fieldset,
        pclass=_CTDParticle,
        lon=[ctd.spacetime.location.lon for ctd in ctds],
        lat=[ctd.spacetime.location.lat for ctd in ctds],
        depth=[ctd.min_depth for ctd in ctds],
        time=[ctd.spacetime.time for ctd in ctds],
        max_depth=max_depths,
        min_depth=[ctd.min_depth for ctd in ctds],
        winch_speed=[WINCH_SPEED],
    )

    # define output file for the simulation
    out_file = ctd_particleset.ParticleFile(name=out_path, outputdt=outputdt)

    # execute simulation
    ctd_particleset.execute(
        [_sample_salinity, _sample_temperature, _ctd_cast],
        endtime=fieldset_endtime,
        dt=outputdt,
        verbose_progress=False,
        output_file=out_file,
    )

    # there should be no particles left, as they delete themselves when they resurface
    if len(ctd_particleset.particledata) != 0:
        raise RuntimeError(
            "Simulation ended before CTD resurfaced. This most likely means the field time dimension did not match the simulation time span."
        )
