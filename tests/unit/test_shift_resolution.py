"""Tests for receipt-time shift resolution and conflict flag propagation."""

from datetime import datetime, time, timezone

import pytest

from deapp.models.excel.field import FlaggedValue
from deapp.models.extracted_data import (
    ExtractedData,
    ProductionActivity,
    ReportExtractedData,
)
from deapp.services.excel import utils
from deapp.services.excel.to_blending_record import (
    get_blending_records_from_processing_report,
)


@pytest.mark.parametrize(
    ("received_at", "reported_shift", "expected_shift"),
    [
        # Lagos-local 16:00 and 22:00 are included in the Day window.
        (datetime(2026, 11, 19, 15, 0, tzinfo=timezone.utc), "Night", "Day"),
        (datetime(2026, 11, 19, 21, 0, tzinfo=timezone.utc), "Night", "Day"),
        # Lagos-local 04:00 and 10:00 are included in the Night window.
        (datetime(2026, 11, 19, 3, 0, tzinfo=timezone.utc), "Day", "Night"),
        (datetime(2026, 11, 19, 9, 0, tzinfo=timezone.utc), "Day", "Night"),
    ],
)
def test_receipt_time_overrides_conflicting_report_shift_at_window_edges(
    received_at: datetime,
    reported_shift: str,
    expected_shift: str,
) -> None:
    shift = utils.to_shift(reported_shift, received_at)

    assert shift.value == expected_shift
    assert shift.flag == 3


def test_matching_shift_and_receipt_outside_windows_keep_report_flag() -> None:
    matching_receipt = datetime(2026, 11, 19, 15, 30, tzinfo=timezone.utc)
    outside_window_receipt = datetime(2026, 11, 19, 9, 1, tzinfo=timezone.utc)

    matching_shift = utils.to_shift("Day", matching_receipt)
    outside_window_shift = utils.to_shift("Day", outside_window_receipt)

    assert matching_shift.value == "Day"
    assert matching_shift.flag == 0
    assert outside_window_shift.value == "Day"
    assert outside_window_shift.flag == 0


@pytest.mark.parametrize(
    ("reported_shift", "expected_value", "expected_flag"),
    [
        (None, "Day", 3),
        ("", None, 1),
        ("day and night", None, 2),
    ],
)
def test_missing_or_unclear_report_shift_is_not_inferred_from_receipt_time(
    reported_shift: str | None,
    expected_value: str | None,
    expected_flag: int,
) -> None:
    received_at = datetime(2026, 11, 19, 15, 30, tzinfo=timezone.utc)

    shift = utils.to_shift(reported_shift, received_at)

    assert shift.value == expected_value
    assert shift.flag == expected_flag


def test_naive_receipt_timestamp_does_not_infer_shift() -> None:
    shift = utils.to_shift("Night", datetime(2026, 11, 19, 18, 30))

    assert shift.value == "Night"
    assert shift.flag == 0


def test_shift_conflict_flag_is_inherited_by_parsed_and_invalid_time_fields() -> None:
    conflict = FlaggedValue("Day", 3)

    parsed_start = utils.extract_time("5:30", conflict)
    invalid_stop = utils.extract_time("unknown", conflict)
    parsed_idle = utils.to_idle_duration("00:10", conflict)
    missing_idle = utils.to_idle_duration(None, conflict)

    assert parsed_start.value == time(17, 30)
    assert parsed_start.flag == 3
    assert invalid_stop.value is None
    assert invalid_stop.flag == 3
    assert parsed_idle.value == time(0, 10)
    assert parsed_idle.flag == 3
    assert missing_idle.value is None
    assert missing_idle.flag == 3


def test_blending_converter_propagates_receipt_time_conflict_to_time_fields() -> None:
    report = ReportExtractedData(
        date_received="2026-11-19",
        report_date="2026-11-18",
        shift="Night",
        data=[
            ExtractedData(
                production_line="Tablet",
                personnels_responsible="A. Operator",
                activities=[
                    ProductionActivity(
                        stage="Blending",
                        product_name="ASTAMENTIN 625MG",
                        batch_no="1126056",
                        no="25KG",
                        start_time="5:30",
                        end_time="6:00",
                        idle_time="00:10",
                        status="COMPLETED",
                    ),
                ],
            ),
        ],
        # 15:30 UTC is 16:30 in Lagos, within the Day receipt window.
        received_at=datetime(2026, 11, 19, 15, 30, tzinfo=timezone.utc),
    )

    [record] = get_blending_records_from_processing_report([report], "test")

    assert record.shift.value == "Day"
    assert record.shift.flag == 3
    assert record.start_time.value == time(17, 30)
    assert record.start_time.flag == 3
    assert record.stop_time.value == time(18, 0)
    assert record.stop_time.flag == 3
    assert record.idle_time.value == time(0, 10)
    assert record.idle_time.flag == 3
