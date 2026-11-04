"""Tests for processing date-range resolution."""

from datetime import date

import pytest

from deapp.utils.dates import resolve_date_range, parse_iso_date


def test_no_overrides_uses_last_successful_date_and_today() -> None:
    result = resolve_date_range(
        last_successful_date=date(2026, 10, 1),
        today=date(2026, 11, 2),
    )

    assert result == (date(2026, 10, 1), date(2026, 11, 2))


def test_start_date_only_defaults_end_date_to_today() -> None:
    result = resolve_date_range(
        start_date=date(2026, 10, 10),
        today=date(2026, 10, 31),
    )

    assert result == (date(2026, 10, 10), date(2026, 10, 31))


def test_end_date_only_starts_at_last_successful_date() -> None:
    result = resolve_date_range(
        end_date=date(2026, 10, 15),
        last_successful_date=date(2026, 10, 1),
        today=date(2026, 11, 2),
    )

    assert result == (date(2026, 10, 1), date(2026, 10, 15))


def test_both_supplied_dates_are_returned() -> None:
    result = resolve_date_range(
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 20),
        today=date(2026, 11, 2),
    )

    assert result == (date(2026, 10, 5), date(2026, 10, 20))


def test_explicit_start_date_allows_first_run_without_saved_date() -> None:
    result = resolve_date_range(
        start_date=date(2026, 10, 1),
        today=date(2026, 10, 31),
    )

    assert result == (date(2026, 10, 1), date(2026, 10, 31))


def test_missing_start_and_last_successful_date_is_rejected() -> None:
    with pytest.raises(ValueError, match="start date is required"):
        resolve_date_range(today=date(2026, 11, 2))


def test_start_date_after_end_date_is_rejected() -> None:
    with pytest.raises(ValueError, match="on or before"):
        resolve_date_range(
            start_date=date(2026, 10, 20),
            end_date=date(2026, 10, 5),
            today=date(2026, 11, 2),
        )


def test_start_date_after_today_is_rejected_when_end_date_defaults_to_today() -> None:
    with pytest.raises(ValueError, match="on or before"):
        resolve_date_range(
            start_date=date(2026, 11, 3),
            today=date(2026, 11, 2),
        )


def test_date_range_can_cross_month_and_year_boundaries() -> None:
    result = resolve_date_range(
        start_date=date(2025, 12, 31),
        end_date=date(2026, 1, 2),
        today=date(2026, 1, 3),
    )

    assert result == (date(2025, 12, 31), date(2026, 1, 2))



@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-10-01", date(2026, 10, 1)),
        ("2026-02-28", date(2026, 2, 28)),
    ],
)
def test_parse_iso_date_accepts_valid_dates(
    value: str,
    expected: date,
) -> None:
    assert parse_iso_date(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "2026-02-30",
        "10/01/2026",
        "2026-1-01",
        "",
    ],
)
def test_parse_iso_date_rejects_invalid_dates(value: str) -> None:
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        parse_iso_date(value)