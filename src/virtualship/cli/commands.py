import shutil
from datetime import timedelta
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
from virtualship.expedition.do_expedition import do_expedition
from virtualship.utils import (
    SCHEDULE,
    SHIP_CONFIG,
    _get_schedule,
    _get_ship_config,
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
    help='Partially initialise a project from an exported xlsx or csv file from NIOZ\' Marine Facilities Planning tool (specifically the "Export Coordinates > DD" option). User edits are required after initialisation.',
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
            "\nPlease edit 'schedule.yaml' and manually add the necessary time values."
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
    ship_config = _get_ship_config(path)

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
    instruments_in_schedule = schedule.get_instruments()

    # Create download folder and set download metadata
    download_folder = data_folder / hash_to_filename(space_time_region_hash)
    download_folder.mkdir()
    DownloadMetadata(download_complete=False).to_yaml(
        download_folder / DOWNLOAD_METADATA
    )
    shutil.copyfile(path / SCHEDULE, download_folder / SCHEDULE)

    if (
        (set(["XBT", "CTD", "SHIP_UNDERWATER_ST"]) & set(instruments_in_schedule))
        or hasattr(ship_config, "ship_underwater_st_config")
        or hasattr(ship_config, "adcp_config")
    ):
        print("Ship data will be downloaded")

        # Define all ship datasets to download, including bathymetry
        download_dict = {
            "Bathymetry": {
                "dataset_id": "cmems_mod_glo_phy_my_0.083deg_static",
                "variables": ["deptho"],
                "output_filename": "bathymetry.nc",
            },
            "UVdata": {
                "dataset_id": "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i",
                "variables": ["uo", "vo"],
                "output_filename": "ship_uv.nc",
            },
            "Sdata": {
                "dataset_id": "cmems_mod_glo_phy-so_anfc_0.083deg_PT6H-i",
                "variables": ["so"],
                "output_filename": "ship_s.nc",
            },
            "Tdata": {
                "dataset_id": "cmems_mod_glo_phy-thetao_anfc_0.083deg_PT6H-i",
                "variables": ["thetao"],
                "output_filename": "ship_t.nc",
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
                    overwrite=True,
                    coordinates_selection_method="outside",
                )
        except InvalidUsernameOrPassword as e:
            shutil.rmtree(download_folder)
            raise e

        complete_download(download_folder)
        click.echo("Ship data download based on space-time region completed.")

    if "DRIFTER" in instruments_in_schedule:
        print("Drifter data will be downloaded")
        drifter_download_dict = {
            "UVdata": {
                "dataset_id": "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i",
                "variables": ["uo", "vo"],
                "output_filename": "drifter_uv.nc",
            },
            "Tdata": {
                "dataset_id": "cmems_mod_glo_phy-thetao_anfc_0.083deg_PT6H-i",
                "variables": ["thetao"],
                "output_filename": "drifter_t.nc",
            },
        }

        # Iterate over all datasets and download each based on space_time_region
        try:
            for dataset in drifter_download_dict.values():
                copernicusmarine.subset(
                    dataset_id=dataset["dataset_id"],
                    variables=dataset["variables"],
                    minimum_longitude=spatial_range.minimum_longitude - 3.0,
                    maximum_longitude=spatial_range.maximum_longitude + 3.0,
                    minimum_latitude=spatial_range.minimum_latitude - 3.0,
                    maximum_latitude=spatial_range.maximum_latitude + 3.0,
                    start_datetime=start_datetime,
                    end_datetime=end_datetime + timedelta(days=21),
                    minimum_depth=abs(1),
                    maximum_depth=abs(1),
                    output_filename=dataset["output_filename"],
                    output_directory=download_folder,
                    username=username,
                    password=password,
                    overwrite=True,
                    coordinates_selection_method="outside",
                )
        except InvalidUsernameOrPassword as e:
            shutil.rmtree(download_folder)
            raise e

        complete_download(download_folder)
        click.echo("Drifter data download based on space-time region completed.")

    if "ARGO_FLOAT" in instruments_in_schedule:
        print("Argo float data will be downloaded")
        argo_download_dict = {
            "UVdata": {
                "dataset_id": "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i",
                "variables": ["uo", "vo"],
                "output_filename": "argo_float_uv.nc",
            },
            "Sdata": {
                "dataset_id": "cmems_mod_glo_phy-so_anfc_0.083deg_PT6H-i",
                "variables": ["so"],
                "output_filename": "argo_float_s.nc",
            },
            "Tdata": {
                "dataset_id": "cmems_mod_glo_phy-thetao_anfc_0.083deg_PT6H-i",
                "variables": ["thetao"],
                "output_filename": "argo_float_t.nc",
            },
        }

        # Iterate over all datasets and download each based on space_time_region
        try:
            for dataset in argo_download_dict.values():
                copernicusmarine.subset(
                    dataset_id=dataset["dataset_id"],
                    variables=dataset["variables"],
                    minimum_longitude=spatial_range.minimum_longitude - 3.0,
                    maximum_longitude=spatial_range.maximum_longitude + 3.0,
                    minimum_latitude=spatial_range.minimum_latitude - 3.0,
                    maximum_latitude=spatial_range.maximum_latitude + 3.0,
                    start_datetime=start_datetime,
                    end_datetime=end_datetime + timedelta(days=21),
                    minimum_depth=abs(1),
                    maximum_depth=abs(spatial_range.maximum_depth),
                    output_filename=dataset["output_filename"],
                    output_directory=download_folder,
                    username=username,
                    password=password,
                    overwrite=True,
                    coordinates_selection_method="outside",
                )
        except InvalidUsernameOrPassword as e:
            shutil.rmtree(download_folder)
            raise e

        complete_download(download_folder)
        click.echo("Argo_float data download based on space-time region completed.")


@click.command()
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
)
def run(path):
    """Run the expedition."""
    do_expedition(Path(path))
