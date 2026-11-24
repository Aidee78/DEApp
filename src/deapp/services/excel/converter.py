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

from deapp.services.excel import (
    to_dispensing_record,
    to_granulation_record,
    to_blending_record,
    to_compression_record,
    to_coating_record,
    to_sifting_record,
    to_filling_record,
    to_blistering_record,
    to_packaging_record,
    to_overprinting_record,
)

from deapp.models.extracted_data import ReportExtractedData
from deapp.models.excel.field import FlaggedValue
from deapp.services.excel import utils
from deapp.services.excel.reconciliation import consolidate_records, remove_completely_empty_records, remove_duplicates


T = TypeVar("T")


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

        self.ipqc_report_name = "ipqc_reports"
        self.packaging_report_name = "packaging_reports"
        self.processing_report_name = "processing_reports"
        self.store_packaging_report_name = "store_packaging_reports"

    def get_blending_records(self,) -> list[blending.BlendingRecord]:
        records: list[blending.BlendingRecord] = []
        records.extend(
            to_blending_record.get_blending_records_from_processing_report(
                self.processing_reports,
                self.processing_report_name,
            ),
        )
        records.extend(
            to_blending_record.get_blending_records_from_ipqc_report(
                self.ipqc_reports,
                self.processing_report_name,
            ),
        )
        
        
        deduplicated_records = remove_duplicates(records)
        
        consolidated_records = consolidate_records(deduplicated_records)
        
        only_valid_records = remove_completely_empty_records(consolidated_records)
        return only_valid_records

    def get_blistering_records(self,) -> list[blistering.BlisteringRecord]:
        records: list[blistering.BlisteringRecord] = []
                
        records.extend(
            to_blistering_record.get_blistering_records_from_ipqc_report(
                self.ipqc_reports,
                self.ipqc_report_name
            ),
        )
        
        
        deduplicated_records = remove_duplicates(records)
        
        consolidated_records = consolidate_records(deduplicated_records)
        
        only_valid_records = remove_completely_empty_records(consolidated_records)
        return only_valid_records

    def get_coating_records(self,) -> list[coating.CoatingRecord]:
        records: list[coating.CoatingRecord] = []

        records.extend(
            to_coating_record.get_coating_records_from_processing_report(
                self.processing_reports,
                self.processing_report_name,
            ),
        )
        records.extend(
            to_coating_record.get_coating_records_from_ipqc_report(
                self.ipqc_reports,
                self.ipqc_report_name,
            ),
        )
        
        
        deduplicated_records = remove_duplicates(records)
        
        consolidated_records = consolidate_records(deduplicated_records)
        
        only_valid_records = remove_completely_empty_records(consolidated_records)
        return only_valid_records

    def get_compression_records(self,) -> list[compression.CompressionRecord]:
        records: list[compression.CompressionRecord] = []
        records.extend(
            to_compression_record.get_compression_records_from_processing_report(
                self.processing_reports,
                self.processing_report_name,
            ),
        )
        records.extend(
            to_compression_record.get_compression_records_from_ipqc_report(
                self.ipqc_reports,
                self.ipqc_report_name,
            ),
        )
        
        
        deduplicated_records = remove_duplicates(records)
        
        consolidated_records = consolidate_records(deduplicated_records)
        
        only_valid_records = remove_completely_empty_records(consolidated_records)
        return only_valid_records

    def get_dispensing_records(self,) -> list[dispensing.DispensingRecord]:
        # requires both store_packaging reports and processing reports, for confirmation
        records: list[dispensing.DispensingRecord] = []

        records.extend(
            to_dispensing_record.get_dispensing_records_from_processing_report(
                self.processing_reports,
                self.processing_report_name,
            )
        )

        records.extend(
            to_dispensing_record.get_dispensing_records_from_store_packaging_report(
                self.store_packaging_reports,
                self.store_packaging_report_name
            )
        )


        deduplicated_records = remove_duplicates(records)

        consolidated_records = consolidate_records(deduplicated_records)

        only_valid_records = remove_completely_empty_records(consolidated_records)
        return only_valid_records
        

    def get_filling_records(self,) -> list[filling.FillingRecord]:
        records: list[filling.FillingRecord] = []
        
        records.extend(
            to_filling_record.get_filling_records_from_ipqc_report(
                self.ipqc_reports,
                self.ipqc_report_name,
            ),
        )
        
        
        deduplicated_records = remove_duplicates(records)
        
        consolidated_records = consolidate_records(deduplicated_records)
        
        only_valid_records = remove_completely_empty_records(consolidated_records)
        return only_valid_records

    def get_granulation_records(self,) -> list[granulation.GranulationRecord]:
        records: list[granulation.GranulationRecord] = []
        records.extend(
            to_granulation_record.get_granulation_records_from_processing_report(
                self.processing_reports,
                self.processing_report_name,
            ),
        )
        records.extend(
            to_granulation_record.get_granulation_records_from_ipqc_report(
                self.ipqc_reports,
                self.ipqc_report_name,
            ),
        )

        
        deduplicated_records = remove_duplicates(records)
        
        consolidated_records = consolidate_records(deduplicated_records)
        
        only_valid_records = remove_completely_empty_records(consolidated_records)
        return only_valid_records

    def get_overprinting_records(self,) -> list[overprinting.OverprintingRecord]:
        records: list[overprinting.OverprintingRecord] = []
        
        records.extend(
            to_overprinting_record.get_overprinting_records_from_packaging_report(
                self.packaging_reports,
                self.packaging_report_name,
            ),
        )
        
        records.extend(
            to_overprinting_record.get_overprinting_records_from_store_packaging_report(
                self.store_packaging_reports,
                self.store_packaging_report_name,
            ),
        )
        
        
        deduplicated_records = remove_duplicates(records)
        
        consolidated_records = consolidate_records(deduplicated_records)
        
        only_valid_records = remove_completely_empty_records(consolidated_records)
        return only_valid_records

    def get_packaging_records(self,) -> list[packaging.PackagingRecord]:
        records: list[packaging.PackagingRecord] = []
        
        records.extend(
            to_packaging_record.get_packaging_records_from_packaging_report(
                self.packaging_reports,
                self.packaging_report_name,
            ),
        )

        records.extend(
            to_packaging_record.get_packaging_records_from_store_packaging_report(
                self.store_packaging_reports,
                self.store_packaging_report_name,
            ),
        )
        
        
        deduplicated_records = remove_duplicates(records)
        
        consolidated_records = consolidate_records(deduplicated_records)
        
        only_valid_records = remove_completely_empty_records(consolidated_records)
        return only_valid_records

    def get_sifting_records(self,) -> list[sifting.SiftingRecord]:
        records: list[sifting.SiftingRecord] = []
        records.extend(
            to_sifting_record.get_sifting_records_from_processing_report(
                self.processing_reports,
                self.processing_report_name,
            ),
        )
        records.extend(
            to_sifting_record.get_sifting_records_from_ipqc_report(
                self.ipqc_reports,
                self.ipqc_report_name,
            ),
        )

        
        deduplicated_records = remove_duplicates(records)
        
        consolidated_records = consolidate_records(deduplicated_records)
        
        only_valid_records = remove_completely_empty_records(consolidated_records)
        return only_valid_records
