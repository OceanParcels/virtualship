"""Waypoint class."""

from dataclasses import dataclass
from datetime import datetime

from .instrument_type import InstrumentType
from .location import Location


@dataclass
class Waypoint:
    """A Waypoint to sail to."""

    location: Location
    time: datetime | None = None
    instrument: InstrumentType | None = None
