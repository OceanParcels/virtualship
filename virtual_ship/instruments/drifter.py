"""Argo float instrument."""

import math
from dataclasses import dataclass
from datetime import timedelta

import numpy as np
from parcels import (
    AdvectionRK4,
    FieldSet,
    JITParticle,
    ParticleSet,
    StatusCode,
    Variable,
)

from .location import Location


@dataclass
class Drifter:
    """Configuration for a single Argo float."""

    location: Location
    deployment_time: float


class _ArgoParticle(JITParticle):
    temperature = Variable(
        "temperature",
        initial=np.nan,
    )


def simulate_drifters(
    drifters: list[Drifter],
    fieldset: FieldSet,
    out_file_name: str,
    outputdt: timedelta,
) -> None:
    """
    Use parcels to simulate a set of Argo floats in a fieldset.

    :param argo_floats: A list of Argo floats to simulate.
    :param fieldset: The fieldset to simulate the Argo floats in.
    :param out_file_name: The file to write the results to.
    :param outputdt: Interval which dictates the update frequency of file output during simulation
    """
    lon = [argo.location.lon for argo in argo_floats]
    lat = [argo.location.lat for argo in argo_floats]
    time = [argo.deployment_time for argo in argo_floats]

    # define the parcels simulation
    argo_float_fieldset = ParticleSet(
        fieldset=fieldset,
        pclass=_ArgoParticle,
        lon=lon,
        lat=lat,
        depth=[argo.min_depth for argo in argo_floats],
        time=time,
        min_depth=[argo.min_depth for argo in argo_floats],
        max_depth=[argo.max_depth for argo in argo_floats],
        drift_depth=[argo.drift_depth for argo in argo_floats],
        vertical_speed=[argo.vertical_speed for argo in argo_floats],
        cycle_days=[argo.cycle_days for argo in argo_floats],
        drift_days=[argo.drift_days for argo in argo_floats],
    )

    # define output file for the simulation
    out_file = argo_float_fieldset.ParticleFile(
        name=out_file_name,
        outputdt=timedelta(minutes=5),
        chunks=(1, 500),
    )

    # get time when the fieldset ends
    fieldset_endtime = fieldset.time_origin.fulltime(fieldset.U.grid.time_full[-1])

    # execute simulation
    drifter_fieldset.execute(
        [AdvectionRK4, _sample_temperature, _check_error],
        endtime=fieldset_endtime,
        dt=outputdt,
        output_file=out_file,
    )
