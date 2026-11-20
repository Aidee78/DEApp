"""
Converts the ReportExtractedData from each email gotten per day to excel records
"""

from collections.abc import Iterable
from itertools import chain
from typing import TypeVar

from deapp.models.excel import (
    blending,
    blistering,
    coating,
    compression,
    dispensing,
    filling,
    granulation,
    overprinting,
    packaging,
    sifting,
)
from deapp.models.extracted_data import ReportExtractedData
from deapp.models.excel.field import FlaggedValue
from deapp.services.excel import utils
from deapp.services.excel.reconciliation import consolidate_records


T = TypeVar("T")



def remove_duplicates(records: Iterable[T]) -> list[T]:
    """Return distinct records in their original order."""
    unique: list[T] = []

    for record in records:
        if record not in unique:
            unique.append(record)

    return unique

class Converter:
    def __init__(
        self,
        ipqc_reports: list[ReportExtractedData],
        packaging_reports: list[ReportExtractedData],
        processing_reports: list[ReportExtractedData],
        store_packaging_reports: list[ReportExtractedData],
    ) -> None:
        self.ipqc_reports = ipqc_reports
        self.packaging_reports = packaging_reports
        self.processing_reports = processing_reports
        self.store_packaging_reports = store_packaging_reports

    def get_blending_records(self,) -> list[blending.BlendingRecord]:
        ...

    def get_blistering_records(self,) -> list[blistering.BlisteringRecord]:
        ...

    def get_coating_records(self,) -> list[coating.CoatingRecord]:
        ...

    def get_compression_records(self,) -> list[compression.CompressionRecord]:
        ...

    def get_dispensing_records(self,) -> list[dispensing.DispensingRecord]:
        # requires both store_packaging reports and processing reports, for confirmation
        records: list[dispensing.DispensingRecord] = []
        for processing_report in chain(self.processing_reports, self.store_packaging_reports):
            if processing_report.data:
                for extracted_data in processing_report.data:
                    for production_activity in extracted_data.activities:

                        if (
                            production_activity.stage is not None
                            and "dispensing" in production_activity.stage.lower()
                        ):
                            shift = utils.to_shift(processing_report.shift)
                            records.append(
                                dispensing.DispensingRecord(
                                    date=FlaggedValue(
                                        utils.to_datetime(processing_report.report_date),
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
                                            production_activity.quantity,
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
                                    received_at=processing_report.received_at,
                                )
                            )

        print(records)
        deduplicated_records = remove_duplicates(records)
        print(deduplicated_records)
        consolidated_records = consolidate_records(deduplicated_records)
        only_valid_records = remove_invalid_records(consolidate_records)
        return consolidated_records
        

    def get_filling_records(self,) -> list[filling.FillingRecord]:
        ...

    def get_granulation_records(self,) -> list[granulation.GranulationRecord]:
        ...

    def get_overprinting_records(self,) -> list[overprinting.OverprintingRecord]:
        ...

    def get_packaging_records(self,) -> list[packaging.PackagingRecord]:
        ...

    def get_sifting_records(self,) -> list[sifting.SiftingRecord]:
            ...
