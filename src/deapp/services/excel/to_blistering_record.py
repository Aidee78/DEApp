"""Convert processing and IPQC report activities into blistering records."""

from deapp.models.excel.field import FlaggedValue
from deapp.models.excel.blistering import BlisteringRecord
from deapp.models.extracted_data import ProductionActivity, ReportExtractedData
from deapp.services.excel import utils


def get_blistering_records_from_ipqc_report(
    ipqc_reports: list[ReportExtractedData],
    report_name: str
) -> list[BlisteringRecord]:
    """Extract blistering records from ipqc reports."""
    records: list[BlisteringRecord] = []
    
    for report in ipqc_reports:
        if report.data:
            shift = utils.to_shift(report.shift)
            for extracted_data in report.data:
                for activity in extracted_data.activities:
                    
                    if (
                        activity.stage is None
                        or "blistering" not in activity.stage.casefold()
                        or not utils.contains_close_word(
                            activity.stage, "blistering"
                        )
                    ):
                        continue

                    drums, quantity_kg, blisters = utils.to_drums_kg_and_blisters(activity.no, activity.mc_no)
        
                    records.append(
                        BlisteringRecord(
                            date=utils.to_datetime(report.report_date),
                            machine=utils.to_blistering_machine(
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
                                shift.value,
                            ),
                            stop_time=utils.extract_time(
                                activity.end_time,
                                shift.value,
                            ),
                            idle_time=utils.to_idle_duration(activity.idle_time),


                            drums = drums,
                            output = blisters,
                            quantity_kg = quantity_kg,


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
