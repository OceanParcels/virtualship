"""do_expedition function."""

import os
import shutil
from pathlib import Path

import pyproj

from virtualship.cli._fetch import get_existing_download, get_space_time_region_hash
from virtualship.utils import (
    CHECKPOINT,
    _get_schedule,
    _get_ship_config,
    get_instruments_in_schedule,
)

from .checkpoint import Checkpoint
from .expedition_cost import expedition_cost
from .input_data import InputData
from .schedule import Schedule
from .ship_config import ShipConfig
from .simulate_measurements import simulate_measurements
from .simulate_schedule import ScheduleProblem, simulate_schedule
from .verify_schedule import verify_schedule


def do_expedition(expedition_dir: str | Path, input_data: Path | None = None) -> None:
    """
    Perform an expedition, providing terminal feedback and file output.

    :param expedition_dir: The base directory for the expedition.
    :param input_data: Input data folder folder (override used for testing).
    """
    if isinstance(expedition_dir, str):
        expedition_dir = Path(expedition_dir)

    ship_config = _get_ship_config(expedition_dir)
    schedule = _get_schedule(expedition_dir)

    # remove instrument configurations that are not in schedule
    instruments_in_schedule = get_instruments_in_schedule(schedule)

    for instrument in [
        "ARGO_FLOAT",
        "DRIFTER",
        "XBT",
        "CTD",
    ]:  # TODO make instrument names consistent capitals or lowercase throughout codebase
        if (
            hasattr(ship_config, instrument.lower() + "_config")
            and instrument not in instruments_in_schedule
        ):
            print(f"{instrument} configuration provided but not in schedule.")
            setattr(ship_config, instrument.lower() + "_config", None)

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
        expedition_dir=expedition_dir,
        schedule=schedule,
        ship_config=ship_config,
        input_data=input_data,
    )

    # verify schedule makes sense
    verify_schedule(projection, ship_config, schedule, input_data)

    # simulate the schedule
    schedule_results = simulate_schedule(
        projection=projection, ship_config=ship_config, schedule=schedule
    )
    if isinstance(schedule_results, ScheduleProblem):
        print(
            "Update your schedule and continue the expedition by running the tool again."
        )
        _save_checkpoint(
            Checkpoint(
                past_schedule=Schedule(
                    waypoints=schedule.waypoints[: schedule_results.failed_waypoint_i]
                )
            ),
            expedition_dir,
        )
        return

    # delete and create results directory
    if os.path.exists(expedition_dir.joinpath("results")):
        shutil.rmtree(expedition_dir.joinpath("results"))
    os.makedirs(expedition_dir.joinpath("results"))

    # calculate expedition cost in US$
    assert schedule.waypoints[0].time is not None, (
        "First waypoint has no time. This should not be possible as it should have been verified before."
    )
    time_past = schedule_results.time - schedule.waypoints[0].time
    cost = expedition_cost(schedule_results, time_past)
    with open(expedition_dir.joinpath("results", "cost.txt"), "w") as file:
        file.writelines(f"cost: {cost} US$")
    print(f"This expedition took {time_past} and would have cost {cost:,.0f} US$.")

    # simulate measurements
    print("Simulating measurements. This may take a while..")
    simulate_measurements(
        expedition_dir,
        ship_config,
        input_data,
        schedule_results.measurements_to_simulate,
    )
    print("Done simulating measurements.")

    print("Your expedition has concluded successfully!")
    print("Your measurements can be found in the results directory.")


def _load_input_data(
    expedition_dir: Path,
    schedule: Schedule,
    ship_config: ShipConfig,
    input_data: Path | None,
) -> InputData:
    """
    Load the input data.

    :param expedition_dir: Directory of the expedition.
    :type expedition_dir: Path
    :param schedule: Schedule object.
    :type schedule: Schedule
    :param ship_config: Ship configuration.
    :type ship_config: ShipConfig
    :param input_data: Folder containing input data.
    :type input_data: Path | None
    :return: InputData object.
    :rtype: InputData
    """
    if input_data is None:
        space_time_region_hash = get_space_time_region_hash(schedule.space_time_region)
        input_data = get_existing_download(expedition_dir, space_time_region_hash)

    return InputData.load(
        directory=input_data,
        load_adcp=ship_config.adcp_config is not None,
        load_argo_float=ship_config.argo_float_config is not None,
        load_ctd=ship_config.ctd_config is not None,
        load_drifter=ship_config.drifter_config is not None,
        load_xbt=ship_config.xbt_config is not None,
        load_ship_underwater_st=ship_config.ship_underwater_st_config is not None,
    )


def _load_checkpoint(expedition_dir: Path) -> Checkpoint | None:
    file_path = expedition_dir.joinpath(CHECKPOINT)
    try:
        return Checkpoint.from_yaml(file_path)
    except FileNotFoundError:
        return None


def _save_checkpoint(checkpoint: Checkpoint, expedition_dir: Path) -> None:
    file_path = expedition_dir.joinpath(CHECKPOINT)
    checkpoint.to_yaml(file_path)
