"""Code for the Virtual Ship Classroom, where Marine Scientists can combine Copernicus Marine Data with an OceanParcels ship to go on a virtual expedition."""

from .do_expedition import do_expedition
from .instrument_type import InstrumentType
from .location import Location
from .schedule import Schedule
from .ship_config import (
    ADCPConfig,
    ArgoFloatConfig,
    CTDConfig,
    DrifterConfig,
    ShipConfig,
    ShipUnderwaterSTConfig,
)
from .spacetime import Spacetime
from .waypoint import Waypoint

__all__ = [
    "ADCPConfig",
    "ArgoFloatConfig",
    "CTDConfig",
    "DrifterConfig",
    "InstrumentType",
    "Location",
    "Schedule",
    "ShipConfig",
    "ShipUnderwaterSTConfig",
    "Spacetime",
    "Waypoint",
    "do_expedition",
    "instruments",
]
