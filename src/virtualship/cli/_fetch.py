import hashlib
from datetime import datetime

from pydantic import BaseModel


def _hash(s: str, *, length: int) -> str:
    """Create a hash of a string."""
    assert length % 2 == 0, "Length must be even."
    half_length = length // 2

    return hashlib.shake_128(s.encode("utf-8")).hexdigest(half_length)


def create_hash(s: str) -> str:
    """Create an 8 digit hash of a string."""
    return _hash(s, length=8)


def hash_model(model: BaseModel) -> str:
    """
    Hash a Pydantic model.

    :param region: The region to hash.
    :returns: The hash.
    """
    return create_hash(model.model_dump_json())


def filename_to_hash(filename: str) -> str:
    """Extract hash from filename of the format YYYYMMDD_HHMMSS_{hash}."""
    return filename.split("_")[-1]


def hash_to_filename(hash: str) -> str:
    """Return a filename of the format YYYYMMDD_HHMMSS_{hash}."""
    return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash}"
