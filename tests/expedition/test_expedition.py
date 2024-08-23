from virtual_ship.expedition import do_expedition
from pytest import CaptureFixture


def test_expedition(capfd: CaptureFixture) -> None:
    do_expedition("expedition_dir")
    # out, _ = capfd.readouterr()
    # assert "This expedition took" in out, "Expedition did not complete successfully."
