"""Waypoint class."""

from dataclasses import dataclass
from datetime import datetime

from ..location import Location
from .instrument_type import InstrumentType


@dataclass
class Waypoint:
    """A Waypoint to sail to with an optional time and an optional instrument."""

    location: Location
    time: datetime | None = None
    instrument: InstrumentType | list[InstrumentType] | None = None
