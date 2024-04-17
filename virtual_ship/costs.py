"""costs function."""


def costs(config, total_time):
    """
    Calculate the cost of the virtual ship (in US$).

    :param config: The cruise configuration.
    :param total_time: Time cruised in seconds.
    :returns: The calculated cost of the cruise.
    """
    ship_cost_per_day = 30000
    drifter_deploy_cost = 2500
    argo_deploy_cost = 15000

    ship_cost = ship_cost_per_day / 24 * total_time // 3600
    argo_cost = len(config.argo_deploylocations) * argo_deploy_cost
    drifter_cost = len(config.drifter_deploylocations) * drifter_deploy_cost

    cost = ship_cost + argo_cost + drifter_cost
    return cost
