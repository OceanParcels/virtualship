import csv

import py

from virtual_ship.make_realistic import adcp_make_realistic


def test_adcp_make_realistic(tmpdir: py.path.LocalPath) -> None:
    # add noise and convert to CSV
    file = adcp_make_realistic("adcp.zarr", out_dir=tmpdir, prefix="ADCP")

    # check if CSV is ok and can be loaded
    with open(file, mode="r", newline="") as csvfile:
        # ignore lines starting with #, we assume that's metadata or comments
        reader = csv.reader(line for line in csvfile if not line.startswith("#"))
        for _ in reader:
            pass  # iterate through the rows to check validity
