"""ADCP instrument."""

from dataclasses import dataclass

import numpy as np
from parcels import FieldSet, JITParticle, ParticleSet, Variable

from .location import Location


@dataclass
class SamplePoint:
    location: Location
    time: float


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
    out_file_name: str,
    max_depth: float,
    min_depth: float,
    bin_size: float,
    sample_points: list[SamplePoint],
) -> None:
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
    out_file = particleset.ParticleFile(
        name=out_file_name,
    )

    for point in sample_points:
        particleset.lon_nextloop[:] = point.location.lon
        particleset.lat_nextloop[:] = point.location.lat
        particleset.time_nextloop[:] = point.time

        particleset.execute([_sample_velocity], dt=1, runtime=1, verbose_progress=False)
        out_file.write(particleset, time=particleset[0].time)
