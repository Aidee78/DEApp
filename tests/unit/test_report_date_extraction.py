"""Tests for extracting report dates from email text."""

from datetime import date, datetime

import pytest

from deapp.parsers.utils import (
    _normalize_report_date_text,
    extract_report_date_and_shift,
)


@pytest.mark.parametrize(
    "date_phrase",
    [
        "18th NOVEMVER, 2026",
        "NOVEMVER 18th, 2026",
    ],
)
def test_report_date_extraction_corrects_a_clear_month_typo(
    date_phrase: str,
) -> None:
    report_date, _ = extract_report_date_and_shift(
        f"<p>{date_phrase}</p>",
        received_at=datetime(2026, 11, 19),
    )

    assert report_date == date(2026, 11, 18)


def test_month_typo_is_corrected_only_inside_a_complete_date() -> None:
    normalized = _normalize_report_date_text(
        "18 NOVEMVER 2026; NOVEMVER appears in this note."
    )

    assert normalized == "18 November 2026; NOVEMVER appears in this note."


def test_low_confidence_month_token_is_left_unchanged() -> None:
    text = "18 NOTAMONTH 2026"

    assert _normalize_report_date_text(text) == text
