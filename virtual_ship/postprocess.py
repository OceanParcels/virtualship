import os
import numpy as np
import xarray as xr
import shutil
from scipy.ndimage import uniform_filter1d

def postprocess():
    '''Postprocesses CTD data and writes to csv files'''

    if os.path.isdir(os.path.join("results","CTDs")):
        i = 0
        filenames = os.listdir(os.path.join("results","CTDs"))
        for filename in sorted(filenames):
            if filename.endswith(".zarr"):
                try: #too many errors, just skip the faulty zarr files
                    i += 1
                    # Open output and read to x, y, z
                    ds = xr.open_zarr(os.path.join("results","CTDs",filename))
                    x = ds["lon"][:].squeeze()
                    y = ds["lat"][:].squeeze()
                    z = ds["z"][:].squeeze()
                    time = ds["time"][:].squeeze()
                    T = ds["temperature"][:].squeeze()
                    S = ds["salinity"][:].squeeze()
                    ds.close()

                    random_walk = np.random.random()/10
                    z_norm = (z-np.min(z))/(np.max(z)-np.min(z))
                    t_norm = np.linspace(0, 1, num=len(time))
                    # add smoothed random noise scaled with depth
                    # and random (reversed) diversion from initial through time scaled with depth
                    S = S + uniform_filter1d(
                        np.random.random(S.shape)/5*(1-z_norm) +
                        random_walk*(np.max(S).values - np.min(S).values)*(1-z_norm)*t_norm/10,
                        max(int(len(time)/40), 1))
                    T = T + uniform_filter1d(
                        np.random.random(T.shape)*5*(1-z_norm) -
                        random_walk/2*(np.max(T).values - np.min(T).values)*(1-z_norm)*t_norm/10,
                        max(int(len(time)/20), 1))

                    # reshaping data to export to csv
                    header = f"pressure [dbar],temperature [degC],salinity [g kg-1]"
                    data = np.column_stack([-z, T, S])
                    new_line = '\n'
                    np.savetxt(f"{os.path.join('results','CTDs','CTD_station_')}{i}.csv", data, fmt="%.4f", header=header, delimiter=',',
                                comments=f'longitude,{x[0].values},"{x.attrs}"{new_line}latitude,{y[0].values},"{y.attrs}"{new_line}start time,{time[0].values}{new_line}end time,{time[-1].values}{new_line}')
                    shutil.rmtree(os.path.join("results","CTDs",filename))
                except TypeError:
                    print(f"CTD file {filename} seems faulty, skipping.")
                    continue
        print("CTD data postprocessed.")
