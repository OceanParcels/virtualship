"""Schedule class."""

from __future__ import annotations

from dataclasses import dataclass

import yaml

from .location import Location
from .waypoint import Waypoint


@dataclass
class Schedule:
    """Schedule of the virtual ship."""

    waypoints: list[Waypoint]

    @classmethod
    def from_yaml(cls, path: str) -> Schedule:
        """
        Load schedule from YAML file.

        :param path: The file to read from.
        :returns: Schedule of waypoints from the YAML file.
        """
        with open(path, "r") as in_file:
            data = yaml.safe_load(in_file)
            waypoints = [
                Waypoint(
                    location=Location(waypoint["lat"], waypoint["lon"]),
                    time=waypoint["time"],
                    instrument=waypoint["instrument"],
                )
                for waypoint in data
            ]
        return Schedule(waypoints)

    def to_yaml(self, path: str) -> None:
        """
        Save schedule to YAML file.

        :param path: The file to write to.
        """
        with open(path, "w") as out_file:
            print(
                yaml.dump(
                    [
                        {
                            "lat": waypoint.location.lat,
                            "lon": waypoint.location.lon,
                            "time": waypoint.time,
                            "instrument": waypoint.instrument,
                        }
                        for waypoint in self.waypoints
                    ],
                    out_file,
                )
            )
        pass
