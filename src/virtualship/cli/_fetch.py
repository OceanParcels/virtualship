from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import click
from pydantic import BaseModel

from virtualship.utils import _dump_yaml, _generic_load_yaml

DOWNLOAD_METADATA = "download_metadata.yaml"


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


def get_existing_download(data_folder: Path, aoi_hash: str) -> Path | None:
    """Check if a download has already been completed. If so, return the path for existing download."""
    for download_path in data_folder.iterdir():
        try:
            hash = filename_to_hash(download_path.name)
        except ValueError:
            click.echo(
                f"Skipping {download_path.name} as it is not a valid download folder name."
            )
            continue

        if hash == aoi_hash:
            check_complete_download(download_path)
            return download_path

    return None


def check_complete_download(download_path: Path) -> bool:
    """Check if a download is complete."""
    download_metadata = download_path / DOWNLOAD_METADATA
    try:
        with open(download_metadata) as file:
            assert DownloadMetadata.from_yaml(file).download_complete
    except (FileNotFoundError, AssertionError) as e:
        raise IncompleteDownloadError(
            f"Download at {download_path} was found, but looks to be incomplete "
            f"(likely due to interupting it mid-download). Please delete this and retry."
        ) from e
    return True


def complete_download(download_path: Path) -> None:
    """Mark a download as complete."""
    download_metadata = download_path / DOWNLOAD_METADATA
    metadata = DownloadMetadata(download_complete=True, download_date=datetime.now())
    metadata.to_yaml(download_metadata)
    return
