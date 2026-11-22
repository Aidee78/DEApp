"""Convert processing and IPQC report activities into granulation records."""

from datetime import time
import re

from deapp.models.excel.field import FlaggedValue
from deapp.models.excel.granulation import GranulationRecord
from deapp.models.extracted_data import ProductionActivity, ReportExtractedData
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


def _to_labeled_kg_quantity(
    value: str | None,
    label_pattern: str,
) -> FlaggedValue[float | None]:
    """Extract a labeled kilogram value, leaving other units unconverted."""
    if value is None:
        return FlaggedValue(None, 1)
    if not isinstance(value, str):
        return FlaggedValue(None, 2)

    number_pattern = r"(?:\d+\s*/\s*\d+|\d+(?:\.\d+)?|\.\d+)"
    match = re.search(
        rf"\b(?:{label_pattern})\b\s*[:=\-]?\s*"
        rf"(?P<quantity>{number_pattern}\s*kg\b)",
        value,
        flags=re.IGNORECASE,
    )
    if match is not None:
        return utils.to_extract_kg_quantity(match.group("quantity"))

    if not utils.to_valid_string(value):
        return FlaggedValue(None, 1)
    return FlaggedValue(None, 2)


def _to_labeled_percentage(
    value: str | None,
    label_pattern: str,
) -> FlaggedValue[float | None]:
    """Extract a labeled percentage between zero and one hundred."""
    if value is None:
        return FlaggedValue(None, 1)
    if not isinstance(value, str):
        return FlaggedValue(None, 2)

    match = re.search(
        rf"\b(?:{label_pattern})\b\s*[:=\-]?\s*"
        r"(?P<percentage>\d+(?:\.\d+)?|\.\d+)\s*%",
        value,
        flags=re.IGNORECASE,
    )
    if match is not None:
        percentage = float(match.group("percentage"))
        if 0 <= percentage <= 100:
            return FlaggedValue(percentage, 0)
        return FlaggedValue(None, 2)

    if not utils.to_valid_string(value):
        return FlaggedValue(None, 1)
    return FlaggedValue(None, 2)


def _normalize_batch_number(value: str | None) -> str | None:
    """Normalize a valid batch identifier for matching earlier activities."""
    parsed_batch = utils.to_batch_number(value)
    if parsed_batch.value is None:
        return None
    return re.sub(r"\s+", "", parsed_batch.value).casefold()


def _get_preceding_sifting_kg(
    activities: list[ProductionActivity],
    granulation_index: int,
    granulation_batch_number: str | None,
) -> FlaggedValue[float | None]:
    """Get the nearest earlier Sifting kg for this granulation batch."""
    batch_key = _normalize_batch_number(granulation_batch_number)
    if batch_key is None:
        return FlaggedValue(None, 2)

    for activity in reversed(activities[:granulation_index]):
        stage = activity.stage.casefold() if activity.stage else ""
        if "sifting" not in stage or "granulation" in stage:
            continue
        if _normalize_batch_number(activity.batch_no) != batch_key:
            continue

        return utils.to_extract_kg_quantity(activity.no)

    return FlaggedValue(None, 2)


def _to_granulation_kg(
    value: str | None,
    label_pattern: str,
    preceding_sifting_kg: FlaggedValue[float | None],
) -> FlaggedValue[float | None]:
    """Extract explicit kg or derive kg from the labeled percentage."""
    explicit_kg = _to_labeled_kg_quantity(value, label_pattern)
    if explicit_kg.value is not None or explicit_kg.flag == 1:
        return explicit_kg

    percentage = _to_labeled_percentage(value, label_pattern)
    if percentage.value is None:
        return percentage
    if preceding_sifting_kg.value is None:
        return FlaggedValue(None, 2)

    return FlaggedValue(
        preceding_sifting_kg.value * percentage.value / 100,
        0,
    )


def _get_granulation_records(
    reports: list[ReportExtractedData],
) -> list[GranulationRecord]:
    """Convert every granulation activity in a collection of parsed reports."""
    records: list[GranulationRecord] = []

    for report in reports:
        shift = utils.to_shift(report.shift)
        for extracted_data in report.data or []:
            for activity_index, activity in enumerate(extracted_data.activities):
                if (
                    activity.stage is None
                    or "granulation" not in activity.stage.casefold()
                ):
                    continue

                preceding_sifting_kg = _get_preceding_sifting_kg(
                    extracted_data.activities,
                    activity_index,
                    activity.batch_no,
                )

                records.append(
                    GranulationRecord(
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
                        coarse_kg=_to_granulation_kg(
                            activity.no,
                            "coarse",
                            preceding_sifting_kg,
                        ),
                        powder_kg=_to_granulation_kg(
                            activity.no,
                            r"fine(?:\s+powder)?|powder",
                            preceding_sifting_kg,
                        ),
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


def get_granulation_records_from_processing_report(
    processing_reports: list[ReportExtractedData],
) -> list[GranulationRecord]:
    """Extract granulation records from processing reports."""
    return _get_granulation_records(processing_reports)


def get_granulation_records_from_ipqc_report(
    ipqc_reports: list[ReportExtractedData],
) -> list[GranulationRecord]:
    """Extract granulation records from IPQC reports."""
    return _get_granulation_records(ipqc_reports)
