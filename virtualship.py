from datetime import timedelta
from virtual_ship.virtual_ship_configuration import VirtualShipConfiguration
from virtual_ship.costs import costs
from virtual_ship.sailship import sailship
from virtual_ship.drifter_deployments import drifter_deployments
from virtual_ship.argo_deployments import argo_deployments
from virtual_ship.postprocess import postprocess

if __name__ == '__main__':
    config = VirtualShipConfiguration('student_input.json')
    drifter_time, argo_time, total_time = sailship(config)
    drifter_deployments(config, drifter_time)
    argo_deployments(config, argo_time)
    postprocess()
    print("All data has been gathered and postprocessed, returning home.")
    cost = costs(config, total_time)
    print(f"This cruise took {timedelta(seconds=total_time)} and would have cost {cost:,.0f} euros.")
