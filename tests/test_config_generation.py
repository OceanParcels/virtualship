from virtualship.utils import get_example_config, get_example_schedule


def test_get_example_config():
    assert len(get_example_config()) > 0


def test_get_example_schedule():
    assert len(get_example_schedule()) > 0
