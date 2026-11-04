"""Tests for reading and writing DEApp execution state."""

import json
from datetime import date
from pathlib import Path

import pytest

from deapp.state.state_manager import (
    StateError,
    read_last_successful_date,
    write_last_successful_date,
)


def test_missing_state_file_returns_none(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"

    assert read_last_successful_date(state_file) is None


def test_empty_state_object_returns_none(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text("{}", encoding="utf-8")

    assert read_last_successful_date(state_file) is None


def test_write_and_read_last_successful_date(tmp_path: Path) -> None:
    state_file = tmp_path / "data" / "state.json"
    successful_date = date(2026, 10, 1)

    write_last_successful_date(state_file, successful_date)

    assert read_last_successful_date(state_file) == successful_date
    assert json.loads(state_file.read_text(encoding="utf-8")) == {
        "last_successful_date": "2026-10-01"
    }


def test_invalid_json_raises_state_error(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text("{invalid json", encoding="utf-8")

    with pytest.raises(StateError, match="State file is not valid JSON"):
        read_last_successful_date(state_file)


def test_non_object_json_raises_state_error(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text("[]", encoding="utf-8")

    with pytest.raises(StateError, match="JSON object"):
        read_last_successful_date(state_file)


def test_missing_date_field_raises_state_error(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text('{"other": "value"}', encoding="utf-8")

    with pytest.raises(StateError, match="last_successful_date"):
        read_last_successful_date(state_file)


def test_invalid_saved_date_raises_state_error(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"last_successful_date": "2026-02-30"}',
        encoding="utf-8",
    )

    with pytest.raises(StateError, match="invalid last_successful_date"):
        read_last_successful_date(state_file)


def test_unreadable_state_file_raises_state_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text("{}", encoding="utf-8")

    def fail_read_text(
        path: Path,
        *args: object,
        **kwargs: object,
    ) -> str:
        if path == state_file:
            raise PermissionError("access denied")
        raise AssertionError("Unexpected path read")

    monkeypatch.setattr(Path, "read_text", fail_read_text)
    # monkeypatch temporarily replaces Path.read_text() with 
    # fail_read_text(), which always raises OSError.

    with pytest.raises(StateError, match="Could not read state file"):
        read_last_successful_date(state_file)


def test_failed_replace_removes_temporary_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_file = tmp_path / "state.json"

    def fail_replace(self: Path, target: Path) -> Path:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(Path, "replace", fail_replace)
    # monkeypatch temporarily replaces Path.replace() with fail_replace
    # (), which always raises OSError. That simulates the failure; it
    #  does not actually interfere with file permissions.

    with pytest.raises(StateError, match="Could not write state file"):
        write_last_successful_date(state_file, date(2026, 10, 1))

    assert not list(tmp_path.glob(".state.json.*.tmp"))