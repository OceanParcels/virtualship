from functools import lru_cache
from importlib.resources import files


def load_static_file(name: str) -> str:
    """Load static file from the ``virtualship.static`` module by file name."""
    return files("virtualship.static").joinpath(name).read_text(encoding="utf-8")


@lru_cache(None)
def get_example_config() -> str:
    """Get the example configuration file."""
    return load_static_file("ship_config.yaml")


@lru_cache(None)
def get_example_schedule() -> str:
    """Get the example schedule file."""
    return load_static_file("schedule.yaml")
