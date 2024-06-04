"""Ship salinity and temperature."""

import numpy as np
from parcels import FieldSet, JITParticle, ParticleSet, Variable

from ..spacetime import Spacetime

_ShipSTParticle = JITParticle.add_variables(
    [
        Variable("salinity", dtype=np.float32, initial=np.nan),
        Variable("temperature", dtype=np.float32, initial=np.nan),
    ]
)


# define function sampling Salinity
def _sample_salinity(particle, fieldset, time):
    particle.salinity = fieldset.salinity[
        time, particle.depth, particle.lat, particle.lon
    ]


# define function sampling Temperature
def _sample_temperature(particle, fieldset, time):
    particle.temperature = fieldset.temperature[
        time, particle.depth, particle.lat, particle.lon
    ]


def simulate_ship_underwater_st(
    fieldset: FieldSet,
    out_file_name: str,
    depth: float,
    sample_points: list[Spacetime],
) -> None:
    """
    Use parcels to simulate underway data, measuring salinity and temperature at the given depth along the ship track in a fieldset.

    :param fieldset: The fieldset to simulate the sampling in.
    :param out_file_name: The file to write the results to.
    :param depth: The depth at which to measure. 0 is water surface, negative is into the water.
    :param sample_points: The places and times to sample at.
    """
    sample_points.sort(key=lambda p: p.time)

    particleset = ParticleSet.from_list(
        fieldset=fieldset,
        pclass=_ShipSTParticle,
        lon=0.0,  # initial lat/lon are irrelevant and will be overruled later.
        lat=0.0,
        depth=depth,
        time=0,  # same for time
    )

    # define output file for the simulation
    out_file = particleset.ParticleFile(
        name=out_file_name,
    )

    for point in sample_points:
        particleset.lon_nextloop[:] = point.location.lon
        particleset.lat_nextloop[:] = point.location.lat
        particleset.time_nextloop[:] = fieldset.time_origin.reltime(point.time)

        particleset.execute(
            [_sample_salinity, _sample_temperature],
            dt=1,
            runtime=1,
            verbose_progress=False,
        )
        out_file.write(particleset, time=particleset[0].time)
