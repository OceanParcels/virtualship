"""VirtualShipConfig class."""

from __future__ import annotations
from datetime import timedelta

from parcels import FieldSet
from pathlib import Path
from pydantic import BaseModel, ConfigDict, field_serializer, field_validator, Field
import yaml
from typing import Any


class ArgoFloatConfig(BaseModel):
    """Configuration for argos floats."""

    min_depth: float = Field(le=0.0)
    max_depth: float = Field(le=0.0)
    drift_depth: float = Field(le=0.0)
    vertical_speed: float = Field(lt=0.0)
    cycle_days: float = Field(gt=0.0)
    drift_days: float = Field(gt=0.0)


class ADCPConfig(BaseModel):
    """Configuration for ADCP instrument."""

    max_depth: float = Field(le=0.0)
    bin_size_m: int = Field(gt=0.0)
    period: timedelta = Field(
        serialization_alias="period_minutes",
        validation_alias="period_minutes",
        gt=timedelta(),
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_serializer("period")
    def serialize_period(self, value: timedelta, _info):
        return value.total_seconds() / 60.0


class CTDConfig(BaseModel):
    """Configuration for CTD instrument."""

    stationkeeping_time: timedelta = Field(
        serialization_alias="stationkeeping_time_minutes",
        validation_alias="stationkeeping_time_minutes",
        gt=timedelta(),
    )
    min_depth: float = Field(ge=0.0)
    max_depth: float = Field(ge=0.0)

    model_config = ConfigDict(populate_by_name=True)

    @field_serializer("stationkeeping_time")
    def serialize_stationkeeping_time(self, value: timedelta, _info):
        return value.total_seconds() / 60.0


class ShipUnderwaterSTConfig(BaseModel):
    """Configuration for underwater ST."""

    period: timedelta = Field(
        serialization_alias="period_minutes",
        validation_alias="period_minutes",
        gt=timedelta(),
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_serializer("period")
    def serialize_period(self, value: timedelta, _info):
        return value.total_seconds() / 60.0


class DrifterConfig(BaseModel):
    """Configuration for drifters."""

    depth: float = Field(le=0.0)
    lifetime: timedelta = Field(
        serialization_alias="lifetime_minutes",
        validation_alias="lifetime_minutes",
        gt=timedelta(),
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_serializer("lifetime")
    def serialize_lifetime(self, value: timedelta, _info):
        return value.total_seconds() / 60.0


class ShipConfig(BaseModel):
    """Configuration of the virtual ship."""

    ship_speed: float = Field(gt=0.0)
    """
    Velocity of the ship in meters per second.
    """

    argo_float_config: ArgoFloatConfig | None = None
    """
    Argo float configuration.
    
    If None, no argo floats can be deployed.
    """

    adcp_config: ADCPConfig | None
    """
    ADCP configuration.

    If None, no ADCP measurements will be performed.
    """

    ctd_config: CTDConfig | None
    """
    CTD configuration.

    If None, no CTDs can be cast.
    """

    ship_underwater_st_config: ShipUnderwaterSTConfig | None
    """
    Ship underwater salinity temperature measurementconfiguration.
    
    If None, no ST measurements will be performed.
    """

    drifter_config: DrifterConfig | None
    """
    Drifter configuration.
    
    If None, no drifters can be deployed.
    """

    model_config = ConfigDict(extra="forbid")

    def to_yaml(self, file_path: str | Path) -> None:
        with open(file_path, "w") as file:
            yaml.dump(self.model_dump(by_alias=True), file)

    @classmethod
    def from_yaml(cls, file_path: str | Path) -> ShipConfig:
        with open(file_path, "r") as file:
            data = yaml.safe_load(file)
        return ShipConfig(**data)
