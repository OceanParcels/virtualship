from virtual_ship import Schedule, Waypoint, Location

def test_schedule() -> None:
    schedule = Schedule([Waypoint(Location(0, 0), 0), Waypoint(Location(1, 1), 1)])
    schedule.to_yaml("schedule.yaml")