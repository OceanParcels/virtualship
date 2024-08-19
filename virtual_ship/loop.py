from datetime import datetime
from .schedule import Schedule
from pathlib import Path


def loop(expedition_dir: str | Path) -> None:
    if isinstance(expedition_dir, str):
        expedition_dir = Path(expedition_dir)
    schedule_dir = expedition_dir.joinpath("schedules")

    start_schedule = None
    while start_schedule is None:
        start_schedule = get_schedule(schedule_dir=schedule_dir, datetime=None)
        if start_schedule is None:
            print_and_wait_for_user(
                f"No schedule found. Save it to \"{schedule_dir.joinpath('start.yaml')}\""
            )


def print_and_wait_for_user(message: str) -> None:
    print(message)
    input()


def get_schedule(schedule_dir: Path, datetime: datetime | None) -> Schedule | None:
    if datetime is not None:
        raise NotImplementedError()

    try:
        return Schedule.from_yaml(schedule_dir.joinpath("start.yaml"))
    except FileNotFoundError:
        return None
