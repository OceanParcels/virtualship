# from datetime import datetime
from .schedule import Schedule
from pathlib import Path

import pyproj
from .ship_config import ShipConfig
from .checkpoint import Checkpoint
from datetime import datetime
from .simulate_schedule import simulate_schedule


def loop(expedition_dir: str | Path) -> None:
    if isinstance(expedition_dir, str):
        expedition_dir = Path(expedition_dir)

    ship_config = _get_ship_config(expedition_dir)
    if ship_config is None:
        return

    schedule = _get_schedule(expedition_dir)
    if schedule is None:
        return

    checkpoint = _load_checkpoint(expedition_dir)
    if checkpoint is None:
        checkpoint = Checkpoint()

    # projection used to sail between waypoints
    projection = pyproj.Geod(ellps="WGS84")

    # simulate the schedule from the checkpoint
    simulate_schedule(projection=projection, ship_config=ship_config)
    # TODO this should return whether the complete schedule is done
    # or the part of the schedule that's done
    # store as checkpoint
    # ask user to update schedule
    # reload and check if matching checkpoint
    # then simulate whole schedule again (it's fast anyway)

    # finally, simulate measurements


def _get_ship_config(expedition_dir: Path) -> ShipConfig | None:
    file_path = expedition_dir.joinpath("ship_config.yaml")
    try:
        return ShipConfig.from_yaml(file_path)
    except FileNotFoundError:
        print(f'Schedule not found. Save it to "{file_path}".')
        return None


def _get_schedule(expedition_dir: Path) -> Schedule | None:
    file_path = expedition_dir.joinpath("schedule.yaml")
    try:
        return Schedule.from_yaml(file_path)
    except FileNotFoundError:
        print(f'Schedule not found. Save it to "{file_path}".')
        return None


def _load_checkpoint(expedition_dir: Path) -> Schedule | None:
    file_path = expedition_dir.joinpath("checkpoint.yaml")
    try:
        return Checkpoint.from_yaml(file_path)
    except FileNotFoundError:
        return None
