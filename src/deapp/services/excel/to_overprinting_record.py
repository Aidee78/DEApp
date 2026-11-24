"""Convert store_packaging and packaging report activities into overprinting records."""

from deapp.models.excel.field import FlaggedValue
from deapp.models.excel.overprinting import OverprintingRecord
from deapp.models.extracted_data import ProductionActivity, ReportExtractedData
from deapp.services.excel import utils


def get_overprinting_records_from_packaging_report(
    overprinting_reports: list[ReportExtractedData],
    report_name: str
) -> list[OverprintingRecord]:
    """Extract overprinting records from packaging reports."""
    records: list[OverprintingRecord] = []

    
    for report in overprinting_reports:
        if report.data:
            shift = utils.to_shift(report.shift)
            for extracted_data in report.data:
                for activity in extracted_data.activities:
                    
                    if (
                        activity.stage is None
                        or "overprinting" not in activity.stage.casefold()
                        or not utils.contains_close_word(
                            activity.stage, "overprinting"
                        )
                    ):
                        continue

                    cartons, packs, bundles, pieces = utils.cartons_packs_bundles_pieces(activity.no, activity.mc_no)
        
                    records.append(
                        OverprintingRecord(
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
                                shift.value,
                            ),
                            stop_time=utils.extract_time(
                                activity.end_time,
                                shift.value,
                            ),
                            idle_time=utils.to_idle_duration(activity.idle_time),

                            number_of_cartons=cartons,
                            
                            number_of_packs=packs,
                            
                            number_of_bundles=bundles,
                            
                            number_of_pieces=pieces,
                            
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


def get_overprinting_records_from_store_packaging_report(
    store_overprinting_reports: list[ReportExtractedData],
    report_name: str
) -> list[OverprintingRecord]:
    """Extract overprinting records from store_packaging reports."""
    records: list[OverprintingRecord] = []
    
    for report in store_overprinting_reports:
        if report.data:
            shift = utils.to_shift(report.shift)
            for extracted_data in report.data:
                for activity in extracted_data.activities:
                    
                    if (
                        activity.stage is None
                        or "overprinting" not in activity.stage.casefold()
                        or not utils.contains_close_word(
                            activity.stage, "overprinting"
                        )
                    ):
                        continue

                    cartons, packs, bundles, pieces = utils.cartons_packs_bundles_pieces(activity.no, activity.mc_no)
        
                    records.append(
                        OverprintingRecord(
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
                                shift.value,
                            ),
                            stop_time=utils.extract_time(
                                activity.end_time,
                                shift.value,
                            ),
                            idle_time=utils.to_idle_duration(activity.idle_time),

                            number_of_cartons=cartons,

                            number_of_packs=packs,

                            number_of_bundles=bundles,

                            number_of_pieces=pieces,
                            
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
