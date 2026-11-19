"""
Converts the ReportExtractedData from each email gotten per day to excel records
"""

from itertools import chain
from collections.abc import Iterable
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
from deapp.services.excel import utils


T = TypeVar("T")


def remove_duplicate_records(records: Iterable[T]) -> list[T]:
    """Return unique records in their original order, keeping the first copy."""
    unique_records: list[T] = []

    for record in records:
        if record not in unique_records:
            unique_records.append(record)

    return unique_records

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
        a_list: list = []
        for processing_report in chain(self.processing_reports, self.store_packaging_reports):
            processing_report.data
            processing_report.date_received
            processing_report.report_date
            processing_report.shift

            if processing_report.data:
                for extracted_data in processing_report.data:
                    extracted_data.production_line
                    extracted_data.personnels_responsible

                    for production_activity in extracted_data.activities:

                        if production_activity.stage is not None and ("dispensing" in production_activity.stage.lower()):
                            a_list.append(
                                dispensing.DispensingRecord(
                                    date = utils.to_datetime(processing_report.report_date),
                                    line = utils.to_production_line(extracted_data.production_line),
                                    shift = utils.to_shift(processing_report.shift),
                                    product = utils.to_resolve_product(production_activity.product_name, production_activity.batch_no),
                                    batch_number = utils.to_batch_number(production_activity.batch_no),
                                    quantity_kg = utils.to_extract_kg_quantity(production_activity.quantity),
                                    dispensing_room = utils.to_dispensing_room(production_activity.stage),
                                    officer = utils.to_personnel_names(extracted_data.personnels_responsible),
                                    start_time = utils._extract_single_time(production_activity.start_time,  utils.to_shift(processing_report.shift)),
                                    stop_time = utils._extract_single_time(production_activity.end_time,  utils.to_shift(processing_report.shift)),
                                    status = utils.to_valid_string(production_activity.status),
                                    remarks = f"{utils.to_valid_string(production_activity.challenges)} || {utils.to_valid_string(production_activity.action_taken_remarks)}"
                                )
                            )

        return remove_duplicate_records(a_list)
        

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