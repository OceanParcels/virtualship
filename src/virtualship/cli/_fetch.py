from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import click
from pydantic import BaseModel

from virtualship.utils import _dump_yaml, _generic_load_yaml

if TYPE_CHECKING:
    from virtualship.expedition.space_time_region import SpaceTimeRegion

DOWNLOAD_METADATA = "download_metadata.yaml"


def _hash(s: str, *, length: int) -> str:
    """Create a hash of a string."""
    assert length % 2 == 0, "Length must be even."
    half_length = length // 2

    return hashlib.shake_128(s.encode("utf-8")).hexdigest(half_length)


def create_hash(s: str) -> str:
    """Create an 8 digit hash of a string."""
    return _hash(s, length=8)


def hash_model(model: BaseModel, salt: int = 0) -> str:
    """
    Hash a Pydantic model.

    :param region: The region to hash.
    :param salt: Salt to add to the hash.
    :returns: The hash.
    """
    return create_hash(model.model_dump_json() + str(salt))


def get_space_time_region_hash(space_time_region: SpaceTimeRegion) -> str:
    # Increment salt in the event of breaking data fetching changes with prior versions
    # of virtualship where you want to force new hashes (i.e., new data downloads)
    salt = 0
    return hash_model(space_time_region, salt=salt)


def filename_to_hash(filename: str) -> str:
    """Extract hash from filename of the format YYYYMMDD_HHMMSS_{hash}."""
    parts = filename.split("_")
    if len(parts) != 3:
        raise ValueError(
            f"Filename '{filename}' must have 3 parts delimited with underscores."
        )
    return parts[-1]


def hash_to_filename(hash: str) -> str:
    """Return a filename of the format YYYYMMDD_HHMMSS_{hash}."""
    if "_" in hash:
        raise ValueError("Hash cannot contain underscores.")
    return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash}"


class IncompleteDownloadError(Exception):
    """Exception raised for incomplete downloads."""

    pass


class DownloadMetadata(BaseModel):
    """Metadata for a data download."""

    download_complete: bool
    download_date: datetime | None = None

    def to_yaml(self, file_path: str | Path) -> None:
        with open(file_path, "w") as file:
            _dump_yaml(self, file)

    @classmethod
    def from_yaml(cls, file_path: str | Path) -> DownloadMetadata:
        return _generic_load_yaml(file_path, cls)


def get_existing_download(
    data_folder: Path, space_time_region_hash: str
) -> Path | None:
    """Check if a download has already been completed. If so, return the path for existing download."""
    for download_path in data_folder.rglob("*"):
        try:
            hash = filename_to_hash(download_path.name)
        except ValueError:
            continue

        if hash == space_time_region_hash:
            assert_complete_download(download_path)
            return download_path

    return None


def assert_complete_download(download_path: Path) -> None:
    download_metadata = download_path / DOWNLOAD_METADATA
    try:
        with open(download_metadata) as file:
            assert DownloadMetadata.from_yaml(file).download_complete
    except (FileNotFoundError, AssertionError) as e:
        raise IncompleteDownloadError(
            f"Download at {download_path} was found, but looks to be incomplete "
            f"(likely due to interupting it mid-download). Please delete this folder and retry."
        ) from e
    return


def complete_download(download_path: Path) -> None:
    """Mark a download as complete."""
    download_metadata = download_path / DOWNLOAD_METADATA
    metadata = DownloadMetadata(download_complete=True, download_date=datetime.now())
    metadata.to_yaml(download_metadata)
    return
