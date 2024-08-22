import py

from virtual_ship import Location, Schedule, Waypoint
from datetime import datetime, timedelta


def test_schedule(tmpdir: py.path.LocalPath) -> None:
    out_path = tmpdir.join("schedule.yaml")

    # arbitrary time for testing
    base_time = datetime.strptime("1950-01-01", "%Y-%m-%d")

    schedule = Schedule(
        waypoints=[
            Waypoint(Location(0, 0), time=base_time, instrument=None),
            Waypoint(
                Location(1, 1), time=base_time + timedelta(hours=1), instrument=None
            ),
        ]
    )
    schedule.to_yaml(out_path)

    schedule2 = Schedule.from_yaml(out_path)
    assert schedule == schedule2
