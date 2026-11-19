"""Tests for value-based activity reconciliation."""

from dataclasses import replace
from datetime import datetime, time, timezone

import pytest

from deapp.models.excel.blending import BlendingRecord
from deapp.models.excel.dispensing import DispensingRecord
from deapp.models.excel.field import FlaggedValue
from deapp.models.extracted_data import (
    ExtractedData,
    ProductionActivity,
    ReportExtractedData,
)
from deapp.parsers.report_parser import parse_production_activities
from deapp.services.excel.converter import Converter, remove_duplicate_records
from deapp.services.excel.reconciliation import (
    ReconciliationError,
    reconcile_records,
)


def _dispensing_record(
    *,
    received_at: datetime | None,
    product: str | None = "ASTAMOCIL 500MG",
    batch_number: str | None = "SM/EXP/11/26/173",
    officer: str | None = "FEMI OYEYINKA",
) -> DispensingRecord:
    """Build a record with a stable activity key for reconciliation tests."""
    return DispensingRecord(
        date=FlaggedValue(datetime(2026, 9, 16)),
        line=FlaggedValue("Dry Syrup"),
        shift=FlaggedValue("Night"),
        product=FlaggedValue(product),
        batch_number=FlaggedValue(batch_number),
        quantity_kg=FlaggedValue(None),
        dispensing_room=FlaggedValue("Dispensing Room 2"),
        officer=FlaggedValue(officer),
        start_time=FlaggedValue(None),
        stop_time=FlaggedValue(None),
        status=FlaggedValue(""),
        remarks=FlaggedValue(" || "),
        received_at=received_at,
    )


def _report(received_at: datetime, quantity: str) -> ReportExtractedData:
    """Build a processing report containing one dispensing activity."""
    return ReportExtractedData(
        date_received=received_at.date().isoformat(),
        report_date="2026-09-16",
        shift="night",
        data=[
            ExtractedData(
                production_line="Dry Syrup",
                personnels_responsible="FEMI OYEYINKA",
                activities=[
                    ProductionActivity(
                        stage="DISPENSING 2",
                        product_name="ASTAMOCIL 500MG",
                        batch_no="SM/EXP/11/26/173",
                        quantity=quantity,
                    ),
                ],
            ),
        ],
        received_at=received_at,
    )


def test_flagged_value_equality_ignores_flag() -> None:
    assert FlaggedValue("ASTAMOCIL 500MG", 0) == FlaggedValue(
        "ASTAMOCIL 500MG",
        3,
    )
    assert FlaggedValue("ASTAMOCIL 500MG", 0) != FlaggedValue(
        "ASTARCLOX 500MG",
        0,
    )


def test_reconcile_uses_latest_value_and_flags_only_conflicting_field() -> None:
    earlier = _dispensing_record(
        received_at=datetime(2026, 9, 16, 10, tzinfo=timezone.utc),
        product="ASTAMOCIL 500MG",
    )
    later = _dispensing_record(
        received_at=datetime(2026, 9, 16, 11, tzinfo=timezone.utc),
        product="ASTAMENTIN 625MG",
    )

    (merged,) = reconcile_records([earlier, later])

    assert merged.product == FlaggedValue("ASTAMENTIN 625MG", 3)
    assert merged.officer == FlaggedValue("FEMI OYEYINKA", 0)
    assert merged.batch_number == FlaggedValue("SM/EXP/11/26/173", 0)
    assert merged.received_at == later.received_at


def test_reconcile_does_not_group_records_missing_an_activity_key() -> None:
    first = _dispensing_record(
        received_at=datetime(2026, 9, 16, 10, tzinfo=timezone.utc),
        batch_number=None,
    )
    second = _dispensing_record(
        received_at=datetime(2026, 9, 16, 11, tzinfo=timezone.utc),
        batch_number=None,
        product="ASTAMENTIN 625MG",
    )

    assert reconcile_records([first, second]) == [first, second]


def test_reconcile_ignores_missing_field_values() -> None:
    earlier = _dispensing_record(
        received_at=datetime(2026, 9, 16, 10, tzinfo=timezone.utc),
        product=None,
    )
    later = _dispensing_record(
        received_at=datetime(2026, 9, 16, 11, tzinfo=timezone.utc),
        product="ASTAMOCIL 500MG",
    )

    (merged,) = reconcile_records([earlier, later])

    assert merged.product == FlaggedValue("ASTAMOCIL 500MG", 0)


def test_remove_duplicate_records_supports_blending_records() -> None:
    earlier = BlendingRecord(
        date=FlaggedValue(datetime(2026, 9, 16)),
        line=FlaggedValue("Capsule"),
        product=FlaggedValue("ASTAMOCIL 500MG"),
        batch_number=FlaggedValue("1026046"),
        officer=FlaggedValue("FEMI OYEYINKA"),
        start_time=FlaggedValue(time(10, 0)),
        stop_time=FlaggedValue(time(11, 0)),
        idle_time=FlaggedValue(time(0, 0)),
        quantity_kg=FlaggedValue(100.0),
        drums=FlaggedValue(2.0),
        status=FlaggedValue("Complete"),
        remarks=FlaggedValue("Earlier note"),
        shift=FlaggedValue("Night"),
        received_at=datetime(2026, 9, 16, 10, tzinfo=timezone.utc),
    )
    later = replace(
        earlier,
        remarks=FlaggedValue("Latest note"),
        received_at=datetime(2026, 9, 16, 11, tzinfo=timezone.utc),
    )

    (merged,) = remove_duplicate_records([earlier, later])

    assert merged.remarks == FlaggedValue("Latest note", 3)
    assert merged.quantity_kg == FlaggedValue(100.0, 0)


def test_reconcile_rejects_conflicting_values_with_tied_latest_times() -> None:
    received_at = datetime(2026, 9, 16, 10, tzinfo=timezone.utc)
    first = _dispensing_record(received_at=received_at, product="Product A")
    second = _dispensing_record(received_at=received_at, product="Product B")

    with pytest.raises(ReconciliationError, match="timestamps tie"):
        reconcile_records([first, second])


def test_reconcile_rejects_conflicts_without_receipt_timestamps() -> None:
    first = _dispensing_record(received_at=None, product="Product A")
    second = _dispensing_record(received_at=None, product="Product B")

    with pytest.raises(ReconciliationError, match="valid email received_at"):
        reconcile_records([first, second])


def test_converter_preserves_receipt_time_and_reconciles_activity() -> None:
    earlier = datetime(2026, 9, 16, 10, tzinfo=timezone.utc)
    later = datetime(2026, 9, 16, 11, tzinfo=timezone.utc)
    converter = Converter(
        ipqc_reports=[],
        packaging_reports=[],
        processing_reports=[
            _report(earlier, "100 kg"),
            _report(later, "120 kg"),
        ],
        store_packaging_reports=[],
    )

    (record,) = converter.get_dispensing_records()

    assert record.batch_number == FlaggedValue("SM/EXP/11/26/173", 0)
    assert record.quantity_kg == FlaggedValue(120.0, 3)
    assert record.product.flag == 0
    assert record.received_at == later


def test_report_parser_keeps_full_email_received_timestamp() -> None:
    received_at = datetime(2026, 9, 16, 11, 30, tzinfo=timezone.utc)
    content = """
    <p>Capsule night shift report</p>
    <table>
      <tr><th>STAGE</th><th>ITEM NAME</th><th>BATCH NO</th></tr>
      <tr><td>DISPENSING 2</td><td>ASTAMOCIL 500MG</td><td>1026046</td></tr>
    </table>
    """

    report = parse_production_activities(content, received_at=received_at)

    assert report.received_at == received_at
