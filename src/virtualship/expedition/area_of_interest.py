"""AreaOfInterest class."""

from dataclasses import dataclass
from datetime import datetime

@dataclass
class SpatialRange:
    """Defines the geographic boundaries for an area of interest."""

    minimum_longitude: float
    maximum_longitude: float
    minimum_latitude: float
    maximum_latitude: float

@dataclass
class TimeRange:
    """Defines the temporal boundaries for an area of interest."""

    start_time: datetime
    end_time: datetime

@dataclass
class AreaOfInterest:
    """An area of interest with spatial and temporal boundaries."""

    spatial_range: SpatialRange
    time_range: TimeRange