from dataclasses import dataclass
from .location import Location
from datetime import datetime
from .instrument_deployment import InstrumentDeployment


@dataclass
class Waypoint:
    location: Location
    time: datetime | None = None
    instrument: InstrumentDeployment | None = None
