import py

from virtual_ship.make_realistic import adcp_make_realistic


def test_adcp_make_realistic(tmpdir: py.path.LocalPath) -> None:
    # add noise and convert to CSV
    file = adcp_make_realistic("adcp.zarr", out_dir=tmpdir, prefix="ADCP")

    # check if CSV is ok and can be loaded
    netCDF4.Dataset(file, mode="r")
