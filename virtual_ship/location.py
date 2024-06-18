"""Location class. See class description."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Location:
    """A location on a sphere."""

    longitude: float
    latitude: float

    @property
    def lon(self) -> float:
        """
        Shorthand for longitude variable.

        :returns: Longitude variable.
        """
        return self.longitude

    @property
    def lat(self) -> float:
        """
        Shorthand for latitude variable.

        :returns: Latitude variable.
        """
        return self.latitude
