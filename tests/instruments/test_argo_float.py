"""Test the simulation of Argo floats."""

from datetime import datetime, timedelta

import numpy as np
import xarray as xr
from parcels import FieldSet

from virtualship.instruments.argo_float import ArgoFloat, simulate_argo_floats
from virtualship.models import Location, Spacetime


def test_simulate_argo_floats(tmpdir) -> None:
    # arbitrary time offset for the dummy fieldset
    base_time = datetime.strptime("1950-01-01", "%Y-%m-%d")

    DRIFT_DEPTH = -1000
    MAX_DEPTH = -2000
    VERTICAL_SPEED = -0.10
    CYCLE_DAYS = 10
    DRIFT_DAYS = 9

    CONST_TEMPERATURE = 1.0  # constant temperature in fieldset
    CONST_SALINITY = 1.0  # constant salinity in fieldset

    v = np.full((2, 2, 2), 1.0)
    u = np.full((2, 2, 2), 1.0)
    t = np.full((2, 2, 2), CONST_TEMPERATURE)
    s = np.full((2, 2, 2), CONST_SALINITY)

    fieldset = FieldSet.from_data(
        {"V": v, "U": u, "T": t, "S": s},
        {
            "lon": np.array([0.0, 10.0]),
            "lat": np.array([0.0, 10.0]),
            "time": [
                np.datetime64(base_time + timedelta(seconds=0)),
                np.datetime64(base_time + timedelta(hours=4)),
            ],
        },
    )

    # argo floats to deploy
    argo_floats = [
        ArgoFloat(
            spacetime=Spacetime(location=Location(latitude=0, longitude=0), time=0),
            min_depth=0.0,
            max_depth=MAX_DEPTH,
            drift_depth=DRIFT_DEPTH,
            vertical_speed=VERTICAL_SPEED,
            cycle_days=CYCLE_DAYS,
            drift_days=DRIFT_DAYS,
        )
    ]

    # perform simulation
    out_path = tmpdir.join("out.zarr")

    simulate_argo_floats(
        fieldset=fieldset,
        out_path=out_path,
        argo_floats=argo_floats,
        outputdt=timedelta(minutes=5),
        endtime=None,
    )

    # test if output is as expected
    results = xr.open_zarr(out_path)

    # check the following variables are in the dataset
    assert len(results.trajectory) == len(argo_floats)
    for var in ["lon", "lat", "z", "temperature", "salinity"]:
        assert var in results, f"Results don't contain {var}"
