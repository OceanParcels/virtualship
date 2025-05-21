"""Code for the Virtual Ship Classroom, where Marine Scientists can combine Copernicus Marine Data with an OceanParcels ship to go on a virtual expedition."""

from importlib.metadata import version as _version

from .models.location import Location
from .models.spacetime import Spacetime

try:
    __version__ = _version("virtualship")
except Exception:
    # Local copy or not installed with setuptools
    __version__ = "unknown"

__all__ = [
    "Location",
    "Spacetime",
    "__version__",
]
