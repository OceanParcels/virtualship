"""Test configuration that is ran for every test."""

import shutil
import tempfile
from typing import Callable, Generator

import pytest


@pytest.fixture(autouse=True)
def change_test_dir(request, monkeypatch):
    """
    Set the working directory for each test to the directory of that test.

    :param request: -
    :param monkeypatch: -
    """
    monkeypatch.chdir(request.fspath.dirname)


@pytest.fixture
def tmp_dir_factory() -> Generator[Callable[[str], str], None, None]:
    """
    Yield functions that can generate a random directory and returns its path.

    Created directories are automatically deleted after the test.

    :yields: A generator for temporary directories that will be automatically removed.
    """
    created_dirs = []

    def _create_temp_dir(suffix: str):
        dir_path = tempfile.mkdtemp(suffix=suffix)
        created_dirs.append(dir_path)
        return dir_path

    yield _create_temp_dir

    for dir_path in created_dirs:
        shutil.rmtree(dir_path)
