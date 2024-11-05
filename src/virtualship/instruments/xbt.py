"""XBT instrument."""

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import numpy as np
from parcels import FieldSet, JITParticle, ParticleSet, Variable

from ..spacetime import Spacetime


@dataclass
class XBT:
    """Configuration for a single XBT."""

    spacetime: Spacetime
    min_depth: float
    max_depth: float


_XBTParticle = JITParticle.add_variables(
    [
        Variable("temperature", dtype=np.float32, initial=np.nan),
        Variable("max_depth", dtype=np.float32),
        Variable("min_depth", dtype=np.float32),
        Variable("winch_speed", dtype=np.float32),
    ]
)


def _sample_temperature(particle, fieldset, time):
    particle.temperature = fieldset.T[time, particle.depth, particle.lat, particle.lon]


def _xbt_cast(particle, fieldset, time):
    # lowering
    particle_ddepth = -particle.winch_speed * particle.dt
    if particle.depth + particle_ddepth < particle.max_depth:
        particle.raising = 1
        particle_ddepth = -particle_ddepth


def simulate_xbt(
    fieldset: FieldSet,
    out_path: str | Path,
    xbts: list[XBT],
    outputdt: timedelta,
) -> None:
    """
    Use Parcels to simulate a set of XBTs in a fieldset.

    :param fieldset: The fieldset to simulate the XBTs in.
    :param out_path: The path to write the results to.
    :param xbts: A list of XBTs to simulate.
    :param outputdt: Interval which dictates the update frequency of file output during simulation
    :raises ValueError: Whenever provided XBTs, fieldset, are not compatible with this function.
    """
    WINCH_SPEED = 1.0  # sink and rise speed in m/s
    DT = 10.0  # dt of XBT simulation integrator

    if len(xbts) == 0:
        print(
            "No XBTs provided. Parcels currently crashes when providing an empty particle set, so no XBT simulation will be done and no files will be created."
        )
        # TODO when Parcels supports it this check can be removed.
        return

    fieldset_starttime = fieldset.time_origin.fulltime(fieldset.U.grid.time_full[0])
    fieldset_endtime = fieldset.time_origin.fulltime(fieldset.U.grid.time_full[-1])

    # deploy time for all xbts should be later than fieldset start time
    if not all(
        [np.datetime64(xbt.spacetime.time) >= fieldset_starttime for xbt in xbts]
    ):
        raise ValueError("XBT deployed before fieldset starts.")

    # depth the xbt will go to. shallowest between xbt max depth and bathymetry.
    max_depths = [
        max(
            xbt.max_depth,
            fieldset.bathymetry.eval(
                z=0, y=xbt.spacetime.location.lat, x=xbt.spacetime.location.lon, time=0
            ),
        )
        for xbt in xbts
    ]

    # XBT depth can not be too shallow, because kernel would break.
    # This shallow is not useful anyway, no need to support.
    if not all([max_depth <= -DT * WINCH_SPEED for max_depth in max_depths]):
        raise ValueError(
            f"XBT max_depth or bathymetry shallower than maximum {-DT * WINCH_SPEED}"
        )

    # define parcel particles
    xbt_particleset = ParticleSet(
        fieldset=fieldset,
        pclass=_XBTParticle,
        lon=[xbt.spacetime.location.lon for xbt in xbts],
        lat=[xbt.spacetime.location.lat for xbt in xbts],
        depth=[xbt.min_depth for xbt in xbts],
        time=[xbt.spacetime.time for xbt in xbts],
        max_depth=max_depths,
        min_depth=[xbt.min_depth for xbt in xbts],
        winch_speed=[WINCH_SPEED for _ in xbts],
    )

    # define output file for the simulation
    out_file = xbt_particleset.ParticleFile(name=out_path, outputdt=outputdt)

    # execute simulation
    xbt_particleset.execute(
        [_sample_temperature, _xbt_cast],
        endtime=fieldset_endtime,
        dt=DT,
        verbose_progress=False,
        output_file=out_file,
    )

    # there should be no particles left, as they delete themselves when they finish profiling
    if len(xbt_particleset.particledata) != 0:
        raise ValueError(
            "Simulation ended before XBT finished profiling. This most likely means the field time dimension did not match the simulation time span."
        )
