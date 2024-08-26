"""adcp_make_realistic function."""

import numpy as np
import py
import xarray as xr


def adcp_make_realistic(
    zarr_path: str | py.path.LocalPath,
    out_dir: str | py.path.LocalPath,
    prefix: str,
) -> py.path.LocalPath:
    """
    Take simulated ADCP data, add noise, then save in (an inconvenient educational) CSV format.

    :param zarr_path: Input simulated data.
    :param out_dir: Output directory for CSV file.
    :param prefix: Prefix for CSV file.
    :returns: Path to created file.
    """
    original = xr.open_zarr(zarr_path)

    times = original.sel(trajectory=1)["time"].values
    depths = original.sel(obs=0)["z"].values
    lats = original.sel(trajectory=1)["lat"].values
    lons = original.sel(trajectory=1)["lon"].values
    all_us = original["U"].values
    all_vs = original["V"].values

    all_us, all_vs = _add_noise(times, depths, all_us, all_vs)

    csv = _to_csv(times, depths, lats, lons, all_us, all_vs)
    out_file = (
        out_dir.join(f"{prefix}.csv")
        if isinstance(out_dir, py.path.LocalPath)
        else f"{out_dir}/{prefix}.csv"
    )
    with open(out_file, "w") as out_cnv:
        out_cnv.write(csv)

    return out_file


def _add_noise(
    times: np.ndarray, depths: np.ndarray, all_us: np.ndarray, all_vs: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """
    Return the provided data with added noise.

    The noise is not a realistic nor based on anything physics, but simply an attempt to have the data look somewhat similar to real ADCP data.

    :param times: Times of the measurements.
    :param depths: Bin depths measured by ADCP.
    :param all_us: All U measurements.
    :param all_vs: All V measurements.
    :return: U and V with added noise.
    """
    surface_noise = (
        
        noise = np.random.random((all_us.shape)) * 0.1 * max(all_us)
        noise = np.where((depths > 100) & (depths < 240), 1, 0)
        # for i, idx in all_us:
        for i, us in enumerate(all_us):
           noise.append([(depths < -100) & (depths > -240)] * (random.uniform(-1, 1) * np.random.random_sample(len(depths))) * us.max())

        for 
        all_us[(depths < -100) & (depths > -240)] * 0.1 * np.random.random_sample(all_us) * 0.1 * max(all_us)
        # np.random.random_sample(all_us) * 0.1 * max(all_us)
        # * np.where((depths > 100) & (depths < 240), 1, 0)
    )
    vertical_noise = (
        for i in range(len(all_us)):
            all_us[i] += noise
            all_vs[i] += noise
    )
    #     0.05
    #     * np.maximum(1.0 + depth / 1000.0, 0.1)
    #     * np.random.random_sample(len(depths))
    # )
    return all_us, all_vs


def _to_csv(
    times: np.ndarray,
    depths: np.ndarray,
    lats: np.ndarray,
    lons: np.ndarray,
    all_us: np.ndarray,
    all_vs: np.ndarray,
) -> str:
    meta = "# depths (m): " + ",".join([str(d) for d in depths])
    header = f"time,lat,lon,{','.join(['u' + str(n) + ',v' + str(n) for n in range(len(depths))])}"
    data = [
        f"{str(time)},{lat},{lon},{','.join([str(u) + ',' + str(v) for u, v in zip(us, vs)])}"
        for time, lat, lon, us, vs in zip(times, lats, lons, all_us.T, all_vs.T)
    ]

    lines = [meta, header] + data
    return "\n".join(lines)
