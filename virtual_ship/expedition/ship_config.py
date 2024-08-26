"""ShipConfig and supporting classes."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ArgoFloatConfig(BaseModel):
    """Configuration for argos floats."""

    min_depth_meter: float = Field(le=0.0)
    max_depth_meter: float = Field(le=0.0)
    drift_depth_meter: float = Field(le=0.0)
    vertical_speed_meter_per_second: float = Field(lt=0.0)
    cycle_days: float = Field(gt=0.0)
    drift_days: float = Field(gt=0.0)


class ADCPConfig(BaseModel):
    """Configuration for ADCP instrument."""

    max_depth_meter: float = Field(le=0.0)
    num_bins: int = Field(gt=0.0)
    period: timedelta = Field(
        serialization_alias="period_minutes",
        validation_alias="period_minutes",
        gt=timedelta(),
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_serializer("period")
    def _serialize_period(self, value: timedelta, _info):
        return value.total_seconds() / 60.0


class CTDConfig(BaseModel):
    """Configuration for CTD instrument."""

    stationkeeping_time: timedelta = Field(
        serialization_alias="stationkeeping_time_minutes",
        validation_alias="stationkeeping_time_minutes",
        gt=timedelta(),
    )
    min_depth_meter: float = Field(le=0.0)
    max_depth_meter: float = Field(le=0.0)

    model_config = ConfigDict(populate_by_name=True)

    @field_serializer("stationkeeping_time")
    def _serialize_stationkeeping_time(self, value: timedelta, _info):
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
    def _serialize_period(self, value: timedelta, _info):
        return value.total_seconds() / 60.0


class DrifterConfig(BaseModel):
    """Configuration for drifters."""

    depth_meter: float = Field(le=0.0)
    lifetime: timedelta = Field(
        serialization_alias="lifetime_minutes",
        validation_alias="lifetime_minutes",
        gt=timedelta(),
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_serializer("lifetime")
    def _serialize_lifetime(self, value: timedelta, _info):
        return value.total_seconds() / 60.0


class ShipConfig(BaseModel):
    """Configuration of the virtual ship."""

    ship_speed_meter_per_second: float = Field(gt=0.0)
    """
    Velocity of the ship in meters per second.
    """

    argo_float_config: ArgoFloatConfig | None = None
    """
    Argo float configuration.

    If None, no argo floats can be deployed.
    """

    adcp_config: ADCPConfig | None = None
    """
    ADCP configuration.

    If None, no ADCP measurements will be performed.
    """

    ctd_config: CTDConfig | None = None
    """
    CTD configuration.

    If None, no CTDs can be cast.
    """

    ship_underwater_st_config: ShipUnderwaterSTConfig | None = None
    """
    Ship underwater salinity temperature measurementconfiguration.

    If None, no ST measurements will be performed.
    """

    drifter_config: DrifterConfig | None = None
    """
    Drifter configuration.

    If None, no drifters can be deployed.
    """

    model_config = ConfigDict(extra="forbid")

    def to_yaml(self, file_path: str | Path) -> None:
        """
        Write config to yaml file.

        :param file_path: Path to the file to write to.
        """
        with open(file_path, "w") as file:
            yaml.dump(self.model_dump(by_alias=True), file)

    @classmethod
    def from_yaml(cls, file_path: str | Path) -> ShipConfig:
        """
        Load config from yaml file.

        :param file_path: Path to the file to load from.
        :returns: The config.
        """
        with open(file_path, "r") as file:
            data = yaml.safe_load(file)
        return ShipConfig(**data)
