from dataclasses import dataclass
from .location import Location
from datetime import datetime
from .instrument_type import InstrumentType


@dataclass
class Waypoint:
    location: Location
    time: datetime | None = None
    instrument: InstrumentType | None = None
