from enum import Enum, auto


class InstrumentType(Enum):
    CTD = auto()
    DRIFTER = auto()
    ARGO_FLOAT = auto()
