"""InputData class."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from parcels import Field, FieldSet


@dataclass
class InputData:
    """A collection of fieldsets that function as input data for simulation."""

    adcp_fieldset: FieldSet | None
    argo_float_fieldset: FieldSet | None
    ctd_fieldset: FieldSet | None
    drifter_fieldset: FieldSet | None
    ship_underwater_st_fieldset: FieldSet | None

    @classmethod
    def load(
        cls,
        directory: str | Path,
        load_adcp: bool,
        load_argo_float: bool,
        load_ctd: bool,
        load_drifter: bool,
        load_ship_underwater_st: bool,
    ) -> InputData:
        """
        Create an instance of this class from netCDF files.

        For now this function makes a lot of assumption about file location and contents.

        :param directory: Base directory of the expedition.
        :param load_adcp: Whether to load the ADCP fieldset.
        :param load_argo_float: Whether to load the argo float fieldset.
        :param load_ctd: Whether to load the CTD fieldset.
        :param load_drifter: Whether to load the drifter fieldset.
        :param load_ship_underwater_st: Whether to load the ship underwater ST fieldset.
        :returns: An instance of this class with loaded fieldsets.
        """
        if load_drifter:
            drifter_fieldset = cls._load_drifter_fieldset(directory)
        else:
            drifter_fieldset = None
        if load_argo_float:
            argo_float_fieldset = cls._load_argo_float_fieldset(directory)
        else:
            argo_float_fieldset = None
        if load_adcp or load_ctd or load_ship_underwater_st:
            default_fieldset = cls._load_default_fieldset(directory)
        if load_adcp:
            adcp_fieldset = default_fieldset
        else:
            adcp_fieldset = None
        if load_ctd:
            ctd_fieldset = default_fieldset
        else:
            ctd_fieldset = None
        if load_ship_underwater_st:
            ship_underwater_st_fieldset = default_fieldset
        else:
            ship_underwater_st_fieldset = None

        return InputData(
            adcp_fieldset=adcp_fieldset,
            argo_float_fieldset=argo_float_fieldset,
            ctd_fieldset=ctd_fieldset,
            drifter_fieldset=drifter_fieldset,
            ship_underwater_st_fieldset=ship_underwater_st_fieldset,
        )

    @classmethod
    def _load_default_fieldset(cls, directory: str | Path) -> FieldSet:
        filenames = {
            "U": directory.joinpath("default_uv.nc"),
            "V": directory.joinpath("default_uv.nc"),
            "S": directory.joinpath("default_s.nc"),
            "T": directory.joinpath("default_t.nc"),
        }
        variables = {"U": "uo", "V": "vo", "S": "so", "T": "thetao"}
        dimensions = {
            "lon": "longitude",
            "lat": "latitude",
            "time": "time",
            "depth": "depth",
        }

        # create the fieldset and set interpolation methods
        fieldset = FieldSet.from_netcdf(
            filenames, variables, dimensions, allow_time_extrapolation=True
        )
        fieldset.T.interp_method = "linear_invdist_land_tracer"
        fieldset.S.interp_method = "linear_invdist_land_tracer"

        # make depth negative
        for g in fieldset.gridset.grids:
            g._depth = -g._depth  # TODO maybe add a grid.negate_depth() method in Parcels?

        # add bathymetry data
        bathymetry_file = directory.joinpath("bathymetry.nc")
        bathymetry_variables = ("bathymetry", "deptho")
        bathymetry_dimensions = {"lon": "longitude", "lat": "latitude"}
        bathymetry_field = Field.from_netcdf(
            bathymetry_file, bathymetry_variables, bathymetry_dimensions
        )
        # make depth negative
        bathymetry_field.data = -bathymetry_field.data
        fieldset.add_field(bathymetry_field)

        # read in data already
        fieldset.computeTimeChunk(0, 1)

        return fieldset

    @classmethod
    def _load_drifter_fieldset(cls, directory: str | Path) -> FieldSet:
        filenames = {
            "U": directory.joinpath("drifter_uv.nc"),
            "V": directory.joinpath("drifter_uv.nc"),
            "T": directory.joinpath("drifter_t.nc"),
        }
        variables = {"U": "uo", "V": "vo", "T": "thetao"}
        dimensions = {
            "lon": "longitude",
            "lat": "latitude",
            "time": "time",
            "depth": "depth",
        }

        fieldset = FieldSet.from_netcdf(
            filenames, variables, dimensions, allow_time_extrapolation=False
        )
        fieldset.T.interp_method = "linear_invdist_land_tracer"

        # make depth negative
        for g in fieldset.gridset.grids:
            g._depth = -g._depth

        # read in data already
        fieldset.computeTimeChunk(0, 1)

        return fieldset

    @classmethod
    def _load_argo_float_fieldset(cls, directory: str | Path) -> FieldSet:
        filenames = {
            "U": directory.joinpath("argo_float_uv.nc"),
            "V": directory.joinpath("argo_float_uv.nc"),
            "S": directory.joinpath("argo_float_s.nc"),
            "T": directory.joinpath("argo_float_t.nc"),
        }
        variables = {"U": "uo", "V": "vo", "S": "so", "T": "thetao"}
        dimensions = {
            "lon": "longitude",
            "lat": "latitude",
            "time": "time",
            "depth": "depth",
        }

        fieldset = FieldSet.from_netcdf(
            filenames, variables, dimensions, allow_time_extrapolation=False
        )
        fieldset.T.interp_method = "linear_invdist_land_tracer"
        fieldset.S.interp_method = "linear_invdist_land_tracer"

        # make depth negative
        for g in fieldset.gridset.grids:
            if max(g.depth) > 0:
                g._depth = -g._depth

        # read in data already
        fieldset.computeTimeChunk(0, 1)

        return fieldset
