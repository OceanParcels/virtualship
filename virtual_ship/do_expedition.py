from .schedule import Schedule
from pathlib import Path

import pyproj
from .ship_config import ShipConfig
from .checkpoint import Checkpoint
from .simulate_schedule import simulate_schedule
from .verify_schedule import verify_schedule
from .input_data import InputData
from .simulate_measurements import simulate_measurements
from .expedition_cost import expedition_cost


def do_expedition(expedition_dir: str | Path) -> None:
    if isinstance(expedition_dir, str):
        expedition_dir = Path(expedition_dir)

    # load ship configuration
    ship_config = _get_ship_config(expedition_dir)
    if ship_config is None:
        return

    # load schedule
    schedule = _get_schedule(expedition_dir)
    if schedule is None:
        return

    # load last checkpoint
    checkpoint = _load_checkpoint(expedition_dir)
    if checkpoint is None:
        checkpoint = Checkpoint(past_schedule=Schedule(waypoints=[]))

    # verify that schedule and checkpoint match
    if (
        not schedule.waypoints[: len(checkpoint.past_schedule.waypoints)]
        == checkpoint.past_schedule.waypoints
    ):
        print(
            "Past waypoints in schedule have been changed! Restore past schedule and only change future waypoints."
        )
        return

    # projection used to sail between waypoints
    projection = pyproj.Geod(ellps="WGS84")

    # load fieldsets
    input_data = _load_input_data(
        expedition_dir=expedition_dir, ship_config=ship_config
    )

    # verify schedule makes sense
    verify_schedule(projection, ship_config, schedule, input_data)

    # simulate the schedule
    schedule_results = simulate_schedule(
        projection=projection, ship_config=ship_config, schedule=schedule
    )
    if not schedule_results.success:
        print(
            f"It is currently {schedule_results.end_spacetime} and waypoint {schedule_results.failed_waypoint_i} could not be reached in time. Update your schedule and continue the expedition."
        )
        _save_checkpoint(
            Checkpoint(
                past_schedule=Schedule(
                    waypoints=schedule.waypoints[: schedule_results.failed_waypoint_i]
                )
            )
        )
        return

    # simulate measurements
    print("Simulating measurements. This may take a while..")
    simulate_measurements(
        expedition_dir,
        ship_config,
        input_data,
        schedule_results.measurements_to_simulate,
    )
    print("Done simulating measurements.")

    # calculate expedition cost in US$
    assert (
        schedule.waypoints[0].time is not None
    ), "First waypoint has no time. This should not be possible as it should have been verified before."
    time_past = schedule_results.end_spacetime.time - schedule.waypoints[0].time
    cost = expedition_cost(schedule_results, time_past)
    with open(expedition_dir.joinpath("results", "cost.txt"), "w") as file:
        file.writelines(f"cost: {cost} US$")
    print(f"This expedition took {time_past} and would have cost {cost:,.0f} US$.")


def _get_ship_config(expedition_dir: Path) -> ShipConfig | None:
    file_path = expedition_dir.joinpath("ship_config.yaml")
    try:
        return ShipConfig.from_yaml(file_path)
    except FileNotFoundError:
        print(f'Schedule not found. Save it to "{file_path}".')
        return None


def _load_input_data(expedition_dir: Path, ship_config: ShipConfig) -> InputData:
    return InputData.load(
        directory=expedition_dir.joinpath("input_data"),
        load_adcp=ship_config.adcp_config is not None,
        load_argo_float=ship_config.argo_float_config is not None,
        load_ctd=ship_config.ctd_config is not None,
        load_drifter=ship_config.drifter_config is not None,
        load_ship_underwater_st=ship_config.ship_underwater_st_config is not None,
    )


def _get_schedule(expedition_dir: Path) -> Schedule | None:
    file_path = expedition_dir.joinpath("schedule.yaml")
    try:
        return Schedule.from_yaml(file_path)
    except FileNotFoundError:
        print(f'Schedule not found. Save it to "{file_path}".')
        return None


def _load_checkpoint(expedition_dir: Path) -> Checkpoint | None:
    file_path = expedition_dir.joinpath("checkpoint.yaml")
    try:
        return Checkpoint.from_yaml(file_path)
    except FileNotFoundError:
        return None


def _save_checkpoint(checkpoint: Checkpoint, expedition_dir: Path) -> None:
    file_path = expedition_dir.joinpath("checkpoint.yaml")
    checkpoint.to_yaml(file_path)
