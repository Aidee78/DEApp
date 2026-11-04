"""Tests for command-line argument parsing."""

from datetime import date

import pytest

from deapp.cli.arguments import parse_arguments


def test_no_arguments_leaves_both_dates_unset() -> None:
    arguments = parse_arguments([])

    assert arguments.start_date is None
    assert arguments.end_date is None


def test_start_date_only() -> None:
    arguments = parse_arguments(["--start-date", "2026-10-01"])

    assert arguments.start_date == date(2026, 10, 1)
    assert arguments.end_date is None


def test_end_date_only() -> None:
    arguments = parse_arguments(["--end-date", "2026-10-31"])

    assert arguments.start_date is None
    assert arguments.end_date == date(2026, 10, 31)


def test_both_dates_in_valid_order() -> None:
    arguments = parse_arguments(
        ["--start-date", "2026-10-01", "--end-date", "2026-10-31"]
    )

    assert arguments.start_date == date(2026, 10, 1)
    assert arguments.end_date == date(2026, 10, 31)


@pytest.mark.parametrize(
    "value",
    [
        "2026-02-30",  # Impossible date.
        "10/01/2026",  # Wrong format.
        "2026-1-01",   # Month must have two digits.
        "",
    ],
)
def test_invalid_date_is_rejected(value: str) -> None:
    with pytest.raises(SystemExit) as error:
        parse_arguments(["--start-date", value])

    assert error.value.code == 2


def test_start_date_after_end_date_is_rejected() -> None:
    with pytest.raises(SystemExit) as error:
        parse_arguments(
            ["--start-date", "2026-10-31", "--end-date", "2026-10-01"]
        )

    assert error.value.code == 2