"""VirtualShipConfig class."""

from dataclasses import dataclass
from datetime import timedelta

from parcels import FieldSet

from .schedule import Schedule


@dataclass
class ArgoFloatConfig:
    """Configuration for argos floats."""

    fieldset: FieldSet
    min_depth: float
    max_depth: float
    drift_depth: float
    vertical_speed: float
    cycle_days: float
    drift_days: float


@dataclass
class ADCPConfig:
    """Configuration for ADCP instrument."""

    max_depth: float
    bin_size_m: int
    period: timedelta
    fieldset: FieldSet


@dataclass
class CTDConfig:
    """Configuration for CTD instrument."""

    stationkeeping_time: timedelta
    fieldset: FieldSet
    min_depth: float
    max_depth: float


@dataclass
class ShipUnderwaterSTConfig:
    """Configuration for underwater ST."""

    period: timedelta
    fieldset: FieldSet


@dataclass
class DrifterConfig:
    """Configuration for drifters."""

    fieldset: FieldSet
    depth: float
    lifetime: timedelta


@dataclass
class VirtualShipConfig:
    """Configuration of the virtual ship."""

    ship_speed: float  # m/s

    waypoints: Schedule

    argo_float_config: ArgoFloatConfig
    adcp_config: ADCPConfig | None  # if None, ADCP is disabled
    ctd_config: CTDConfig
    ship_underwater_st_config: (
        ShipUnderwaterSTConfig | None
    )  # if None, ship underwater st is disabled
    drifter_config: DrifterConfig

    def verify(self) -> None:
        """
        Verify this configuration is valid.

        :raises ValueError: If not valid.
        """
        if len(self.waypoints) < 2:
            raise ValueError("Waypoints require at least a start and an end.")

        if self.argo_float_config.max_depth > 0:
            raise ValueError("Argo float max depth must be negative or zero.")

        if self.argo_float_config.drift_depth > 0:
            raise ValueError("Argo float drift depth must be negative or zero.")

        if self.argo_float_config.vertical_speed >= 0:
            raise ValueError("Argo float vertical speed must be negative.")

        if self.argo_float_config.cycle_days <= 0:
            raise ValueError("Argo float cycle days must be larger than zero.")

        if self.argo_float_config.drift_days <= 0:
            raise ValueError("Argo drift cycle days must be larger than zero.")

        if self.adcp_config is not None and self.adcp_config.max_depth > 0:
            raise ValueError("ADCP max depth must be negative.")
