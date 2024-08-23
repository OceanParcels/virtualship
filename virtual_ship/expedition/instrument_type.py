"""InstrumentType Enum."""

from enum import Enum, auto


class InstrumentType(Enum):
    """Types of instruments."""

    CTD = "CTD"
    DRIFTER = "DRIFTER"
    ARGO_FLOAT = "ARGO_FLOAT"
