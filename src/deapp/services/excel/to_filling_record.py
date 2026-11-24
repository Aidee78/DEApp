"""Convert processing and IPQC report activities into filling records."""

from deapp.models.excel.filling import FillingRecord
from deapp.models.extracted_data import ProductionActivity, ReportExtractedData
from deapp.services.excel import utils


def get_filling_records_from_ipqc_report(
    ipqc_reports: list[ReportExtractedData],
    report_name: str,
) -> list[FillingRecord]:
    """Extract filling records from ipqc reports."""
    records: list[FillingRecord] = []
    
    for report in ipqc_reports:
        if report.data:
            shift = utils.to_shift(report.shift, report.received_at)
            for extracted_data in report.data:
                for activity in extracted_data.activities:
                    
                    if (
                        activity.stage is None
                        or "filling" not in activity.stage.casefold()
                        or not utils.contains_close_word(
                            activity.stage, "filling"
                        )
                    ):
                        continue

                    drums, quantity_kg, output = utils.to_drums_kg_and_capsules(activity.no)
        
                    records.append(
                        FillingRecord(
                            date=utils.to_datetime(report.report_date),
                            line=utils.to_filling_production_line(
                                extracted_data, activity
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


                            drums = drums,
                            output = output,
                            quantity_kg = quantity_kg,


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
