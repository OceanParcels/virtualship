"""Ship salinity and temperature."""

from dataclasses import dataclass

import numpy as np
from parcels import FieldSet, JITParticle, ParticleSet, Variable

from .location import Location


@dataclass
class SamplePoint:
    location: Location
    time: float


_ShipSTParticle = JITParticle.add_variables(
    [
        Variable("salinity", dtype=np.float32, initial=np.nan),
        Variable("temperature", dtype=np.float32, initial=np.nan),
    ]
)


# define function sampling Salinity
def _sample_salinity(particle, fieldset, time):
    particle.salinity = fieldset.S[time, particle.depth, particle.lat, particle.lon]


# define function sampling Temperature
def _sample_temperature(particle, fieldset, time):
    particle.temperature = fieldset.T[time, particle.depth, particle.lat, particle.lon]


def simulate_ship_st(
    fieldset: FieldSet,
    out_file_name: str,
    depth: float,
    sample_points: list[SamplePoint],
) -> None:
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
        particleset.time_nextloop[:] = point.time

        particleset.execute(
            [_sample_salinity, _sample_temperature],
            dt=1,
            runtime=1,
            verbose_progress=False,
        )
        out_file.write(particleset, time=particleset[0].time)
