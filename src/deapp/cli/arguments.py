"""Command-line argument parsing for DEApp."""

import argparse
from collections.abc import Sequence

from deapp.utils.dates import parse_iso_date


def build_parser() -> argparse.ArgumentParser:
    """Create the parser for DEApp's optional processing date overrides."""
    parser = argparse.ArgumentParser(
        prog="deapp",
        description="Process DEApp emails for a specified date range.",
    )
    parser.add_argument(
        "--start-date",
        type=parse_iso_date,
        metavar="YYYY-MM-DD",
        help="first date to process",
    )
    parser.add_argument(
        "--end-date",
        type=parse_iso_date,
        metavar="YYYY-MM-DD",
        help="last date to process",
    )
    return parser


def parse_arguments(
    argv: Sequence[str] | None = None,
) -> argparse.Namespace:
    """Parse CLI arguments and reject a reversed explicitly supplied range."""
    parser = build_parser()
    arguments = parser.parse_args(argv)

    if (
        arguments.start_date is not None
        and arguments.end_date is not None
        and arguments.start_date > arguments.end_date
    ):
        parser.error("--start-date must be on or before --end-date")

    return arguments