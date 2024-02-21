import os
import json
# import copernicusmarine as cm


class VirtualShipConfiguration:
    def __init__(self, json_file):
        with open(os.path.join(os.path.dirname(__file__), json_file), 'r') as file:
            json_input = json.loads(file.read())
            for key in json_input:
                setattr(self, key, json_input[key])



def create_json(config):

    data_dict = {
    "dataset_id": "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i",
    "variables": ["uo", "vo"],
    "minimum_longitude": config.region_of_interest["West"],
    "maximum_longitude": config.region_of_interest["East"],
    "minimum_latitude": config.region_of_interest["South"],
    "maximum_latitude": config.region_of_interest["North"],
    "start_datetime": config.requested_ship_time["start"],
    "end_datetime": config.requested_ship_time["end"],
    "minimum_depth": 0.49402499198913574,
    "maximum_depth": 5727.9169921875,
    "output_filename":  "CMEMS_Indian_currents_Jan2022.nc",
    "output_directory":  "group_A"
    }

    with open("sample.json", "w") as outfile:
        json.dump(data_dict, outfile)




if __name__ == '__main__':
    config = VirtualShipConfiguration('student_input.json')
    create_json(config)
    copernicusmarine.subset(request_file = "sample.json")