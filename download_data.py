# run file from commandline with echo -e "\n\n\n\n\n\n\n\n" | python download_data.py

import os
import json
import copernicusmarine
import datetime
# from virtualship import VirtualShipConfiguration

class VirtualShipConfiguration:
    def __init__(self, json_file):
        with open(os.path.join(os.path.dirname(__file__), json_file), 'r') as file:
            json_input = json.loads(file.read())
            for key in json_input:
                setattr(self, key, json_input[key])

if __name__ == '__main__':
    config = VirtualShipConfiguration('student_input.json')

    download_dict = {
        'UVdata': {'dataset_id': 'cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i', 'variables': ['uo', 'vo'], 'output_filename': "studentdata_UV.nc",},
        'Sdata': {'dataset_id': 'cmems_mod_glo_phy-so_anfc_0.083deg_PT6H-i', 'variables': ['so'], 'output_filename': "studentdata_S.nc"},
        'Tdata': {'dataset_id': 'cmems_mod_glo_phy-thetao_anfc_0.083deg_PT6H-i', 'variables': ['thetao'], 'output_filename': "studentdata_T.nc"}
    }

    for dataset in download_dict:
        copernicusmarine.subset(
            dataset_id=download_dict[dataset]['dataset_id'],
            variables=download_dict[dataset]['variables'],
            minimum_longitude=config.region_of_interest["West"],
            maximum_longitude=config.region_of_interest["East"],
            minimum_latitude=config.region_of_interest["South"],
            maximum_latitude=config.region_of_interest["North"],
            start_datetime=config.requested_ship_time["start"],
            end_datetime=config.requested_ship_time["end"],
            minimum_depth=0.49402499198913574,
            maximum_depth=5727.9169921875,
            output_filename=download_dict[dataset]['output_filename']
        )


    if len(config.drifter_deploylocations) > 0:

        download_dict = {
            'UVdata': {'dataset_id': 'cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i', 'variables': ['uo', 'vo'], 'output_filename': "drifterdata_UV.nc",},
            'Tdata': {'dataset_id': 'cmems_mod_glo_phy-thetao_anfc_0.083deg_PT6H-i', 'variables': ['thetao'], 'output_filename': "drifterdata_T.nc"}
        }    

        for dataset in download_dict:
            copernicusmarine.subset(
                dataset_id=download_dict[dataset]['dataset_id'],
                variables=download_dict[dataset]['variables'],
                minimum_longitude=config.region_of_interest["West"]-5,
                maximum_longitude=config.region_of_interest["East"]+5,
                minimum_latitude=config.region_of_interest["South"]-5,
                maximum_latitude=config.region_of_interest["North"]+5,
                start_datetime=config.requested_ship_time["start"],
                end_datetime=f'{datetime.datetime.strptime(config.requested_ship_time["end"],"%Y-%m-%dT%H:%M:%S")+datetime.timedelta(days=21):%Y-%m-%dT%H:%M:%S}',
                minimum_depth=0.49402499198913574,
                maximum_depth=0.49402499198913574,
                output_filename=download_dict[dataset]['output_filename']
            )

    if len(config.argo_deploylocations) > 0:
        download_dict = {
            'UVdata': {'dataset_id': 'cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i', 'variables': ['uo', 'vo'], 'output_filename': "argodata_UV.nc",},
            'Sdata' : {'dataset_id': 'cmems_mod_glo_phy-so_anfc_0.083deg_PT6H-i', 'variables': ['so'], 'output_filename': "argodata_S.nc"},
            'Tdata': {'dataset_id': 'cmems_mod_glo_phy-thetao_anfc_0.083deg_PT6H-i', 'variables': ['thetao'], 'output_filename': "argodata_T.nc"}
        }    

        for dataset in download_dict:
            copernicusmarine.subset(
                dataset_id=download_dict[dataset]['dataset_id'],
                variables=download_dict[dataset]['variables'],
                minimum_longitude=config.region_of_interest["West"]-5,
                maximum_longitude=config.region_of_interest["East"]+5,
                minimum_latitude=config.region_of_interest["South"]-5,
                maximum_latitude=config.region_of_interest["North"]+5,
                start_datetime=config.requested_ship_time["start"],
                end_datetime=f'{datetime.datetime.strptime(config.requested_ship_time["end"],"%Y-%m-%dT%H:%M:%S")+datetime.timedelta(days=21):%Y-%m-%dT%H:%M:%S}',
                minimum_depth=0.49402499198913574,
                maximum_depth=5727.9169921875,
                output_filename=download_dict[dataset]['output_filename']
            )
