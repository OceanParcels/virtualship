from pathlib import Path

import pytest
from pydantic import BaseModel

from virtualship.cli._fetch import (
    DOWNLOAD_METADATA,
    DownloadMetadata,
    IncompleteDownloadError,
    check_complete_download,
    complete_download,
    create_hash,
    filename_to_hash,
    get_existing_download,
    hash_model,
    hash_to_filename,
)


def test_create_hash():
    assert len(create_hash("correct-length")) == 8
    assert create_hash("same") == create_hash("same")
    assert create_hash("unique1") != create_hash("unique2")


def test_hash_filename_roundtrip():
    hash_ = create_hash("test")
    assert filename_to_hash(hash_to_filename(hash_)) == hash_


def test_hash_model():
    class TestModel(BaseModel):
        a: int
        b: str

    hash_model(TestModel(a=0, b="b"))


def test_complete_download(tmp_path):
    # Setup
    DownloadMetadata(download_complete=False).to_yaml(tmp_path / DOWNLOAD_METADATA)

    complete_download(tmp_path)

    assert check_complete_download(tmp_path)


def test_check_complete_download_complete(tmp_path):
    # Setup
    DownloadMetadata(download_complete=True).to_yaml(tmp_path / DOWNLOAD_METADATA)

    assert check_complete_download(tmp_path)


def test_check_complete_download_incomplete(tmp_path):
    # Setup
    DownloadMetadata(download_complete=False).to_yaml(tmp_path / DOWNLOAD_METADATA)

    with pytest.raises(IncompleteDownloadError):
        check_complete_download(tmp_path)


def test_check_complete_download_missing(tmp_path):
    with pytest.raises(IncompleteDownloadError):
        assert not check_complete_download(tmp_path)


@pytest.fixture
def existing_data_folder(tmp_path, monkeypatch):
    # Setup
    folders = [
        "YYYYMMDD_HHMMSS_hash",
        "YYYYMMDD_HHMMSS_hash2",
        "some-invalid-data-folder",
        "YYYYMMDD_HHMMSS_hash3",
    ]
    data_folder = tmp_path
    monkeypatch.setattr(
        "virtualship.cli._fetch.check_complete_download", lambda x: True
    )
    for f in folders:
        (data_folder / f).mkdir()
    yield data_folder


def test_get_existing_download(existing_data_folder):
    assert isinstance(get_existing_download(existing_data_folder, "hash"), Path)
    assert get_existing_download(existing_data_folder, "missing-hash") is None
