"""Drifter instrument."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from parcels import AdvectionRK4, FieldSet, JITParticle, ParticleSet, Variable

from ..spacetime import Spacetime


@dataclass
class Drifter:
    """Configuration for a single Drifter."""

    spacetime: Spacetime
    depth: float  # depth at which it floats and samples
    lifetime: timedelta | None  # if none, lifetime is infinite


_DrifterParticle = JITParticle.add_variables(
    [
        Variable("temperature", dtype=np.float32, initial=np.nan),
        Variable("has_lifetime", dtype=np.int8),  # bool
        Variable("age", dtype=np.float32, initial=0.0),
        Variable("lifetime", dtype=np.float32),
    ]
)


def _sample_temperature(particle, fieldset, time):
    particle.temperature = fieldset.T[time, particle.depth, particle.lat, particle.lon]


def _check_lifetime(particle, fieldset, time):
    if particle.has_lifetime == 1:
        particle.age += particle.dt
        if particle.age >= particle.lifetime:
            particle.delete()


def simulate_drifters(
    fieldset: FieldSet,
    out_path: str | Path,
    drifters: list[Drifter],
    outputdt: timedelta,
    dt: timedelta,
    endtime: datetime | None = None,
) -> None:
    """
    Use Parcels to simulate a set of drifters in a fieldset.

    :param fieldset: The fieldset to simulate the Drifters in.
    :param out_path: The path to write the results to.
    :param drifters: A list of drifters to simulate.
    :param outputdt: Interval which dictates the update frequency of file output during simulation.
    :param dt: Dt for integration.
    :param endtime: Stop at this time, or if None, continue until the end of the fieldset or until all drifters ended. If this is earlier than the last drifter ended or later than the end of the fieldset, a warning will be printed.
    """
    if len(drifters) == 0:
        print(
            "No drifters provided. Parcels currently crashes when providing an empty particle set, so no drifter simulation will be done and no files will be created."
        )
        # TODO when Parcels supports it this check can be removed.
        return

    # define parcel particles
    drifter_particleset = ParticleSet(
        fieldset=fieldset,
        pclass=_DrifterParticle,
        lat=[drifter.spacetime.location.lat for drifter in drifters],
        lon=[drifter.spacetime.location.lon for drifter in drifters],
        depth=[drifter.depth for drifter in drifters],
        time=[drifter.spacetime.time for drifter in drifters],
        has_lifetime=[1 if drifter.lifetime is not None else 0 for drifter in drifters],
        lifetime=[
            0 if drifter.lifetime is None else drifter.lifetime.total_seconds()
            for drifter in drifters
        ],
    )

    # define output file for the simulation
    out_file = drifter_particleset.ParticleFile(
        name=out_path, outputdt=outputdt, chunks=[len(drifter_particleset), 100]
    )

    # get earliest between fieldset end time and provide end time
    fieldset_endtime = fieldset.time_origin.fulltime(fieldset.U.grid.time_full[-1])
    if endtime is None:
        actual_endtime = fieldset_endtime
    elif endtime > fieldset_endtime:
        print("WARN: Requested end time later than fieldset end time.")
        actual_endtime = fieldset_endtime
    else:
        actual_endtime = np.timedelta64(endtime)

    # execute simulation
    drifter_particleset.execute(
        [AdvectionRK4, _sample_temperature, _check_lifetime],
        endtime=actual_endtime,
        dt=dt,
        output_file=out_file,
        verbose_progress=True,
    )

    # if there are more particles left than the number of drifters with an indefinite endtime, warn the user
    if len(drifter_particleset.particledata) > len(
        [d for d in drifters if d.lifetime is None]
    ):
        print(
            "WARN: Some drifters had a life time beyond the end time of the fieldset or the requested end time."
        )
