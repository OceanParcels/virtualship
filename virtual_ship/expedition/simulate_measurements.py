"""simulate_measurements function."""

from datetime import timedelta
from pathlib import Path

from ..instruments.adcp import simulate_adcp
from ..instruments.argo_float import simulate_argo_floats
from ..instruments.ctd import simulate_ctd
from ..instruments.drifter import simulate_drifters
from ..instruments.ship_underwater_st import simulate_ship_underwater_st
from .input_data import InputData
from .ship_config import ShipConfig
from .simulate_schedule import MeasurementsToSimulate


def simulate_measurements(
    expedition_dir: str | Path,
    ship_config: ShipConfig,
    input_data: InputData,
    measurements: MeasurementsToSimulate,
) -> None:
    """
    Simulate measurements using parcels.

    Saves everything the $expedition_dir/results.

    :param expedition_dir: Base directory of the expedition.
    :param ship_config: Ship configuration.
    :param input_data: Input data for simulation.
    :param measurements: The measurements to simulate.
    :raises RuntimeError: In case fieldsets of configuration is not provided. Make sure to check this before calling this function.
    """
    if isinstance(expedition_dir, str):
        expedition_dir = Path(expedition_dir)

    if len(measurements.ship_underwater_sts) > 0:
        print("Simulating onboard salinity and temperature measurements.")
        if input_data.ship_underwater_st_fieldset is None:
            raise RuntimeError("No fieldset for ship underwater ST provided.")
        if ship_config.ship_underwater_st_config is None:
            raise RuntimeError("No configuration for ship underwater ST provided.")
        simulate_ship_underwater_st(
            fieldset=input_data.ship_underwater_st_fieldset,
            out_path=expedition_dir.joinpath("results", "ship_underwater_st.zarr"),
            depth=-2,
            sample_points=measurements.ship_underwater_sts,
        )

    if len(measurements.adcps) > 0:
        print("Simulating onboard ADCP.")
        if input_data.adcp_fieldset is None:
            raise RuntimeError("No fieldset for ADCP provided.")
        if ship_config.adcp_config is None:
            raise RuntimeError("No configuration for ADCP provided.")
        simulate_adcp(
            fieldset=input_data.adcp_fieldset,
            out_path=expedition_dir.joinpath("results", "adcp.zarr"),
            max_depth=ship_config.adcp_config.max_depth,
            min_depth=-5,
            num_bins=ship_config.adcp_config.num_bins,
            sample_points=measurements.adcps,
        )

    if len(measurements.ctds) > 0:
        print("Simulating CTD casts.")
        if input_data.ctd_fieldset is None:
            raise RuntimeError("No fieldset for CTD provided.")
        if ship_config.ctd_config is None:
            raise RuntimeError("No configuration for CTD provided.")
        simulate_ctd(
            out_path=expedition_dir.joinpath("results", "ctd.zarr"),
            fieldset=input_data.ctd_fieldset,
            ctds=measurements.ctds,
            outputdt=timedelta(seconds=10),
        )

    if len(measurements.drifters) > 0:
        print("Simulating drifters")
        if input_data.drifter_fieldset is None:
            raise RuntimeError("No fieldset for drifters provided.")
        if ship_config.drifter_config is None:
            raise RuntimeError("No configuration for drifters provided.")
        simulate_drifters(
            out_path=expedition_dir.joinpath("results", "drifters.zarr"),
            fieldset=input_data.drifter_fieldset,
            drifters=measurements.drifters,
            outputdt=timedelta(hours=5),
            dt=timedelta(minutes=5),
            endtime=None,
        )

    if len(measurements.argo_floats) > 0:
        print("Simulating argo floats")
        if input_data.argo_float_fieldset is None:
            raise RuntimeError("No fieldset for argo floats provided.")
        if ship_config.argo_float_config is None:
            raise RuntimeError("No configuration for argo floats provided.")
        simulate_argo_floats(
            out_path=expedition_dir.joinpath("results", "argo_floats.zarr"),
            argo_floats=measurements.argo_floats,
            fieldset=input_data.argo_float_fieldset,
            outputdt=timedelta(minutes=5),
            endtime=None,
        )
