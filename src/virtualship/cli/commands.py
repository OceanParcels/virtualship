from pathlib import Path

import click

from virtualship import utils
from virtualship.expedition.do_expedition import do_expedition
from virtualship.utils import SCHEDULE, SHIP_CONFIG


@click.command(
    help="Initialize a directory for a new expedition, with an example configuration."
)
@click.argument(
    "path",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
    # help="Expedition directory",
)
def init(path):
    """Entrypoint for the tool."""
    path = Path(path)
    path.mkdir(exist_ok=True)

    config = path / SHIP_CONFIG
    schedule = path / SCHEDULE

    if config.exists():
        raise FileExistsError(
            f"File '{config}' already exist. Please remove it or choose another directory."
        )

    if schedule.exists():
        raise FileExistsError(
            f"File '{schedule}' already exist. Please remove it or choose another directory."
        )

    config.write_text(utils.get_example_config())
    schedule.write_text(utils.get_example_schedule())

    click.echo(f"Created '{config.name}' and '{schedule.name}' at {path}.")


@click.command(
    help="Download the relevant data specified in an expedition directory (i.e., by the expedition config)."
)
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
)
def fetch(path):
    """Entrypoint for the tool."""
    raise NotImplementedError("Not implemented yet.")


@click.command(help="Do the expedition.")
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
)
def run(path):
    """Entrypoint for the tool."""
    do_expedition(Path(path))
