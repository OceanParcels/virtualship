"""VirtualShipConfiguration class."""

import datetime
import json
from datetime import timedelta

from parcels import FieldSet
from shapely.geometry import Point, Polygon


class VirtualShipConfiguration:
    """Configuration of the virtual ship, initialized from a json file."""

    adcp_fieldset: FieldSet
    ship_st_fieldset: FieldSet
    argo_float_fieldset: FieldSet
    drifter_fieldset: FieldSet
    ctd_fieldset: FieldSet
    drifter_fieldset: FieldSet
    argo_float_fieldset: FieldSet

    def __init__(
        self,
        json_file,
        adcp_fieldset: FieldSet,
        ship_st_fieldset: FieldSet,
        ctd_fieldset: FieldSet,
        drifter_fieldset: FieldSet,
        argo_float_fieldset: FieldSet,
    ):
        """
        Initialize this object.

        :param json_file: Path to the JSON file to init from.
        :param adcp_fieldset: Fieldset for ADCP measurements.
        :param ship_st_fieldset: Fieldset for ship salinity temperature measurements.
        :param ctd_fieldset: Fieldset for CTD measurements.
        :param drifter_fieldset: Fieldset for CTD measurements.
        :param argo_float_fieldset: Fieldset for argo float measurements.
        :raises ValueError: If JSON file not valid.
        """
        self.adcp_fieldset = adcp_fieldset
        self.ship_st_fieldset = ship_st_fieldset
        self.ctd_fieldset = ctd_fieldset
        self.drifter_fieldset = drifter_fieldset
        self.argo_float_fieldset = argo_float_fieldset

        with open(json_file, "r") as file:
            json_input = json.loads(file.read())
            for key in json_input:
                setattr(self, key, json_input[key])

        # Create a polygon from the region of interest to check coordinates
        north = self.region_of_interest["North"]
        east = self.region_of_interest["East"]
        south = self.region_of_interest["South"]
        west = self.region_of_interest["West"]
        poly = Polygon([(west, north), (west, south), (east, south), (east, north)])
        # validate input, raise ValueErrors if invalid
        if (
            self.region_of_interest["North"] > 90
            or self.region_of_interest["South"] < -90
            or self.region_of_interest["East"] > 180
            or self.region_of_interest["West"] < -180
        ):
            raise ValueError("Invalid coordinates in region of interest")
        if self.requested_ship_time["start"] > self.requested_ship_time["end"]:
            raise ValueError("Start time should be before end time")
        if datetime.datetime.strptime(
            self.requested_ship_time["end"], "%Y-%m-%dT%H:%M:%S"
        ) > datetime.datetime.now() + timedelta(days=2):
            raise ValueError("End time cannot be more then 2 days into the future")
        if datetime.datetime.strptime(
            self.requested_ship_time["end"], "%Y-%m-%dT%H:%M:%S"
        ) - datetime.datetime.strptime(
            self.requested_ship_time["start"], "%Y-%m-%dT%H:%M:%S"
        ) > timedelta(
            days=21
        ):
            raise ValueError("The time period is too long, maximum is 21 days")
        if len(self.route_coordinates) < 2:
            raise ValueError(
                "Route needs to consist of at least 2 longitude-latitude coordinate sets"
            )
        for coord in self.route_coordinates:
            if coord[1] > 90 or coord[1] < -90 or coord[0] > 180 or coord[0] < -180:
                raise ValueError("Invalid coordinates in route")
            # if not poly.contains(Point(coord)):
            #     raise ValueError("Route coordinates need to be within the region of interest")
        if not len(self.CTD_locations) == 0:
            for coord in self.CTD_locations:
                if coord not in self.route_coordinates:
                    raise ValueError("CTD coordinates should be on the route")
                if coord[1] > 90 or coord[1] < -90 or coord[0] > 180 or coord[0] < -180:
                    raise ValueError("Invalid coordinates in route")
                if not poly.contains(Point(coord)):
                    raise ValueError(
                        "CTD coordinates need to be within the region of interest"
                    )
        if type(self.CTD_settings["max_depth"]) is not int:
            if self.CTD_settings["max_depth"] != "max":
                raise ValueError(
                    'Specify "max" for maximum depth or a negative integer for max_depth in CTD_settings'
                )
        if type(self.CTD_settings["max_depth"]) is int:
            if self.CTD_settings["max_depth"] > 0:
                raise ValueError("Invalid depth for CTD")
        if len(self.drifter_deploylocations) > 30:
            raise ValueError("Too many drifter deployment locations, maximum is 30")
        if not len(self.drifter_deploylocations) == 0:
            for coord in self.drifter_deploylocations:
                if coord not in self.route_coordinates:
                    raise ValueError("Drifter coordinates should be on the route")
                if coord[1] > 90 or coord[1] < -90 or coord[0] > 180 or coord[0] < -180:
                    raise ValueError("Invalid coordinates in route")
                if not poly.contains(Point(coord)):
                    raise ValueError(
                        "Drifter coordinates need to be within the region of interest"
                    )
        if len(self.argo_deploylocations) > 30:
            raise ValueError("Too many argo deployment locations, maximum is 30")
        if not len(self.argo_deploylocations) == 0:
            for coord in self.argo_deploylocations:
                if coord not in self.route_coordinates:
                    raise ValueError("argo coordinates should be on the route")
                if coord[1] > 90 or coord[1] < -90 or coord[0] > 180 or coord[0] < -180:
                    raise ValueError("Invalid coordinates in route")
                if not poly.contains(Point(coord)):
                    raise ValueError(
                        "argo coordinates need to be within the region of interest"
                    )
        if not isinstance(self.underway_data, bool):
            raise ValueError("Underway data needs to be true or false")
        if not isinstance(self.ADCP_data, bool):
            raise ValueError("ADCP data needs to be true or false")
        if (
            self.ADCP_settings["bin_size_m"] < 0
            or self.ADCP_settings["bin_size_m"] > 24
        ):
            raise ValueError("Invalid bin size for ADCP")
        if self.ADCP_settings["max_depth"] > 0:
            raise ValueError("Invalid depth for ADCP")
        if (
            self.argo_characteristics["driftdepth"] > 0
            or self.argo_characteristics["driftdepth"] < -5727
        ):
            raise ValueError(
                "Specify negative depth. Max drift depth for argo is -5727 m due to data availability"
            )
        if (
            self.argo_characteristics["maxdepth"] > 0
            or self.argo_characteristics["maxdepth"] < -5727
        ):
            raise ValueError(
                "Specify negative depth. Max depth for argo is -5727 m due to data availability"
            )
        if type(self.argo_characteristics["vertical_speed"]) is not float:
            raise ValueError("Specify vertical speed for argo with decimals in m/s")
        if self.argo_characteristics["vertical_speed"] > 0:
            self.argo_characteristics["vertical_speed"] = -self.argo_characteristics[
                "vertical_speed"
            ]
        if (
            abs(self.argo_characteristics["vertical_speed"]) < 0.06
            or abs(self.argo_characteristics["vertical_speed"]) > 0.12
        ):
            raise ValueError(
                "Specify a realistic speed for argo, i.e. between -0.06 and -0.12 m/s"
            )
        if self.argo_characteristics["cycle_days"] < 0:
            raise ValueError("Specify a postitive number of cycle days for argo")
        if self.argo_characteristics["drift_days"] < 0:
            raise ValueError("Specify a postitive number of drift days for argo")
