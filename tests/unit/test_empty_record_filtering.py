"""Tests for filtering records that contain no activity data."""

from dataclasses import replace
from datetime import datetime, time, timezone

from deapp.models.excel.blending import BlendingRecord
from deapp.models.excel.field import FlaggedValue
from deapp.services.excel.reconciliation import remove_completely_empty_records


def _empty_blending_record() -> BlendingRecord:
    """Build an unbatched record with no activity values."""
    return BlendingRecord(
        date=FlaggedValue(None, 1),
        line=FlaggedValue(None, 1),
        product=FlaggedValue(None, 1),
        batch_number=FlaggedValue(None, 1),
        officer=FlaggedValue(None, 1),
        start_time=FlaggedValue(None, 3),
        stop_time=FlaggedValue(None, 3),
        idle_time=FlaggedValue(None, 3),
        quantity_kg=FlaggedValue(None, 1),
        drums=FlaggedValue(None, 1),
        status=FlaggedValue(None, 1),
        remarks=FlaggedValue(None, 1),
        shift=FlaggedValue("Day", 3),
        received_at=datetime(2026, 11, 19, 15, 30, tzinfo=timezone.utc),
        report_type="test",
    )


def test_empty_record_is_removed_when_missing_times_have_flag_three() -> None:
    record = _empty_blending_record()

    assert remove_completely_empty_records([record]) == []


def test_record_with_only_an_idle_duration_is_retained() -> None:
    record = replace(
        _empty_blending_record(),
        idle_time=FlaggedValue(time(0, 10), 3),
    )

    assert remove_completely_empty_records([record]) == [record]


def test_record_with_a_populated_conflicted_time_is_retained() -> None:
    record = replace(
        _empty_blending_record(),
        start_time=FlaggedValue(time(17, 30), 3),
    )

    assert remove_completely_empty_records([record]) == [record]
