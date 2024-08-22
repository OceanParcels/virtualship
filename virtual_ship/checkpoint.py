from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_serializer, Field
from pathlib import Path
import yaml
from .schedule import Schedule


class Checkpoint(BaseModel):
    past_schedule: Schedule

    def to_yaml(self, file_path: str | Path) -> None:
        with open(file_path, "w") as file:
            yaml.dump(self.model_dump(by_alias=True), file)

    @classmethod
    def from_yaml(cls, file_path: str | Path) -> Checkpoint:
        with open(file_path, "r") as file:
            data = yaml.safe_load(file)
        return Checkpoint(**data)
