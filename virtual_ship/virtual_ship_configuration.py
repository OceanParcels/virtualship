"""VirtualShipConfig class."""

from dataclasses import dataclass
from datetime import datetime

import numpy as np
from parcels import FieldSet

from .location import Location


@dataclass
class ArgoFloatConfig:
    """Configuration for argos floats."""

    fieldset: FieldSet
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


@dataclass
class VirtualShipConfig:
    """Configuration of the virtual ship."""

    start_time: datetime
    route_coordinates: list[Location]

    adcp_fieldset: FieldSet
    ship_underwater_st_fieldset: FieldSet
    ctd_fieldset: FieldSet
    drifter_fieldset: FieldSet

    argo_float_deploy_locations: list[Location]
    drifter_deploy_locations: list[Location]
    ctd_deploy_locations: list[Location]

    argo_float_config: ArgoFloatConfig
    adcp_config: ADCPConfig

    def verify(self) -> None:
        """
        Verify this configuration is valid.

        :raises ValueError: If not valid.
        """
        if len(self.route_coordinates) < 2:
            raise ValueError("Route needs to consist of at least locations.")

        if not all(
            [self._is_valid_location(coord) for coord in self.route_coordinates]
        ):
            raise ValueError("Invalid coordinates in route.")

        if not all(
            [
                self._is_valid_location(coord)
                for coord in self.argo_float_deploy_locations
            ]
        ):
            raise ValueError("Argo float deploy locations are not valid coordinates.")

        if not all(
            [
                any(
                    [
                        np.isclose(deploy.lat, coord.lat)
                        and np.isclose(deploy.lon, coord.lon)
                        for coord in self.route_coordinates
                    ]
                )
                for deploy in self.argo_float_deploy_locations
            ]
        ):
            raise ValueError(
                "Argo float deploy locations are not exactly on route coordinates."
            )

        if not all(
            [self._is_valid_location(coord) for coord in self.drifter_deploy_locations]
        ):
            raise ValueError("Drifter deploy locations are not valid coordinates.")

        if not all(
            [
                any(
                    [
                        np.isclose(deploy.lat, coord.lat)
                        and np.isclose(deploy.lon, coord.lon)
                        for coord in self.route_coordinates
                    ]
                )
                for deploy in self.drifter_deploy_locations
            ]
        ):
            raise ValueError(
                "Drifter deploy locations are not exactly on route coordinates."
            )

        if not all(
            [self._is_valid_location(coord) for coord in self.ctd_deploy_locations]
        ):
            raise ValueError("CTD deploy locations are not valid coordinates.")

        if not all(
            [
                any(
                    [
                        np.isclose(deploy.lat, coord.lat)
                        and np.isclose(deploy.lon, coord.lon)
                        for coord in self.route_coordinates
                    ]
                )
                for deploy in self.ctd_deploy_locations
            ]
        ):
            raise ValueError(
                "CTD deploy locations are not exactly on route coordinates."
            )

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

        if self.adcp_config.max_depth > 0:
            raise ValueError("ADCP max depth must be negative.")

    @staticmethod
    def _is_valid_location(location: Location) -> bool:
        return (
            location.lat >= -90
            and location.lat <= 90
            and location.lon >= -180
            and location.lon <= 360
        )
