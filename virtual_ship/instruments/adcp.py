"""ADCP instrument."""

import numpy as np
import py
from parcels import FieldSet, JITParticle, ParticleSet, Variable

from ..spacetime import Spacetime

_ADCPParticle = JITParticle.add_variables(
    [
        Variable("U", dtype=np.float32, initial=np.nan),
        Variable("V", dtype=np.float32, initial=np.nan),
    ]
)


def _sample_velocity(particle, fieldset, time):
    particle.U, particle.V = fieldset.UV.eval(
        time, particle.depth, particle.lat, particle.lon, applyConversion=False
    )


def simulate_adcp(
    fieldset: FieldSet,
    out_path: str | py.path.LocalPath,
    max_depth: float,
    min_depth: float,
    bin_size: float,
    sample_points: list[Spacetime],
) -> None:
    """
    Use parcels to simulate an ADCP in a fieldset.

    :param fieldset: The fieldset to simulate the ADCP in.
    :param out_path: The path to write the results to.
    :param max_depth: Maximum depth the ADCP can measure.
    :param min_depth: Minimum depth the ADCP can measure.
    :param bin_size: How many samples to take in the complete range between max_depth and min_depth.
    :param sample_points: The places and times to sample at.
    """
    sample_points.sort(key=lambda p: p.time)

    bins = np.arange(max_depth, min_depth, bin_size)
    num_particles = len(bins)
    particleset = ParticleSet.from_list(
        fieldset=fieldset,
        pclass=_ADCPParticle,
        lon=np.full(
            num_particles, 0.0
        ),  # initial lat/lon are irrelevant and will be overruled later.
        lat=np.full(num_particles, 0.0),
        depth=bins,
        time=0,  # same for time
    )

    # define output file for the simulation
    # outputdt set to infinie as we want to just want to write at the end of every call to 'execute'
    out_file = particleset.ParticleFile(name=out_path, outputdt=np.inf)

    for point in sample_points:
        particleset.lon_nextloop[:] = point.location.lon
        particleset.lat_nextloop[:] = point.location.lat
        particleset.time_nextloop[:] = point.time

        particleset.execute([_sample_velocity], dt=1, runtime=1, verbose_progress=False)
        out_file.write(particleset, time=particleset[0].time)
