"""expedition_cost function."""

from datetime import timedelta

from .simulate_schedule import ScheduleResults


def expedition_cost(schedule_results: ScheduleResults, time_past: timedelta) -> float:
    """
    Calculate the cost of the expedition in US$.

    :param schedule_results: Results from schedule simulation.
    :param time_past: Time the expedition took.
    :returns: The calculated cost of the expedition in US$.
    """
    SHIP_COST_PER_DAY = 30000
    DRIFTER_DEPLOY_COST = 2500
    ARGO_DEPLOY_COST = 15000

    ship_cost = SHIP_COST_PER_DAY / 24 * time_past.total_seconds() // 3600
    num_argos = len(schedule_results.measurements_to_simulate.argo_floats)
    argo_cost = num_argos * ARGO_DEPLOY_COST
    num_drifters = len(schedule_results.measurements_to_simulate.drifters)
    drifter_cost = num_drifters * DRIFTER_DEPLOY_COST

    cost = ship_cost + argo_cost + drifter_cost
    return cost
