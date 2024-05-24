from dataclasses import dataclass


@dataclass(frozen=True)
class Location:
    latitude: float
    longitude: float

    @property
    def lat(self) -> float:
        return self.latitude

    @property
    def lon(self) -> float:
        return self.longitude
