"""Tests for conversion of granulation activity values."""

from datetime import datetime

import pytest

from deapp.models.extracted_data import (
    ExtractedData,
    ProductionActivity,
    ReportExtractedData,
)
from deapp.services.excel.to_granulation_record import (
    get_granulation_records_from_processing_report,
)


def _make_report(
    activities: list[ProductionActivity],
) -> ReportExtractedData:
    """Create a parsed report with one production line and activity table."""
    return ReportExtractedData(
        date_received="2026-11-19",
        report_date="2026-11-18",
        shift="night",
        data=[
            ExtractedData(
                production_line="TABLET",
                personnels_responsible="A. Operator",
                activities=activities,
            ),
        ],
        received_at=datetime.fromisoformat("2026-11-19T06:05:00+00:00"),
    )


def _activity(
    *,
    stage: str,
    batch_no: str,
    no: str,
) -> ProductionActivity:
    """Build a minimal activity row for the conversion tests."""
    return ProductionActivity(
        stage=stage,
        product_name="ASTAMENTIN 625MG",
        batch_no=batch_no,
        no=no,
        start_time="21:00",
        end_time="21:30",
        idle_time="00:05",
        status="COMPLETED",
    )


def test_granulation_percentages_use_preceding_same_batch_sifting_kg() -> None:
    report = _make_report(
        [
            _activity(
                stage="SIFTING",
                batch_no="1126056",
                no="108.39KG",
            ),
            _activity(
                stage="GRANULATION",
                batch_no="1126056",
                no="COARSE:70% FINE POWDER:29%",
            ),
        ],
    )

    [record] = get_granulation_records_from_processing_report([report])

    assert record.coarse_kg.value == pytest.approx(75.873)
    assert record.coarse_kg.flag == 0
    assert record.powder_kg.value == pytest.approx(31.4331)
    assert record.powder_kg.flag == 0


def test_granulation_does_not_use_sifting_kg_from_another_batch() -> None:
    report = _make_report(
        [
            _activity(
                stage="SIFTING",
                batch_no="1126055",
                no="108.39KG",
            ),
            _activity(
                stage="GRANULATION",
                batch_no="1126056",
                no="COARSE:70% FINE POWDER:29%",
            ),
        ],
    )

    [record] = get_granulation_records_from_processing_report([report])

    assert record.coarse_kg.value is None
    assert record.coarse_kg.flag == 2
    assert record.powder_kg.value is None
    assert record.powder_kg.flag == 2
