import numpy as np
from parcels import FieldSet, JITParticle, ParticleSet, Variable

from datetime import datetime


Particle = JITParticle.add_variables(
    [
        Variable("temperature", dtype=np.float32, initial=np.nan),
    ]
)


def sample_temperature(particle, fieldset, time):
    particle.temperature = fieldset.T[time, particle.depth, particle.lat, particle.lon]


def simulate_ctd() -> None:
    base_time = datetime.strptime("1950-01-01", "%Y-%m-%d")

    fieldset = FieldSet.from_data(
        {
            "V": np.zeros((2, 2, 2, 2)),
            "U": np.zeros((2, 2, 2, 2)),
            "T": np.zeros((2, 2, 2, 2)),
        },
        {
            "time": [
                np.datetime64(base_time + datetime.timedelta(hours=0)),
                np.datetime64(base_time + datetime.timedelta(hours=1)),
            ],
            "depth": [-1000, 0],
            "lat": [0, 1],
            "lon": [0, 1],
        },
    )

    fieldset_endtime = fieldset.time_origin.fulltime(fieldset.U.grid.time_full[-1])

    particleset = ParticleSet(
        fieldset=fieldset,
        pclass=Particle,
        lon=[],
        lat=[],
        depth=[],
        time=[],
    )

    # define output file for the simulation
    out_file = particleset.ParticleFile(name="test")

    # execute simulation
    particleset.execute(
        [sample_temperature],
        endtime=fieldset_endtime,
        dt=5,
        verbose_progress=False,
        output_file=out_file,
    )
