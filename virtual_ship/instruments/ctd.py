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
        Variable("raising", dtype=np.int32, initial=0),
        Variable("max_depth", dtype=np.float32),
        Variable("winch_speed", dtype=np.float32),
    ]
)


def _sample_temperature(particle, fieldset, time):
    particle.temperature = fieldset.T[time, particle.depth, particle.lat, particle.lon]


def _sample_salinity(particle, fieldset, time):
    particle.salinity = fieldset.S[time, particle.depth, particle.lat, particle.lon]


def _ctd_cast(particle, fieldset, time):
    if particle.raising == 0:
        # Sinking with winch_speed until near seafloor
        particle_ddepth = -particle.winch_speed * particle.dt
        if particle.depth <= particle.max_depth:
            particle.raising = 1

    if particle.raising == 1:
        # Rising with winch_speed until depth is -2 m
        if particle.depth < -2:
            particle_ddepth = particle.winch_speed * particle.dt
            if particle.depth + particle_ddepth >= -2:
                # to break the loop ...
                particle.state = StatusCode.StopAllExecution


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

    for ctd in ctds:
        if ctd.spacetime.time < fieldset_starttime:
            raise RuntimeError("CTD deployed before fieldset starts.")

        # depth the ctd will go to. deepest between ctd max depth and bathymetry.
        max_depth = min(
            ctd.max_depth,
            fieldset.bathymetry.eval(
                z=0, y=ctd.spacetime.location.lat, x=ctd.spacetime.location.lon, time=0
            ),
        )

        # define parcel particles
        ctd_particleset = ParticleSet(
            fieldset=fieldset,
            pclass=_CTDParticle,
            lon=[ctd.spacetime.location.lon],
            lat=[ctd.spacetime.location.lat],
            depth=[ctd.min_depth],
            time=[ctd.spacetime.time],
            max_depth=[max_depth],
            winch_speed=[WINCH_SPEED],
        )

        # define output file for the simulation
        out_file = ctd_particleset.ParticleFile(name=out_path, outputdt=outputdt)

        # execute simulation
        ctd_particleset.execute(
            [_sample_salinity],  # , _sample_temperature, _ctd_cast],
            endtime=fieldset_endtime,
            dt=outputdt,
            verbose_progress=False,
            output_file=out_file,
        )

        if ctd_particleset.raising[0] == 0 or not np.isclose(
            ctd_particleset.particledata.depth[0], ctd.min_depth
        ):
            raise RuntimeError(
                "Simulation ended before CTD resurfaced. This most likely means the field time dimension did not match the simulation time span."
            )
