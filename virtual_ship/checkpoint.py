"""Checkpoint class."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

from .schedule import Schedule


class Checkpoint(BaseModel):
    """
    Checkpoint is schedule simulation.

    Until where the schedule execution proceeded without troubles.
    """

    past_schedule: Schedule

    def to_yaml(self, file_path: str | Path) -> None:
        """
        Write checkpoint to yaml file.

        :param file_path: Path to the file to write to.
        """
        with open(file_path, "w") as file:
            yaml.dump(self.model_dump(by_alias=True), file)

    @classmethod
    def from_yaml(cls, file_path: str | Path) -> Checkpoint:
        """
        Load checkpoint from yaml file.

        :param file_path: Path to the file to load from.
        :returns: The checkpoint.
        """
        with open(file_path, "r") as file:
            data = yaml.safe_load(file)
        return Checkpoint(**data)
