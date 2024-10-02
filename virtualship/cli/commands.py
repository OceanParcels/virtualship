from pathlib import Path

import click

from virtualship.expedition.do_expedition import do_expedition


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
    raise NotImplementedError("Not implemented yet.")


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
