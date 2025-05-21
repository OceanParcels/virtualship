import logging

# get Parcels logger
external_logger = logging.getLogger("parcels.tools.loggers")


# filter class
class Filter(logging.Filter):
    """Logging filter for all (Parcels) logging messages."""

    def filter(self, record):
        return False
