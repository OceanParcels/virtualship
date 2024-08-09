import py
import xarray as xr
import matplotlib.pyplot as plt
import opensimplex
import numpy as np
import random


def ctd_make_realistic(zarr_path: str | py.path.LocalPath) -> None:
    original = xr.open_zarr(zarr_path)

    for ctd_i, traj in enumerate(original.trajectory):
        temperature = original.sel(trajectory=traj)["temperature"].values
        salinity = original.sel(trajectory=traj)["salinity"].values
        depth = original.sel(trajectory=traj)["z"].values

        temperature = temperature_noise(temperature, depth)

        fig, ax = plt.subplots()
        ax.plot(temperature, depth)
        plt.show()
        break


def temperature_noise(temperature: np.ndarray, depth: np.ndarray) -> np.ndarray:
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
