from pathlib import Path

import pytest
from click.testing import CliRunner

from virtualship.cli.commands import init
from virtualship.utils import SCHEDULE, SHIP_CONFIG


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
