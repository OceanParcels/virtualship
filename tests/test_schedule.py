import py

from virtual_ship import Location, Schedule, Waypoint


def test_schedule(tmpdir: py.path.LocalPath) -> None:
    out_path = tmpdir.join("schedule.yaml")

    schedule = Schedule(
        [
            Waypoint(Location(0, 0), time=0, instrument=None),
            Waypoint(Location(1, 1), time=1, instrument=None),
        ]
    )
    schedule.to_yaml(out_path)

    schedule2 = Schedule.from_yaml(out_path)
    assert schedule == schedule2
