"""InstrumentType Enum."""

from enum import Enum


class InstrumentType(Enum):
    """Types of instruments."""

    CTD = "CTD"
    CTD_BGC = "CTD_BGC"
    DRIFTER = "DRIFTER"
    ARGO_FLOAT = "ARGO_FLOAT"
    XBT = "XBT"
