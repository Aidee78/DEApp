from deapp.models.excel.dispensing import DispensingRecord
from deapp.models.extracted_data import ReportExtractedData
from deapp.models.excel.field import FlaggedValue
from deapp.services.excel import utils



def get_dispensing_records_from_processing_report(processing_reports: list[ReportExtractedData]) -> list[DispensingRecord]:
    records: list[DispensingRecord] = []


    for processing_report in processing_reports:
        if processing_report.data:
            for extracted_data in processing_report.data:
                for production_activity in extracted_data.activities:

                    if (
                        production_activity.stage is not None
                        and "dispensing" in production_activity.stage.lower()
                    ):
                        shift = utils.to_shift(processing_report.shift)
                        records.append(
                            DispensingRecord(
                                date=utils.to_datetime(processing_report.report_date),

                                line=utils.to_production_line(
                                extracted_data.production_line,),

                                shift=shift,

                                product=utils.to_resolve_product(
                                production_activity.product_name,
                                production_activity.batch_no,
                                ),
                                    
                                batch_number=utils.to_batch_number(
                                production_activity.batch_no,
                                ),

                                quantity_kg=utils.to_extract_kg_quantity(
                                production_activity.no,
                                ),
                                
                                dispensing_room=FlaggedValue(
                                    utils.to_dispensing_room(
                                        production_activity.stage,
                                    ),
                                ),
                                officer=FlaggedValue(
                                    utils.to_personnel_names(
                                        extracted_data.personnels_responsible,
                                    ),
                                ),
                                start_time=FlaggedValue(
                                    utils._extract_single_time(
                                        production_activity.start_time,
                                        shift.value,
                                    ),
                                ),
                                stop_time=FlaggedValue(
                                    utils._extract_single_time(
                                        production_activity.end_time,
                                        shift.value,
                                    ),
                                ),
                                status=FlaggedValue(
                                    utils.to_valid_string(
                                        production_activity.status,
                                    ),
                                ),
                                remarks=FlaggedValue(
                                    f"{utils.to_valid_string(production_activity.challenges)} "
                                    f"{utils.to_valid_string(production_activity.action_taken_remarks)}",
                                ),
                                received_at=processing_report.received_at,
                            )
                        )

    return records

def get_dispensing_records_from_store_packaging_report(store_packaging_reports: list[ReportExtractedData]) -> list[DispensingRecord]:
    records: list[DispensingRecord] = []


    for store_packaging_report in store_packaging_reports:
        if store_packaging_report.data:
            for extracted_data in store_packaging_report.data:
                for production_activity in extracted_data.activities:

                    if (
                        production_activity.stage is not None
                        and "dispensing" in production_activity.stage.lower()
                    ):
                        shift = utils.to_shift(store_packaging_report.shift)
                        records.append(
                            DispensingRecord(
                                date=FlaggedValue(
                                    utils.to_datetime(store_packaging_report.report_date),
                                ),
                                line=FlaggedValue(
                                    utils.to_production_line(
                                        extracted_data.production_line,
                                    ),
                                ),
                                shift=FlaggedValue(shift),
                                product=FlaggedValue(
                                    utils.to_resolve_product(
                                        production_activity.product_name,
                                        production_activity.batch_no,
                                    ),
                                ),
                                batch_number=FlaggedValue(
                                    utils.to_batch_number(
                                        production_activity.batch_no,
                                    ),
                                ),
                                quantity_kg=FlaggedValue(
                                    utils.to_extract_kg_quantity(
                                        production_activity.no,
                                    ),
                                ),
                                dispensing_room=FlaggedValue(
                                    utils.to_dispensing_room(
                                        production_activity.stage,
                                    ),
                                ),
                                officer=FlaggedValue(
                                    utils.to_personnel_names(
                                        extracted_data.personnels_responsible,
                                    ),
                                ),
                                start_time=FlaggedValue(
                                    utils._extract_single_time(
                                        production_activity.start_time,
                                        shift,
                                    ),
                                ),
                                stop_time=FlaggedValue(
                                    utils._extract_single_time(
                                        production_activity.end_time,
                                        shift,
                                    ),
                                ),
                                status=FlaggedValue(
                                    utils.to_valid_string(
                                        production_activity.status,
                                    ),
                                ),
                                remarks=FlaggedValue(
                                    f"{utils.to_valid_string(production_activity.challenges)} "
                                    f"{utils.to_valid_string(production_activity.action_taken_remarks)}",
                                ),
                                received_at=store_packaging_report.received_at,
                            )
                        )

    return records
