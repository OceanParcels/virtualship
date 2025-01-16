from pathlib import Path

import pytest
from click.testing import CliRunner

from virtualship.cli.commands import fetch, init
from virtualship.utils import SCHEDULE, SHIP_CONFIG


@pytest.fixture
def copernicus_subset_no_download(monkeypatch):
    """Mock the download function."""

    def fake_download(output_filename, output_directory, **_):
        Path(output_directory).joinpath(output_filename).touch()

    monkeypatch.setattr(
        "virtualship.cli.commands.copernicusmarine.subset", fake_download
    )
    yield


@pytest.fixture
def runner():
    """An example expedition."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(init, ["."])
        yield runner


def test_init():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(init, ["."])
        assert result.exit_code == 0
        config = Path(SHIP_CONFIG)
        schedule = Path(SCHEDULE)

        assert config.exists()
        assert schedule.exists()


def test_init_existing_config():
    runner = CliRunner()
    with runner.isolated_filesystem():
        config = Path(SHIP_CONFIG)
        config.write_text("test")

        with pytest.raises(FileExistsError):
            result = runner.invoke(init, ["."])
            raise result.exception


def test_init_existing_schedule():
    runner = CliRunner()
    with runner.isolated_filesystem():
        schedule = Path(SCHEDULE)
        schedule.write_text("test")

        with pytest.raises(FileExistsError):
            result = runner.invoke(init, ["."])
            raise result.exception


@pytest.mark.parametrize(
    "fetch_args",
    [
        [".", "--username", "test"],
        [".", "--password", "test"],
    ],
)
@pytest.mark.usefixtures("copernicus_subset_no_download")
def test_fetch_both_creds_via_cli(runner, fetch_args):
    result = runner.invoke(fetch, fetch_args)
    assert result.exit_code == 1
    assert "Both username and password" in result.exc_info[1].args[0]


@pytest.mark.usefixtures("copernicus_subset_no_download")
def test_fetch(runner):
    """Test the fetch command, but mock the download."""
    result = runner.invoke(fetch, [".", "--username", "test", "--password", "test"])
    assert result.exit_code == 0
