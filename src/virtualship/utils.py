import hashlib
import json
from datetime import datetime
from functools import lru_cache
from importlib.resources import files

SCHEDULE = "schedule.yaml"
SHIP_CONFIG = "ship_config.yaml"
CHECKPOINT = "checkpoint.yaml"


def load_static_file(name: str) -> str:
    """Load static file from the ``virtualship.static`` module by file name."""
    return files("virtualship.static").joinpath(name).read_text(encoding="utf-8")


@lru_cache(None)
def get_example_config() -> str:
    """Get the example configuration file."""
    return load_static_file(SHIP_CONFIG)


@lru_cache(None)
def get_example_schedule() -> str:
    """Get the example schedule file."""
    return load_static_file(SCHEDULE)


def create_string_hash(data):
    """
    Creates a hash string from a nested dictionary or any data.
    :param data: Dictionary or other serializable object.
    :return: A string hash (e.g., SHA256).
    """

    # Custom serialization function for non-serializable types
    def custom_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()  # Convert datetime to ISO 8601 string
        raise TypeError(f"Type {type(obj)} not serializable")

    # Convert the dictionary to a sorted JSON string
    data_str = json.dumps(data, sort_keys=True, default=custom_serializer)

    # Create a hash using SHA256
    hash_obj = hashlib.sha256(data_str.encode())

    # Return the hash as a string of letters (hexadecimal)
    return hash_obj.hexdigest()
