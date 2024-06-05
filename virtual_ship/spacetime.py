"""Location class. See class description."""

from dataclasses import dataclass

from .location import Location


@dataclass
# TODO I take suggestions for a better name
class Spacetime:
    """A location and time."""

    location: Location
    time: float