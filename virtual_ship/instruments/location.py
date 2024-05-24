"""Location class."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Location:
    """A location on a sphere."""

    latitude: float
    longitude: float

    @property
    def lat(self) -> float:
        """
        Shorthand for latitude variable.

        :returns: Latitude variable.
        """
        return self.latitude

    @property
    def lon(self) -> float:
        """
        Shorthand for longitude variable.

        :returns: Longitude variable.
        """
        return self.longitude
