"""Ship salinity and temperature."""

import logging
from pathlib import Path

import numpy as np
from parcels import FieldSet, ParticleSet, ScipyParticle, Variable

from ..log_filter import DuplicateFilter
from ..spacetime import Spacetime

# we specifically use ScipyParticle because we have many small calls to execute
# there is some overhead with JITParticle and this ends up being significantly faster
_ShipSTParticle = ScipyParticle.add_variables(
    [
        Variable("S", dtype=np.float32, initial=np.nan),
        Variable("T", dtype=np.float32, initial=np.nan),
    ]
)


# define function sampling Salinity
def _sample_salinity(particle, fieldset, time):
    particle.S = fieldset.S[time, particle.depth, particle.lat, particle.lon]


# define function sampling Temperature
def _sample_temperature(particle, fieldset, time):
    particle.T = fieldset.T[time, particle.depth, particle.lat, particle.lon]


def simulate_ship_underwater_st(
    fieldset: FieldSet,
    out_path: str | Path,
    depth: float,
    sample_points: list[Spacetime],
    log_filter: bool = True,
) -> None:
    """
    Use Parcels to simulate underway data, measuring salinity and temperature at the given depth along the ship track in a fieldset.

    :param fieldset: The fieldset to simulate the sampling in.
    :param out_path: The path to write the results to.
    :param depth: The depth at which to measure. 0 is water surface, negative is into the water.
    :param sample_points: The places and times to sample at.
    :param log_filter: Whether to filter duplicate log messages (defaults to True). This is a bit of a hack, but it works and could be removed if changed in Parcels.
    """
    sample_points.sort(key=lambda p: p.time)

    particleset = ParticleSet.from_list(
        fieldset=fieldset,
        pclass=_ShipSTParticle,
        lon=0.0,  # initial lat/lon are irrelevant and will be overruled later
        lat=0.0,
        depth=depth,
        time=0,  # same for time
    )

    # define output file for the simulation
    # outputdt set to infinie as we want to just want to write at the end of every call to 'execute'
    out_file = particleset.ParticleFile(name=out_path, outputdt=np.inf)

    #  whether to filter parcels duplicate log messages
    if log_filter:
        external_logger = logging.getLogger("parcels.tools.loggers")
        for handler in external_logger.handlers:
            handler.addFilter(DuplicateFilter())

    # iterate over each point, manually set lat lon time, then
    # execute the particle set for one step, performing one set of measurement
    for point in sample_points:
        particleset.lon_nextloop[:] = point.location.lon
        particleset.lat_nextloop[:] = point.location.lat
        particleset.time_nextloop[:] = fieldset.time_origin.reltime(
            np.datetime64(point.time)
        )

        # perform one step using the particleset
        # dt and runtime are set so exactly one step is made.
        particleset.execute(
            [_sample_salinity, _sample_temperature],
            dt=1,
            runtime=1,
            verbose_progress=False,
            output_file=out_file,
        )

    # turn off log filter after .execute(), to prevent being applied universally to all loggers
    # separate if statement from above to prevent error if log_filter is False
    if log_filter:
        for handler in external_logger.handlers:
            handler.removeFilter(handler.filters[0])
