"""Drifter instrument."""

from dataclasses import dataclass
from datetime import timedelta

import numpy as np
from parcels import AdvectionRK4, FieldSet, JITParticle, ParticleSet, Variable

from .location import Location


@dataclass
class Drifter:
    """Configuration for a single Drifter."""

    location: Location
    deployment_time: float
    min_depth: float


class _DrifterParticle(JITParticle):
    temperature = Variable(
        "temperature",
        initial=np.nan,
    )


def _sample_temperature(particle, fieldset, time):
    particle.temperature = fieldset.T[time, particle.depth, particle.lat, particle.lon]


def _check_error(particle, fieldset, time):
    if particle.state >= 50:  # This captures all Errors
        particle.delete()


def simulate_drifters(
    drifters: list[Drifter],
    fieldset: FieldSet,
    out_file_name: str,
    outputdt: timedelta,
) -> None:
    """
    Use parcels to simulate a set of drifters in a fieldset.

    :param drifters: A list of drifters to simulate.
    :param fieldset: The fieldset to simulate the drifters in.
    :param out_file_name: The file to write the results to.
    :param outputdt: Interval which dictates the update frequency of file output during simulation
    """
    lon = [drifter.location.lon for drifter in drifters]
    lat = [drifter.location.lat for drifter in drifters]
    time = [drifter.deployment_time for drifter in drifters]

    # define the parcels simulation
    drifter_particleset = ParticleSet(
        fieldset=fieldset,
        pclass=_DrifterParticle,
        lon=lon,
        lat=lat,
        depth=[drifter.min_depth for drifter in drifters],
        time=time,
    )

    # define output file for the simulation
    out_file = drifter_particleset.ParticleFile(
        name=out_file_name,
        outputdt=timedelta(minutes=5),
        chunks=(1, 500),
    )

    # get time when the fieldset ends
    fieldset_endtime = fieldset.time_origin.fulltime(fieldset.U.grid.time_full[-1])

    # execute simulation
    drifter_particleset.execute(
        [AdvectionRK4, _sample_temperature, _check_error],
        endtime=fieldset_endtime,
        dt=outputdt,
        output_file=out_file,
    )
