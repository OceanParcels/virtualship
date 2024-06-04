"""Location class. See class description."""

from dataclasses import dataclass

from .location import Location
import numpy as np


@dataclass
# TODO I take suggestions for a better name
class Spacetime:
    """A location and time."""

    location: Location
    time: np.datetime64
