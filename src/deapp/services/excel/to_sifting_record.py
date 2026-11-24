"""Convert processing and IPQC report activities into sifting records."""

from deapp.models.excel.sifting import SiftingRecord
from deapp.models.extracted_data import ReportExtractedData
from deapp.services.excel import utils


def _get_sifting_records(
    reports: list[ReportExtractedData],
    report_name: str,
) -> list[SiftingRecord]:
    """Convert every sifting activity in a collection of parsed reports."""
    records: list[SiftingRecord] = []

    for report in reports:
        shift = utils.to_shift(report.shift, report.received_at)
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
                            shift,
                        ),
                        stop_time=utils.extract_time(
                            activity.end_time,
                            shift,
                        ),
                        idle_time=utils.to_idle_duration(
                            activity.idle_time,
                            shift,
                        ),

                        quantity_kg=utils.to_extract_kg_quantity(activity.no),
                        
                        status=utils.to_status(activity.status),
                        remarks=utils.to_remarks(
                            activity.challenges,
                            activity.action_taken_remarks,
                        ),
                        received_at=report.received_at,
                        shift=shift,
                        report_type=report_name,
                    ),
                )

    return records


def get_sifting_records_from_processing_report(
    processing_reports: list[ReportExtractedData],
    report_name: str,
) -> list[SiftingRecord]:
    """Extract sifting records from processing reports."""
    return _get_sifting_records(processing_reports, report_name)


def get_sifting_records_from_ipqc_report(
    ipqc_reports: list[ReportExtractedData],
    report_name: str,
) -> list[SiftingRecord]:
    """Extract sifting records from IPQC reports."""
    return _get_sifting_records(ipqc_reports, report_name)
