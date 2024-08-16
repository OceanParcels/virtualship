from __future__ import annotations

from dataclasses import dataclass
from .waypoint import Waypoint
import yaml

@dataclass
class Schedule:
    """Schedule of the virtual ship."""

    waypoints: list[Waypoint]

    def from_yaml(cls, path: str) -> Schedule:
        """Load schedule from YAML file."""
        pass

    def to_yaml(self, path: str) -> None:
        """Save schedule to YAML file."""
        print(yaml.dumpf([waypoint.to_dict() for waypoint in self.waypoints], path))
        pass