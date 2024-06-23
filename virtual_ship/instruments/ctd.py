"""CTD instrument."""

from dataclasses import dataclass
from datetime import timedelta

import numpy as np
import py
from parcels import FieldSet, JITParticle, ParticleSet, Variable

from ..spacetime import Spacetime


@dataclass
class CTD:
    """Configuration for a single CTD."""

    spacetime: Spacetime
    min_depth: float
    max_depth: float


_CTDParticle = JITParticle.add_variables(
    [
        Variable("salinity", dtype=np.float32, initial=np.nan),
        Variable("temperature", dtype=np.float32, initial=np.nan),
        Variable("raising", dtype=np.int32, initial=0),
        Variable("max_depth", dtype=np.float32),
    ]
)


def _sample_temperature(particle, fieldset, time):
    particle.temperature = fieldset.T[time, particle.depth, particle.lat, particle.lon]


def _sample_salinity(particle, fieldset, time):
    particle.salinity = fieldset.S[time, particle.depth, particle.lat, particle.lon]


def _ctd_cast(particle, fieldset, time):
    # Lowering and raising CTD
    if (
        -fieldset.bathymetry[time, particle.depth, particle.lat, particle.lon]
        > particle.max_depth
    ):
        maxdepth = (
            -fieldset.bathymetry[time, particle.depth, particle.lat, particle.lon] + 20
        )
    else:
        maxdepth = particle.max_depth
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
    lon = [ctd.spacetime.location.lon for ctd in ctds]
    lat = [ctd.spacetime.location.lat for ctd in ctds]
    time = [ctd.spacetime.time for ctd in ctds]

    # define parcel particles
    ctd_particleset = ParticleSet(
        fieldset=fieldset,
        pclass=_CTDParticle,
        lon=lon,
        lat=lat,
        depth=[ctd.min_depth for ctd in ctds],
        time=time,
        max_depth=[ctd.max_depth for ctd in ctds],
    )

    # define output file for the simulation
    out_file = ctd_particleset.ParticleFile(
        name=out_path,
        outputdt=outputdt,
        chunks=(1, 500),
    )

    # get time when the fieldset ends
    fieldset_endtime = fieldset.time_origin.fulltime(fieldset.U.grid.time_full[-1])

    # execute simulation
    ctd_particleset.execute(
        [_sample_salinity, _sample_temperature, _ctd_cast],
        endtime=fieldset_endtime,
        dt=outputdt,
        output_file=out_file,
    )
