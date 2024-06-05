"""Location class. See class description."""

from dataclasses import dataclass

import numpy as np

from .location import Location


@dataclass
# TODO I take suggestions for a better name
class Spacetime:
    """A location and time."""

    location: Location
    time: np.datetime64
