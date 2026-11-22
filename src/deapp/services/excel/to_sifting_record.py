"""Convert processing and IPQC report activities into sifting records."""

from datetime import time
import re

from deapp.models.excel.field import FlaggedValue
from deapp.models.excel.sifting import SiftingRecord
from deapp.models.extracted_data import ReportExtractedData
from deapp.services.excel import utils


def _to_idle_duration(value: str | None) -> FlaggedValue[time | None]:
    """Parse an elapsed HH:MM[:SS] duration without applying shift offsets."""
    if value is None:
        return FlaggedValue(None, 1)
    if not isinstance(value, str):
        return FlaggedValue(None, 2)

    normalized = re.sub(r"\s+", "", value)
    if not normalized or re.fullmatch(r"[-=]+", normalized):
        return FlaggedValue(None, 1)

    match = re.fullmatch(
        r"(?P<hours>\d{1,2}):(?P<minutes>\d{1,2})"
        r"(?::(?P<seconds>\d{1,2}))?",
        normalized,
    )
    if match is None:
        return FlaggedValue(None, 2)

    hours = int(match.group("hours"))
    minutes = int(match.group("minutes"))
    seconds = int(match.group("seconds") or 0)
    if hours > 23 or minutes > 59 or seconds > 59:
        return FlaggedValue(None, 2)

    return FlaggedValue(time(hours, minutes, seconds), 0)


def _get_sifting_records(
    reports: list[ReportExtractedData],
) -> list[SiftingRecord]:
    """Convert every sifting activity in a collection of parsed reports."""
    records: list[SiftingRecord] = []

    for report in reports:
        shift = utils.to_shift(report.shift)
        for extracted_data in report.data or []:
            for activity in extracted_data.activities:
                if (
                    activity.stage is None
                    or "sifting" not in activity.stage.casefold()
                ):
                    continue

                records.append(
                    SiftingRecord(
                        date=utils.to_datetime(report.report_date),
                        line=utils.to_production_line(
                            extracted_data.production_line,
                        ),
                        product=utils.to_resolve_product(
                            activity.product_name,
                            activity.batch_no,
                        ),
                        batch_number=utils.to_batch_number(activity.batch_no),
                        officer=utils.to_personnel_names(
                            extracted_data.personnels_responsible,
                        ),
                        start_time=utils.extract_time(
                            activity.start_time,
                            shift.value,
                        ),
                        stop_time=utils.extract_time(
                            activity.end_time,
                            shift.value,
                        ),
                        idle_time=_to_idle_duration(activity.idle_time),

                        quantity_kg=utils.to_extract_kg_quantity(activity.no),
                        
                        status=FlaggedValue(
                            utils.to_valid_string(activity.status),
                        ),
                        remarks=utils.to_remarks(
                            activity.challenges,
                            activity.action_taken_remarks,
                        ),
                        received_at=report.received_at,
                        shift=shift,
                    ),
                )

    return records


def get_sifting_records_from_processing_report(
    processing_reports: list[ReportExtractedData],
) -> list[SiftingRecord]:
    """Extract sifting records from processing reports."""
    return _get_sifting_records(processing_reports)


def get_sifting_records_from_ipqc_report(
    ipqc_reports: list[ReportExtractedData],
) -> list[SiftingRecord]:
    """Extract sifting records from IPQC reports."""
    return _get_sifting_records(ipqc_reports)
