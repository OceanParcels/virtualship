import copernicusmarine
import datetime

if __name__ == "__main__":
    datadir = "data_groupF"

    download_dict = {
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

    for dataset in download_dict:
        copernicusmarine.subset(
            dataset_id=download_dict[dataset]["dataset_id"],
            variables=download_dict[dataset]["variables"],
            minimum_longitude=-1,
            maximum_longitude=1,
            minimum_latitude=-1,
            maximum_latitude=1,
            start_datetime=datetime.datetime.strptime("2023-01-01", "%Y-%m-%d"),
            end_datetime=datetime.datetime.strptime("2023-01-02", "%Y-%m-%d"),
            minimum_depth=0.49402499198913574,
            maximum_depth=5727.9169921875,
            output_filename=download_dict[dataset]["output_filename"],
            output_directory=datadir,
        )

    download_dict = {
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

    for dataset in download_dict:
        copernicusmarine.subset(
            dataset_id=download_dict[dataset]["dataset_id"],
            variables=download_dict[dataset]["variables"],
            minimum_longitude=-1,
            maximum_longitude=1,
            minimum_latitude=-1,
            maximum_latitude=1,
            start_datetime=datetime.datetime.strptime("2023-01-01", "%Y-%m-%d"),
            end_datetime=datetime.datetime.strptime("2023-01-02", "%Y-%m-%d"),
            minimum_depth=0.49402499198913574,
            maximum_depth=0.49402499198913574,
            output_filename=download_dict[dataset]["output_filename"],
            output_directory=datadir,
        )

    download_dict = {
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

    for dataset in download_dict:
        copernicusmarine.subset(
            dataset_id=download_dict[dataset]["dataset_id"],
            variables=download_dict[dataset]["variables"],
            minimum_longitude=-1,
            maximum_longitude=1,
            minimum_latitude=-1,
            maximum_latitude=1,
            start_datetime=datetime.datetime.strptime("2023-01-01", "%Y-%m-%d"),
            end_datetime=datetime.datetime.strptime("2023-01-02", "%Y-%m-%d"),
            minimum_depth=0.49402499198913574,
            maximum_depth=5727.9169921875,
            output_filename=download_dict[dataset]["output_filename"],
            output_directory=datadir,
        )
