"""
Command line interface tool for virtualship.expedition.do_expedition:do_expedition function.

See --help for usage.
"""

import argparse
from pathlib import Path

from virtualship.expedition.do_expedition import do_expedition


def main() -> None:
    """Entrypoint for the tool."""
    parser = argparse.ArgumentParser(
        prog="do_expedition",
        description="Perform an expedition based on a provided schedule.",
    )
    parser.add_argument(
        "dir",
        type=str,
        help="Directory for the expedition. This should contain all required configuration files, and the result will be saved here as well.",
    )
    args = parser.parse_args()

    do_expedition(Path(args.dir))


if __name__ == "__main__":
    main()
