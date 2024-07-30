"""Code for the Virtual Ship Classroom, where Marine Scientists can combine Copernicus Marine Data with an OceanParcels ship to go on a virtual expedition."""

from . import instruments, sailship
from .location import Location
from .spacetime import Spacetime
from .waypoint import Waypoint
from .instrument_type import InstrumentType

__all__ = [
    "Location",
    "Spacetime",
    "instruments",
    "sailship",
    "InstrumentType",
    "Waypoint",
]
