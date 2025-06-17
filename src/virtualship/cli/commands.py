import webbrowser
from pathlib import Path

import click
from textual_serve.server import Server

from virtualship import utils
from virtualship.cli._fetch import _fetch
from virtualship.expedition.do_expedition import do_expedition
from virtualship.utils import (
    SCHEDULE,
    SHIP_CONFIG,
    mfp_to_yaml,
)


@click.command()
@click.argument(
    "path",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
)
@click.option(
    "--from-mfp",
    type=str,
    default=None,
    help="Partially initialise a project from an exported xlsx or csv file from NIOZ' "
    'Marine Facilities Planning tool (specifically the "Export Coordinates > DD" option). '
    "User edits are required after initialisation.",
)
def init(path, from_mfp):
    """
    Initialize a directory for a new expedition, with an example schedule and ship config files.

    If --mfp-file is provided, it will generate the schedule from the MPF file instead.
    """
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
    if from_mfp:
        mfp_file = Path(from_mfp)
        # Generate schedule.yaml from the MPF file
        click.echo(f"Generating schedule from {mfp_file}...")
        mfp_to_yaml(mfp_file, schedule)
        click.echo(
            "\n⚠️  The generated schedule does not contain time values. "
            "\nPlease either use the 'virtualship plan` app to complete the schedule configuration, "
            "\nOR edit 'schedule.yaml' and manually add the necessary time values."
            "\n🕒  Expected time format: 'YYYY-MM-DD HH:MM:SS' (e.g., '2023-10-20 01:00:00').\n"
        )
    else:
        # Create a default example schedule
        # schedule_body = utils.get_example_schedule()
        schedule.write_text(utils.get_example_schedule())

    click.echo(f"Created '{config.name}' and '{schedule.name}' at {path}.")


@click.command()
@click.argument(
    "path",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
)
def plan(path):
    """Launch UI to help build schedule and ship config files. Opens in web browser, hosted on the user's local machine only."""
    server = Server(
        command=f"python -m virtualship.cli._plan {Path(path)}",
        title="VirtualShip plan",
    )
    url = "http://localhost:8000"
    webbrowser.open(url)
    server.serve()


@click.command()
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
)
@click.option(
    "--username",
    type=str,
    default=None,
    help="Copernicus Marine username.",
)
@click.option(
    "--password",
    type=str,
    default=None,
    help="Copernicus Marine password.",
)
def fetch(path: str | Path, username: str | None, password: str | None) -> None:
    """
    Download input data for an expedition.

    Entrypoint for the tool to download data based on space-time region provided in the
    schedule file. Data is downloaded from Copernicus Marine, credentials for which can be
    obtained via registration: https://data.marine.copernicus.eu/register . Credentials can
    be provided on prompt, via command line arguments, or via a YAML config file. Run
    `virtualship fetch` on a expedition for more info.
    """
    _fetch(path, username, password)


@click.command()
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
)
def run(path):
    """Run the expedition."""
    do_expedition(Path(path))
