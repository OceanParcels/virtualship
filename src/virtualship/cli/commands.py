import shutil
from pathlib import Path

import click
import copernicusmarine
from copernicusmarine.core_functions.credentials_utils import InvalidUsernameOrPassword

import virtualship.cli._creds as creds
from virtualship import utils
from virtualship.cli._fetch import (
    DOWNLOAD_METADATA,
    DownloadMetadata,
    complete_download,
    get_existing_download,
    get_space_time_region_hash,
    hash_to_filename,
)
from virtualship.expedition.do_expedition import _get_schedule, do_expedition
from virtualship.utils import SCHEDULE, SHIP_CONFIG


@click.command()
@click.argument(
    "path",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
)
def init(path):
    """Initialize a directory for a new expedition, with an example schedule and ship config files."""
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
    if sum([username is None, password is None]) == 1:
        raise ValueError("Both username and password must be provided when using CLI.")

    path = Path(path)

    data_folder = path / "data"
    data_folder.mkdir(exist_ok=True)

    schedule = _get_schedule(path)

    if schedule.space_time_region is None:
        raise ValueError(
            "space_time_region not found in schedule, please define it to fetch the data."
        )

    space_time_region_hash = get_space_time_region_hash(schedule.space_time_region)

    existing_download = get_existing_download(data_folder, space_time_region_hash)
    if existing_download is not None:
        click.echo(
            f"Data download for space-time region already completed ('{existing_download}')."
        )
        return

    creds_path = path / creds.CREDENTIALS_FILE
    username, password = creds.get_credentials_flow(username, password, creds_path)

    # Extract space_time_region details from the schedule
    spatial_range = schedule.space_time_region.spatial_range
    time_range = schedule.space_time_region.time_range
    start_datetime = time_range.start_time
    end_datetime = time_range.end_time

    # Create download folder and set download metadata
    download_folder = data_folder / hash_to_filename(space_time_region_hash)
    download_folder.mkdir()
    DownloadMetadata(download_complete=False).to_yaml(
        download_folder / DOWNLOAD_METADATA
    )
    shutil.copyfile(path / SCHEDULE, download_folder / SCHEDULE)

    # Define all datasets to download, including bathymetry
    download_dict = {
        "Bathymetry": {
            "dataset_id": "cmems_mod_glo_phy_my_0.083deg_static",
            "variables": ["deptho"],
            "output_filename": "bathymetry.nc",
        },
        "UVdata": {
            "dataset_id": "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i",
            "variables": ["uo", "vo"],
            "output_filename": "default_uv.nc",
        },
        "Sdata": {
            "dataset_id": "cmems_mod_glo_phy-so_anfc_0.083deg_PT6H-i",
            "variables": ["so"],
            "output_filename": "default_s.nc",
        },
        "Tdata": {
            "dataset_id": "cmems_mod_glo_phy-thetao_anfc_0.083deg_PT6H-i",
            "variables": ["thetao"],
            "output_filename": "default_t.nc",
        },
    }

    # Iterate over all datasets and download each based on space_time_region
    try:
        for dataset in download_dict.values():
            copernicusmarine.subset(
                dataset_id=dataset["dataset_id"],
                variables=dataset["variables"],
                minimum_longitude=spatial_range.minimum_longitude,
                maximum_longitude=spatial_range.maximum_longitude,
                minimum_latitude=spatial_range.minimum_latitude,
                maximum_latitude=spatial_range.maximum_latitude,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                minimum_depth=abs(spatial_range.minimum_depth),
                maximum_depth=abs(spatial_range.maximum_depth),
                output_filename=dataset["output_filename"],
                output_directory=download_folder,
                username=username,
                password=password,
                force_download=True,
                overwrite=True,
            )
    except InvalidUsernameOrPassword as e:
        shutil.rmtree(download_folder)
        raise e

    complete_download(download_folder)
    click.echo("Data download based on space-time region completed.")


@click.command()
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
)
def run(path):
    """Run the expedition."""
    do_expedition(Path(path))
