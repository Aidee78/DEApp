"""Convert processing and IPQC report activities into granulation records."""

from deapp.models.excel.field import FlaggedValue
from deapp.models.excel.granulation import GranulationRecord
from deapp.models.extracted_data import ProductionActivity, ReportExtractedData
from deapp.services.excel import utils

def get_granulation_records_from_processing_report(
    processing_reports: list[ReportExtractedData],
    report_name: str,
) -> list[GranulationRecord]:
    """Extract granulation records from processing reports."""
    records: list[GranulationRecord] = []
    
    for report in processing_reports:
        if report.data:
            shift = utils.to_shift(report.shift)
            for extracted_data in report.data:
                for activity in extracted_data.activities:
                    if (
                        activity.stage is None
                        or "granulation" not in activity.stage.casefold()
                        or not utils.contains_close_word(
                            activity.stage, "granulation"
                        )
                    ):
                        continue

                    coarse_percent, powder_percent = utils.to_coarse_powder(activity.no)
        
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
                            idle_time=utils.to_idle_duration(activity.idle_time),

                            coarse_percent = coarse_percent,

                            powder_percent = powder_percent,

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


def get_granulation_records_from_ipqc_report(
    ipqc_reports: list[ReportExtractedData],
    report_name: str,
) -> list[GranulationRecord]:
    """Extract granulation records from IPQC reports."""
    records: list[GranulationRecord] = []
    
    for report in ipqc_reports:
        if report.data:
            shift = utils.to_shift(report.shift)
            for extracted_data in report.data:
                for activity in extracted_data.activities:
                    if (
                        activity.stage is None
                        or "granulation" not in activity.stage.casefold()
                        or not utils.contains_close_word(
                            activity.stage, "granulation"
                        )
                    ):
                        
                        continue

                    coarse_percent, powder_percent = utils.to_coarse_powder(activity.no)
        
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
                            idle_time=utils.to_idle_duration(activity.idle_time),

                            coarse_percent = coarse_percent,

                            powder_percent = powder_percent,

                            status=FlaggedValue(
                                utils.to_valid_string(activity.status),
                            ),
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