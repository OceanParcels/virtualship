from virtual_ship.make_realistic import ctd_make_realistic


def test_ctd_make_realistic() -> None:
    ctd_make_realistic("ctd.zarr")
