"""costs function."""

from datetime import timedelta

from .virtual_ship_configuration import VirtualShipConfig


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
    argo_cost = len(config.argo_float_deploy_locations) * argo_deploy_cost
    drifter_cost = len(config.drifter_deploy_locations) * drifter_deploy_cost

    cost = ship_cost + argo_cost + drifter_cost
    return cost
