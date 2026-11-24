"""Tests for flag selection when consolidated values are both empty."""

from datetime import datetime, timezone

from deapp.models.excel.blending import BlendingRecord
from deapp.models.excel.field import FieldFlag, FlaggedValue
from deapp.services.excel.reconciliation import consolidate_records


def _record(
    *,
    report_type: str,
    received_at: datetime,
    empty_flag: FieldFlag,
) -> BlendingRecord:
    """Build matching reports whose selected fields are empty."""
    return BlendingRecord(
        date=FlaggedValue(datetime(2026, 11, 23)),
        line=FlaggedValue("Tablet"),
        product=FlaggedValue("Product"),
        batch_number=FlaggedValue("Batch 1"),
        officer=FlaggedValue(None, empty_flag),
        start_time=FlaggedValue(None, empty_flag),
        stop_time=FlaggedValue(None, empty_flag),
        idle_time=FlaggedValue(None, empty_flag),
        quantity_kg=FlaggedValue(100.0),
        drums=FlaggedValue(None, empty_flag),
        status=FlaggedValue(None, empty_flag),
        remarks=FlaggedValue(None, empty_flag),
        shift=FlaggedValue("Day"),
        received_at=received_at,
        report_type=report_type,
    )


def test_both_none_fields_keep_the_greater_flag_in_stage_two() -> None:
    earlier = _record(
        report_type="processing_reports",
        received_at=datetime(2026, 11, 23, 10, tzinfo=timezone.utc),
        empty_flag=1,
    )
    later = _record(
        report_type="ipqc_reports",
        received_at=datetime(2026, 11, 23, 11, tzinfo=timezone.utc),
        empty_flag=3,
    )

    (merged,) = consolidate_records([earlier, later])

    assert merged.status == FlaggedValue(None, 3)
    assert merged.remarks == FlaggedValue(None, 3)
    assert merged.officer == FlaggedValue(None, 3)
    assert merged.idle_time == FlaggedValue(None, 3)
