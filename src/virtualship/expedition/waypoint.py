"""Waypoint class."""

from datetime import datetime

from pydantic import BaseModel, field_serializer

from ..location import Location
from .instrument_type import InstrumentType


class Waypoint(BaseModel):
    """A Waypoint to sail to with an optional time and an optional instrument."""

    location: Location
    time: datetime | None = None
    instrument: InstrumentType | list[InstrumentType] | None = None

    @field_serializer("instrument")
    def serialize_instrument(self, instrument):
        """Ensure InstrumentType is serialized as a string (or list of strings)."""
        if isinstance(instrument, list):
            return [inst.value for inst in instrument]
        return instrument.value if instrument else None
