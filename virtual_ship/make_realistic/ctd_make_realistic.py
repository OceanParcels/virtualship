import py
import xarray as xr
import opensimplex
import numpy as np
import random


def ctd_make_realistic(
    zarr_path: str | py.path.LocalPath, out_dir: str | py.path.LocalPath, prefix: str
) -> list[py.path.LocalPath]:
    original = xr.open_zarr(zarr_path)

    files = []
    for ctd_i, traj in enumerate(original.trajectory):
        time = original.sel(trajectory=traj)["time"].values
        reltimesec = (time - time[0]) / np.timedelta64(1, "s")
        latitude = original.sel(trajectory=traj)["lat"].values
        longitude = original.sel(trajectory=traj)["lon"].values
        temperature = original.sel(trajectory=traj)["temperature"].values
        salinity = original.sel(trajectory=traj)["salinity"].values
        depth = original.sel(trajectory=traj)["z"].values

        # temperature = _add_temperature_noise(temperature, depth)

        out_file = out_dir.join(f"{prefix}{ctd_i}.cnv")
        files.append(out_file)

        cnv = _to_cnv(
            filename=str(out_file),
            latitudes=latitude,
            longitudes=longitude,
            times=reltimesec,
            temperatures=temperature,
            depths=depth,
            salinities=salinity,
        )

        with open(out_file, "w") as out_cnv:
            out_cnv.write(cnv)

    return files


def _add_temperature_noise(temperature: np.ndarray, depth: np.ndarray) -> np.ndarray:
    surface_noise = (
        2.0
        * (np.random.random_sample(len(temperature)) * 2.0 - 1)
        * np.exp(depth / 4.0)
    )
    noise = (
        0.05
        * np.maximum(1.0 + depth / 1000.0, 0.1)
        * np.random.random_sample(len(temperature))
    )
    drift = (
        0.3
        * (np.random.random() * 2.0 - 1)
        * np.array(range(len(temperature)))
        / len(temperature)
    )
    opensimplex.seed(np.random.randint(999999))
    noise2 = (
        2.0
        * np.maximum(1.0 + depth / 1000.0, 0.1)
        * (
            np.array([opensimplex.noise2(n / 30, 0.0) for n in range(len(temperature))])
            ** 8
        )
    )
    opensimplex.seed(np.random.randint(999999))
    noise3 = 0.1 * (
        np.array([opensimplex.noise2(n / 8, 0.0) for n in range(len(temperature))]) ** 2
    )

    return temperature + surface_noise + drift + noise + noise3 + noise2


def _to_cnv(
    filename: str,
    latitudes: np.ndarray,
    longitudes: np.ndarray,
    times: np.ndarray,
    temperatures: np.ndarray,
    depths: np.ndarray,
    salinities: np.ndarray,
) -> str:
    """
    Convert data to CNV.

    :param time: Elapsed time since first measurement in seconds.
    :param temperature: Temperature data.
    :param depth: Depth data.
    :returns: The CNV.

    """
    header = rf"""
* Sea-Bird SBE 9 Data File:
* FileName = {filename}
# start_time = Aug 02 2024 21:29:45 [NMEA time, first data scan]
# bad_flag = -9.990e-29
# file_type = ascii
# name 0 = scan: Scan Count
# name 1 = timeS: Time, Elapsed [seconds]
# name 2 = latitude: Latitude [deg]
# name 3 = longitude: Longitude [deg]
# name 4 = depSM: Depth [salt water, m]
# name 5 = t090C: Temperature [ITS-90, deg C]
# name 6 = sal00: Salinity, Practical [PSU]
*END*
""".strip()

    random_time_offset = random.random()

    rows = [
        f"{_i_col(13 + 24 * n)}{_f_col(time + random_time_offset, 3)}{_f_col(lat, 5)}{_f_col(lon, 5)}{_f_col(-depth, 3)}{_f_col(temp, 4)}{_f_col(sal, 4)}"
        for n, (time, temp, lat, lon, depth, sal) in enumerate(
            zip(times, temperatures, latitudes, longitudes, depths, salinities)
        )
    ]

    cnv = header + "\n" + "\n".join(rows) + "\n"

    return cnv


def _make_column(val: str) -> str:
    return val.rjust(11)


def _i_col(val: int) -> str:
    return _make_column(str(val))


def _f_col(val: float, digits: int) -> str:
    return _make_column(str(round(val, digits)))
