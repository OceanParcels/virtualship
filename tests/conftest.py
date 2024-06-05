"""Test configuration that is ran for every test."""

import pytest


@pytest.fixture(autouse=True)
def change_test_dir(request, monkeypatch):
    """
    Set the working directory for each test to the directory of that test.

    :param request: -
    :param monkeypatch: -
    """
    monkeypatch.chdir(request.fspath.dirname)
