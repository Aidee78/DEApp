"""Convert store_packaging and packaging report activities into packaging records."""

from deapp.models.excel.packaging import PackagingRecord
from deapp.models.extracted_data import ProductionActivity, ReportExtractedData
from deapp.services.excel import utils


def get_packaging_records_from_packaging_report(
    packaging_reports: list[ReportExtractedData],
    report_name: str
) -> list[PackagingRecord]:
    """Extract packaging records from packaging reports."""
    records: list[PackagingRecord] = []

    
    for report in packaging_reports:
        if report.data:
            shift = utils.to_shift(report.shift, report.received_at)
            for extracted_data in report.data:
                for activity in extracted_data.activities:
                    
                    if (
                        activity.stage is None
                        or "packaging" not in activity.stage.casefold()
                        or not utils.contains_close_word(
                            activity.stage, "packaging"
                        )
                    ):
                        continue

        
                    records.append(
                        PackagingRecord(
                            date=utils.to_datetime(report.report_date),
                            line=utils.to_production_line(
                                extracted_data.production_line
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

                            number_of_cartons=utils.to_number_of_cartons(activity.no_of_cartons,activity.batch_no,),
                            
                            status=utils.to_status(activity.status),
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


def get_packaging_records_from_store_packaging_report(
    store_packaging_reports: list[ReportExtractedData],
    report_name: str
) -> list[PackagingRecord]:
    """Extract packaging records from packaging reports."""
    records: list[PackagingRecord] = []
    
    for report in store_packaging_reports:
        if report.data:
            shift = utils.to_shift(report.shift, report.received_at)
            for extracted_data in report.data:
                for activity in extracted_data.activities:
                    
                    if (
                        activity.stage is None
                        or (
                            activity.stage.casefold()
                            not in {line.casefold() for line in utils.PRODUCTION_LINES}
                            and not any(
                                utils.contains_close_word(activity.stage, line)
                                for line in utils.PRODUCTION_LINES
                            )
                        )
                    ):
                        continue

                    records.append(
                        PackagingRecord(
                            date=utils.to_datetime(report.report_date),
                            line=utils.to_production_line(
                                extracted_data.production_line
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

                            number_of_cartons=utils.to_number_of_cartons(activity.no_of_cartons,activity.batch_no,),
                            
                            status=utils.to_status(activity.status),
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
