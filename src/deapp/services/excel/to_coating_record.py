"""Convert processing and IPQC report activities into coating records."""

from deapp.models.excel.field import FlaggedValue
from deapp.models.excel.coating import CoatingRecord
from deapp.models.extracted_data import ProductionActivity, ReportExtractedData
from deapp.services.excel import utils

def get_coating_records_from_processing_report(
    processing_reports: list[ReportExtractedData],
    report_name: str,
) -> list[CoatingRecord]:
    """Extract coating records from processing reports."""
    records: list[CoatingRecord] = []
    
    for report in processing_reports:
        if report.data:
            shift = utils.to_shift(report.shift)
            for extracted_data in report.data:
                for activity in extracted_data.activities:
                    if (
                        activity.stage is None
                        or "coating" not in activity.stage.casefold()
                        or not utils.contains_close_word(
                            activity.stage, "coating"
                        )
                    ):
                        continue

                    quantity_kg, tabs = utils.to_quantity_kg_and_tabs(activity.no)
        
                    records.append(
                        CoatingRecord(
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
                            idle_time=utils.to_idle_duration(activity.idle_time),

                            quantity_kg = quantity_kg,

                            quantity_tabs = tabs,

                            status=FlaggedValue(
                                utils.to_valid_string(activity.status),
                            ),
                            remarks=utils.to_remarks(
                                activity.challenges,
                                activity.action_taken_remarks,
                            ),
                            received_at=report.received_at,
                            shift=shift,
                            report_type=report_name
                        ),
                    )
    
    return records


def get_coating_records_from_ipqc_report(
    ipqc_reports: list[ReportExtractedData],
    report_name: str,
) -> list[CoatingRecord]:
    """Extract coating records from ipqc reports."""
    records: list[CoatingRecord] = []
    
    for report in ipqc_reports:
        if report.data:
            shift = utils.to_shift(report.shift)
            for extracted_data in report.data:
                for activity in extracted_data.activities:
                    if (
                        activity.stage is None
                        or "coating" not in activity.stage.casefold()
                        or not utils.contains_close_word(
                            activity.stage, "coating"
                        )
                    ):
                        continue

                    quantity_kg, quantity_tabs = utils.to_quantity_kg_and_tabs(activity.no)
        
                    records.append(
                        CoatingRecord(
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
                            idle_time=utils.to_idle_duration(activity.idle_time),

                            quantity_kg = quantity_kg,

                            quantity_tabs = quantity_tabs,

                            status=FlaggedValue(
                                utils.to_valid_string(activity.status),
                            ),
                            remarks=utils.to_remarks(
                                activity.challenges,
                                activity.action_taken_remarks,
                            ),
                            received_at=report.received_at,
                            shift=shift,
                            report_type=report_name
                        ),
                    )
    
    return records
