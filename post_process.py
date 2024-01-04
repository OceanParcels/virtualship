#!/usr/bin/env python3
# Post proces .results folder created by cruise_simulation.py

### Post-processing
import xarray as xr
import numpy as np
from scipy.ndimage import uniform_filter1d

# rewrite CTD data to cvs
ctd = 6
for i in range(1, ctd+1):
    
    # Open output and read to x, y, z
    ds = xr.open_zarr(f"./results/CTD_test_{i}.zarr")
    x = ds["lon"][:].squeeze()
    y = ds["lat"][:].squeeze()
    z = ds["z"][:].squeeze()
    time = ds["time"][:].squeeze()
    T = ds["temperature"][:].squeeze()
    S = ds["salinity"][:].squeeze()
    ds.close()

    # add some noise
    random_walk = np.random.random()/10
    z_norm = (z-np.min(z))/(np.max(z)-np.min(z))
    t_norm = np.linspace(0, 1, num=len(time))
    # dS = abs(np.append(0, np.diff(S))) # scale noise with gradient
    # for j in range(5, 0, -1):
    #     dS[dS<1*10**-j] = 0.5-j/10
    # add smoothed random noise scaled with depth (and OPTIONAL with gradient for S) 
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
    header = f"'pressure [hPa]','temperature [degC]', 'salinity [g kg-1]'"
    data = np.column_stack([(z/10), T, S])
    new_line = '\n'
    np.savetxt(f"./results/CTD_station_{i}.csv", data, fmt="%.4f", header=header, delimiter=',', 
               comments=f'{x.attrs}{new_line}{x[0].values}{new_line}{y.attrs}{new_line}{y[0].values}{new_line}start time: {time[0].values}{new_line}end time: {time[-1].values}{new_line}')

