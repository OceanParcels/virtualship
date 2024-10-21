from pathlib import Path

import pytest
from click.testing import CliRunner

from virtualship.cli.commands import CONFIG_FILE, SCHEDULE_FILE, init


def test_init():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(init, ["."])
        assert result.exit_code == 0
        config = Path(CONFIG_FILE)
        schedule = Path(SCHEDULE_FILE)

        assert config.exists()
        assert schedule.exists()


def test_init_existing_config():
    runner = CliRunner()
    with runner.isolated_filesystem():
        config = Path("ship_config.yaml")
        config.write_text("test")

        with pytest.raises(FileExistsError):
            result = runner.invoke(init, ["."])
            raise result.exception


def test_init_existing_schedule():
    runner = CliRunner()
    with runner.isolated_filesystem():
        schedule = Path("schedule.yaml")
        schedule.write_text("test")

        with pytest.raises(FileExistsError):
            result = runner.invoke(init, ["."])
            raise result.exception
