"""Conversion functions from zarr instrument results to realistic file formats with data adjusted to be more realistic."""

from .ctd_make_realistic import ctd_make_realistic
from .adcp_make_realistic import adcp_make_realistic

__all__ = ["ctd_make_realistic", "adcp_make_realistic"]
