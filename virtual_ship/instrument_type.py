"""InstrumentType Enum."""

from enum import Enum, auto


class InstrumentType(Enum):
    """Types of instruments."""

    CTD = auto()
    DRIFTER = auto()
    ARGO_FLOAT = auto()
