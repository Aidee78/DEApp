"""Tests for Phase 2 application startup coordination."""

from datetime import date
from pathlib import Path

import pytest

from deapp.application.runner import prepare_execution
from deapp.config import Settings
from deapp.state.state_manager import (
    StateError,
    write_last_successful_date,
)


def make_settings(state_file: Path) -> Settings:
    """Build settings that point state at a test-owned temporary path."""
    return Settings(
        app_name="DEApp",
        log_level="INFO",
        state_file=state_file,
        log_file=state_file.parent / "deapp.log",
    )


def test_default_range_uses_saved_date_and_today(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    write_last_successful_date(state_file, date(2026, 10, 1))

    result = prepare_execution(
        [],
        settings=make_settings(state_file),
        today=date(2026, 11, 2),
    )

    assert result == (date(2026, 10, 1), date(2026, 11, 2))


def test_explicit_dates_do_not_require_saved_state(tmp_path: Path) -> None:
    state_file = tmp_path / "missing-state.json"

    result = prepare_execution(
        ["--start-date", "2026-10-05", "--end-date", "2026-10-20"],
        settings=make_settings(state_file),
        today=date(2026, 11, 2),
    )

    assert result == (date(2026, 10, 5), date(2026, 10, 20))
    assert not state_file.exists()


def test_start_date_only_defaults_end_to_today(tmp_path: Path) -> None:
    state_file = tmp_path / "missing-state.json"

    result = prepare_execution(
        ["--start-date", "2026-10-10"],
        settings=make_settings(state_file),
        today=date(2026, 10, 31),
    )

    assert result == (date(2026, 10, 10), date(2026, 10, 31))


def test_end_date_only_starts_at_saved_date(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    write_last_successful_date(state_file, date(2026, 10, 1))

    result = prepare_execution(
        ["--end-date", "2026-10-15"],
        settings=make_settings(state_file),
        today=date(2026, 11, 2),
    )

    assert result == (date(2026, 10, 1), date(2026, 10, 15))


def test_no_start_date_or_saved_date_is_an_error(tmp_path: Path) -> None:
    settings = make_settings(tmp_path / "missing-state.json")

    with pytest.raises(ValueError, match="start date is required"):
        prepare_execution([], settings=settings, today=date(2026, 11, 2))


def test_invalid_saved_state_stops_preparation(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text("{invalid json", encoding="utf-8")

    with pytest.raises(StateError, match="valid JSON"):
        prepare_execution(
            [],
            settings=make_settings(state_file),
            today=date(2026, 11, 2),
        )