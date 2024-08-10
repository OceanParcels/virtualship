import py
import seabird

from virtual_ship.make_realistic import ctd_make_realistic


def test_ctd_make_realistic(tmpdir: py.path.LocalPath) -> None:
    # add noise and convert to cnv
    files = ctd_make_realistic("ctd.zarr", out_dir=tmpdir, prefix="CTD_")

    # check if cnv is ok and can be loaded
    for file in files:
        seabird.fCNV(file)
