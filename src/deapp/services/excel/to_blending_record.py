from deapp.models.excel.blending import BlendingRecord
from deapp.models.extracted_data import ReportExtractedData
from deapp.models.excel.field import FlaggedValue
from deapp.services.excel import utils



def get_blending_records_from_processing_report(processing_reports: list[ReportExtractedData], report_name: str) -> list[BlendingRecord]:
    """Extract blending records from processing reports."""
    records: list[BlendingRecord] = []
    
    for report in processing_reports:
        if report.data:
            shift = utils.to_shift(report.shift, report.received_at)
            for extracted_data in report.data:
                for activity in extracted_data.activities:
                    if (
                        activity.stage is None
                        or "blending" not in activity.stage.casefold()
                        or not utils.contains_close_word(
                            activity.stage, "blending"
                        )
                    ):
                        continue
                            
                    quantity_kg, drums = utils.to_quantity_kg_and_drums(activity.no)
        
                    records.append(
                        BlendingRecord(
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

                            quantity_kg = quantity_kg,

                            drums = drums,

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


def get_blending_records_from_ipqc_report(
    ipqc_reports: list[ReportExtractedData],
    report_name: str,
) -> list[BlendingRecord]:
    """Extract granulation records from IPQC reports."""
    records: list[BlendingRecord] = []
    
    for report in ipqc_reports:
        if report.data:
            shift = utils.to_shift(report.shift, report.received_at)
            for extracted_data in report.data:
                for activity in extracted_data.activities:
                    if (
                        activity.stage is None
                        or "blending" not in activity.stage.casefold()
                        or not utils.contains_close_word(
                            activity.stage, "blending"
                        )
                    ):
                        continue
    
                    quantity_kg, drums = utils.to_quantity_kg_and_drums(activity.no)
    
                    records.append(
                        BlendingRecord(
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
    
                            quantity_kg = quantity_kg,
    
                            drums = drums,
    
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
