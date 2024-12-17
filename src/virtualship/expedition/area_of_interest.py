"""AreaOfInterest class."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self

Longitude = Annotated[float, Field(..., ge=-180, le=180)]
Latitude = Annotated[float, Field(..., ge=-90, le=90)]
Depth = float  # TODO: insert a minimum depth here? e.g., `Annotated[float, Field(..., ge=0)]`


class SpatialRange(BaseModel):
    """Defines the geographic boundaries for an area of interest."""

    minimum_longitude: Longitude
    maximum_longitude: Longitude
    minimum_latitude: Latitude
    maximum_latitude: Latitude
    minimum_depth: Depth | None = None
    maximum_depth: Depth | None = None

    @model_validator(mode="after")
    def _check_lon_lat_domain(self) -> Self:
        if not self.minimum_longitude < self.maximum_longitude:
            raise ValueError("minimum_longitude must be less than maximum_longitude")
        if not self.minimum_latitude < self.maximum_latitude:
            raise ValueError("minimum_latitude must be less than maximum_latitude")

        if sum([self.minimum_depth is None, self.maximum_depth is None]) == 1:
            raise ValueError("Both minimum_depth and maximum_depth must be provided.")

        if self.minimum_depth is None:
            return self

        if not self.minimum_depth < self.maximum_depth:
            raise ValueError("minimum_depth must be less than maximum_depth")
        return self


class TimeRange(BaseModel):
    """Defines the temporal boundaries for an area of interest."""

    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def _check_time_range(self) -> Self:
        if not self.start_time < self.end_time:
            raise ValueError("start_time must be before end_time")
        return self


class AreaOfInterest(BaseModel):
    """An area of interest with spatial and temporal boundaries."""

    spatial_range: SpatialRange
    time_range: TimeRange
