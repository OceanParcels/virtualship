"""costs function."""

from datetime import timedelta

from .instrument_type import InstrumentType
from .virtual_ship_config import VirtualShipConfig


def costs(config: VirtualShipConfig, total_time: timedelta):
    """
    Calculate the cost of the virtual ship (in US$).

    :param config: The cruise configuration.
    :param total_time: Time cruised.
    :returns: The calculated cost of the cruise.
    """
    ship_cost_per_day = 30000
    drifter_deploy_cost = 2500
    argo_deploy_cost = 15000

    ship_cost = ship_cost_per_day / 24 * total_time.total_seconds() // 3600
    num_argos = len(
        [
            waypoint
            for waypoint in config.waypoints
            if waypoint.instrument is InstrumentType.ARGO_FLOAT
        ]
    )
    argo_cost = num_argos * argo_deploy_cost
    num_drifters = len(
        [
            waypoint
            for waypoint in config.waypoints
            if waypoint.instrument is InstrumentType.DRIFTER
        ]
    )
    drifter_cost = num_drifters * drifter_deploy_cost

    cost = ship_cost + argo_cost + drifter_cost
    return cost
