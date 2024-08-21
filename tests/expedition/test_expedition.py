from virtual_ship import (
    ShipConfig,
    ArgoFloatConfig,
    ADCPConfig,
    CTDConfig,
    DrifterConfig,
    ShipUnderwaterSTConfig,
)
from datetime import timedelta


def test_expedition() -> None:
    argo_float_config = ArgoFloatConfig(
        min_depth=0,
        max_depth=-2000,
        drift_depth=-1000,
        vertical_speed=-0.10,
        cycle_days=10,
        drift_days=9,
    )

    adcp_config = ADCPConfig(
        max_depth=-1000,
        bin_size_m=24,
        period=timedelta(minutes=5),
    )

    ship_underwater_st_config = ShipUnderwaterSTConfig(
        period=timedelta(minutes=5),
    )

    ctd_config = CTDConfig(
        stationkeeping_time=timedelta(minutes=20),
        min_depth=0,
        max_depth=2000,
    )

    drifter_config = DrifterConfig(
        depth=0,
        lifetime=timedelta(weeks=4),
    )

    ShipConfig(
        ship_speed=5.14,
        argo_float_config=argo_float_config,
        adcp_config=adcp_config,
        ctd_config=ctd_config,
        ship_underwater_st_config=ship_underwater_st_config,
        drifter_config=drifter_config,
    ).save_to_yaml("test.yaml")
    ShipConfig.load_from_yaml("test.yaml")
    # with open("ship_config.yaml", "r") as file:
    #     data = yaml.load(file)
    #     x = ShipConfig()
    #     x = ShipConfig(ship_speed=3.0)
