from pathlib import Path

import click
import copernicusmarine

import virtualship.cli._creds as creds
from virtualship import utils
from virtualship.cli._fetch import (
    DOWNLOAD_METADATA,
    DownloadMetadata,
    complete_download,
    get_existing_download,
    hash_model,
    hash_to_filename,
)
from virtualship.expedition.do_expedition import _get_schedule, do_expedition
from virtualship.utils import SCHEDULE, SHIP_CONFIG


@click.command(
    help="Initialize a directory for a new expedition, with an example configuration."
)
@click.argument(
    "path",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
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
@click.option(
    "--username",
    type=str,
    default=None,
)
@click.option(
    "--password",
    type=str,
    default=None,
)
def fetch(path: str | Path, username: str | None, password: str | None) -> None:
    """Entrypoint for the tool to download data based on area of interest."""
    if sum([username is None, password is None]) == 1:
        raise ValueError("Both username and password must be provided when using CLI.")

    path = Path(path)

    data_folder = path / "data"
    data_folder.mkdir(exist_ok=True)

    schedule = _get_schedule(path)

    aoi_hash = hash_model(schedule.area_of_interest)

    existing_download = get_existing_download(data_folder, aoi_hash)
    if existing_download is not None:
        click.echo(
            f"Data download based on area of interest already completed at {existing_download}."
        )
        return

    creds_path = path / creds.CREDENTIALS_FILE
    username, password = creds.get_credentials_flow(username, password, creds_path)

    # Extract area_of_interest details from the schedule
    spatial_range = schedule.area_of_interest.spatial_range
    time_range = schedule.area_of_interest.time_range
    start_datetime = time_range.start_time
    end_datetime = time_range.end_time

    # Create download folder and set download metadata
    download_folder = data_folder / hash_to_filename(aoi_hash)
    download_folder.mkdir()
    DownloadMetadata(download_complete=False).to_yaml(
        download_folder / DOWNLOAD_METADATA
    )

    # Define all datasets to download, including bathymetry
    download_dict = {
        "Bathymetry": {
            "dataset_id": "cmems_mod_glo_phy_my_0.083deg_static",
            "variables": ["deptho"],
            "output_filename": str(download_folder / "bathymetry.nc"),
            "force_dataset_part": "bathy",
        },
        "UVdata": {
            "dataset_id": "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i",
            "variables": ["uo", "vo"],
            "output_filename": str(download_folder / "default_uv.nc"),
        },
        "Sdata": {
            "dataset_id": "cmems_mod_glo_phy-so_anfc_0.083deg_PT6H-i",
            "variables": ["so"],
            "output_filename": str(download_folder / "default_s.nc"),
        },
        "Tdata": {
            "dataset_id": "cmems_mod_glo_phy-thetao_anfc_0.083deg_PT6H-i",
            "variables": ["thetao"],
            "output_filename": str(download_folder / "default_t.nc"),
        },
    }

    # Iterate over all datasets and download each based on area_of_interest
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
            output_directory=path.joinpath(f"data/{aoi_hash}/"),
            username=username,
            password=password,
            force_download=True,
            overwrite_output_data=True,
            force_dataset_part=dataset.get(
                "force_dataset_part"
            ),  # Only used if specified in dataset
        )

    complete_download()
    click.echo("Data download based on area of interest completed.")


@click.command(help="Do the expedition.")
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
)
@click.option(
    "--username",
    prompt=True,
    type=str,
)
def run(path):
    """Entrypoint for the tool."""
    do_expedition(Path(path))
