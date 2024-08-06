"""Code for the Virtual Ship Classroom, where Marine Scientists can combine Copernicus Marine Data with an OceanParcels ship to go on a virtual expedition."""

from . import instruments, sailship
from .instrument_type import InstrumentType
from .location import Location
from .planning_error import PlanningError
from .spacetime import Spacetime
from .waypoint import Waypoint

__all__ = [
    "InstrumentType",
    "Location",
    "PlanningError",
    "Spacetime",
    "Waypoint",
    "instruments",
    "sailship",
]
