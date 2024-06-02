"""CTD instrument."""

from dataclasses import dataclass
from datetime import timedelta

import numpy as np
from parcels import FieldSet, JITParticle, ParticleSet, Variable

from .location import Location


@dataclass
class CTDInstrument:
    """Configuration for a single CTD instrument."""

    location: Location
    deployment_time: float
    min_depth: float
    max_depth: float


_CTDParticle = JITParticle.add_variables(
    [
        Variable("salinity", initial=np.nan),
        Variable("temperature", initial=np.nan),
        Variable("raising", dtype=np.int32, initial=0.0),
        Variable("max_depth", dtype=np.float32),
    ]
)


def _sample_temperature(particle, fieldset, time):
    particle.temperature = fieldset.T[time, particle.depth, particle.lat, particle.lon]


def _sample_salinity(particle, fieldset, time):
    particle.salinity = fieldset.S[time, particle.depth, particle.lat, particle.lon]


def _ctd_cast(particle, fieldset, time):
    # Lowering and raising CTD
    # TODO question: if is executed every time... move outside function? Not if "drifting" now possible
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
    ctd_instruments: list[CTDInstrument],
    fieldset: FieldSet,
    out_file_name: str,
    outputdt: timedelta,
) -> None:
    """
    Use parcels to simulate a set of CTD instruments in a fieldset.

    :param ctd_instruments: A list of CTD instruments to simulate.
    :param fieldset: The fieldset to simulate the CTD instruments in.
    :param out_file_name: The file to write the results to.
    :param outputdt: Interval which dictates the update frequency of file output during simulation
    """
    lon = [ctd.location.lon for ctd in ctd_instruments]
    lat = [ctd.location.lat for ctd in ctd_instruments]
    time = [ctd.deployment_time for ctd in ctd_instruments]

    # define parcel particles
    ctd_particleset = ParticleSet(
        fieldset=fieldset,
        pclass=_CTDParticle,
        lon=lon,
        lat=lat,
        depth=[ctd.min_depth for ctd in ctd_instruments],
        time=time,
        max_depth=[ctd.max_depth for ctd in ctd_instruments],
    )

    # define output file for the simulation
    out_file = ctd_particleset.ParticleFile(
        name=out_file_name,
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
