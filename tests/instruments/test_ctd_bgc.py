"""
Test the simulation of CTD_BGC instruments.

Fields are kept static over time and time component of CTD_BGC measurements is not tested because it's tricky to provide expected measurements.
"""

import datetime
from datetime import timedelta

import numpy as np
import xarray as xr
from parcels import Field, FieldSet

from virtualship.instruments.ctd_bgc import CTD_BGC, simulate_ctd_bgc
from virtualship.models import Location, Spacetime


def test_simulate_ctd_bgcs(tmpdir) -> None:
    # arbitrary time offset for the dummy fieldset
    base_time = datetime.datetime.strptime("1950-01-01", "%Y-%m-%d")

    # where to cast CTD_BGCs
    ctd_bgcs = [
        CTD_BGC(
            spacetime=Spacetime(
                location=Location(latitude=0, longitude=1),
                time=base_time + datetime.timedelta(hours=0),
            ),
            min_depth=0,
            max_depth=float("-inf"),
        ),
        CTD_BGC(
            spacetime=Spacetime(
                location=Location(latitude=1, longitude=0),
                time=base_time,
            ),
            min_depth=0,
            max_depth=float("-inf"),
        ),
    ]

    # expected observations for ctd_bgcs at surface and at maximum depth
    ctd_bgc_exp = [
        {
            "surface": {
                "o2": 9,
                "chl": 10,
                "lat": ctd_bgcs[0].spacetime.location.lat,
                "lon": ctd_bgcs[0].spacetime.location.lon,
            },
            "maxdepth": {
                "o2": 11,
                "chl": 12,
                "lat": ctd_bgcs[0].spacetime.location.lat,
                "lon": ctd_bgcs[0].spacetime.location.lon,
            },
        },
        {
            "surface": {
                "o2": 9,
                "chl": 10,
                "lat": ctd_bgcs[1].spacetime.location.lat,
                "lon": ctd_bgcs[1].spacetime.location.lon,
            },
            "maxdepth": {
                "o2": 11,
                "chl": 12,
                "lat": ctd_bgcs[1].spacetime.location.lat,
                "lon": ctd_bgcs[1].spacetime.location.lon,
            },
        },
    ]

    # create fieldset based on the expected observations
    # indices are time, depth, latitude, longitude
    u = np.zeros((2, 2, 2, 2))
    v = np.zeros((2, 2, 2, 2))
    o2 = np.zeros((2, 2, 2, 2))  # o2 field
    chl = np.zeros((2, 2, 2, 2))  # chl field

    o2[:, 1, 0, 1] = ctd_bgc_exp[0]["surface"]["o2"]
    o2[:, 0, 0, 1] = ctd_bgc_exp[0]["maxdepth"]["o2"]
    o2[:, 1, 1, 0] = ctd_bgc_exp[1]["surface"]["o2"]
    o2[:, 0, 1, 0] = ctd_bgc_exp[1]["maxdepth"]["o2"]

    chl[:, 1, 0, 1] = ctd_bgc_exp[0]["surface"]["chl"]
    chl[:, 0, 0, 1] = ctd_bgc_exp[0]["maxdepth"]["chl"]
    chl[:, 1, 1, 0] = ctd_bgc_exp[1]["surface"]["chl"]
    chl[:, 0, 1, 0] = ctd_bgc_exp[1]["maxdepth"]["chl"]

    fieldset = FieldSet.from_data(
        {"V": v, "U": u, "o2": o2, "chl": chl},
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
    fieldset.add_field(Field("bathymetry", [-1000], lon=0, lat=0))

    # perform simulation
    out_path = tmpdir.join("out.zarr")

    simulate_ctd_bgc(
        ctd_bgcs=ctd_bgcs,
        fieldset=fieldset,
        out_path=out_path,
        outputdt=timedelta(seconds=10),
    )

    # test if output is as expected
    results = xr.open_zarr(out_path)

    assert len(results.trajectory) == len(ctd_bgcs)

    for ctd_i, (traj, exp_bothloc) in enumerate(
        zip(results.trajectory, ctd_bgc_exp, strict=True)
    ):
        obs_surface = results.sel(trajectory=traj, obs=0)
        min_index = np.argmin(results.sel(trajectory=traj)["z"].data)
        obs_maxdepth = results.sel(trajectory=traj, obs=min_index)

        for obs, loc in [
            (obs_surface, "surface"),
            (obs_maxdepth, "maxdepth"),
        ]:
            exp = exp_bothloc[loc]
            for var in ["o2", "chl", "lat", "lon"]:
                obs_value = obs[var].values.item()
                exp_value = exp[var]
                assert np.isclose(obs_value, exp_value), (
                    f"Observation incorrect {ctd_i=} {loc=} {var=} {obs_value=} {exp_value=}."
                )
