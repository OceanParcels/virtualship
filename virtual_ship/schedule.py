"""Schedule class."""

from __future__ import annotations

from pathlib import Path
from pydantic import BaseModel, ConfigDict
import yaml
from .waypoint import Waypoint


class Schedule(BaseModel):
    """Schedule of the virtual ship."""

    waypoints: list[Waypoint]

    model_config = ConfigDict(extra="forbid")

    def to_yaml(self, file_path: str | Path) -> None:
        with open(file_path, "w") as file:
            yaml.dump(self.model_dump(by_alias=True), file)

    @classmethod
    def from_yaml(cls, file_path: str | Path) -> Schedule:
        with open(file_path, "r") as file:
            data = yaml.safe_load(file)
        return Schedule(**data)
