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
    to_sifting_record,
)

from deapp.models.extracted_data import ReportExtractedData
from deapp.models.excel.field import FlaggedValue
from deapp.services.excel import utils
from deapp.services.excel.reconciliation import consolidate_records, remove_completely_empty_records


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
        records: list[blending.BlendingRecord] = []
        records.extend(
            to_blending_record.get_blending_records_from_processing_report(
                self.processing_reports,
            ),
        )
        records.extend(
            to_blending_record.get_blending_records_from_ipqc_report(
                self.ipqc_reports,
            ),
        )
        
        print(f"records returned:")
        print(f"Count: {len(records)}")
        print(records)
        
        deduplicated_records = remove_duplicates(records)
        print(f"deduplicated_records returned:")
        print(f"Count: {len(deduplicated_records)}")
        print(deduplicated_records)
        
        consolidated_records = consolidate_records(deduplicated_records)
        print(f"consolidated_records returned:")
        print(f"Count: {len(consolidated_records)}")
        print(consolidated_records)
        
        only_valid_records = remove_completely_empty_records(consolidated_records)
        return only_valid_records

    def get_blistering_records(self,) -> list[blistering.BlisteringRecord]:
        ...

    def get_coating_records(self,) -> list[coating.CoatingRecord]:
        ...

    def get_compression_records(self,) -> list[compression.CompressionRecord]:
        records: list[compression.CompressionRecord] = []
        records.extend(
            to_compression_record.get_compression_records_from_processing_report(
                self.processing_reports,
            ),
        )
        records.extend(
            to_compression_record.get_compression_records_from_ipqc_report(
                self.ipqc_reports,
            ),
        )
        
        print(f"records returned:")
        print(f"Count: {len(records)}")
        print(records)
        
        deduplicated_records = remove_duplicates(records)
        print(f"deduplicated_records returned:")
        print(f"Count: {len(deduplicated_records)}")
        print(deduplicated_records)
        
        consolidated_records = consolidate_records(deduplicated_records)
        print(f"consolidated_records returned:")
        print(f"Count: {len(consolidated_records)}")
        print(consolidated_records)
        
        only_valid_records = remove_completely_empty_records(consolidated_records)
        return only_valid_records

    def get_dispensing_records(self,) -> list[dispensing.DispensingRecord]:
        # requires both store_packaging reports and processing reports, for confirmation
        records: list[dispensing.DispensingRecord] = []

        records.extend(to_dispensing_record.get_dispensing_records_from_processing_report(self.processing_reports))
        records.extend(to_dispensing_record.get_dispensing_records_from_store_packaging_report(self.store_packaging_reports))

        print(f"records returned:")
        print(f"Count: {len(records)}")
        print(records)

        deduplicated_records = remove_duplicates(records)
        print(f"deduplicated_records returned:")
        print(f"Count: {len(deduplicated_records)}")
        print(deduplicated_records)

        consolidated_records = consolidate_records(deduplicated_records)
        print(f"consolidated_records returned:")
        print(f"Count: {len(consolidated_records)}")
        print(consolidated_records)

        only_valid_records = remove_completely_empty_records(consolidated_records)
        return only_valid_records
        

    def get_filling_records(self,) -> list[filling.FillingRecord]:
        ...

    def get_granulation_records(self,) -> list[granulation.GranulationRecord]:
        records: list[granulation.GranulationRecord] = []
        records.extend(
            to_granulation_record.get_granulation_records_from_processing_report(
                self.processing_reports,
            ),
        )
        records.extend(
            to_granulation_record.get_granulation_records_from_ipqc_report(
                self.ipqc_reports,
            ),
        )

        print(f"records returned:")
        print(f"Count: {len(records)}")
        print(records)
        
        deduplicated_records = remove_duplicates(records)
        print(f"deduplicated_records returned:")
        print(f"Count: {len(deduplicated_records)}")
        print(deduplicated_records)
        
        consolidated_records = consolidate_records(deduplicated_records)
        print(f"consolidated_records returned:")
        print(f"Count: {len(consolidated_records)}")
        print(consolidated_records)
        
        only_valid_records = remove_completely_empty_records(consolidated_records)
        return only_valid_records

    def get_overprinting_records(self,) -> list[overprinting.OverprintingRecord]:
        ...

    def get_packaging_records(self,) -> list[packaging.PackagingRecord]:
        ...

    def get_sifting_records(self,) -> list[sifting.SiftingRecord]:
        records: list[sifting.SiftingRecord] = []
        records.extend(
            to_sifting_record.get_sifting_records_from_processing_report(
                self.processing_reports,
            ),
        )
        records.extend(
            to_sifting_record.get_sifting_records_from_ipqc_report(
                self.ipqc_reports,
            ),
        )

        print(f"records returned:")
        print(f"Count: {len(records)}")
        print(records)
        
        deduplicated_records = remove_duplicates(records)
        print(f"deduplicated_records returned:")
        print(f"Count: {len(deduplicated_records)}")
        print(deduplicated_records)
        
        consolidated_records = consolidate_records(deduplicated_records)
        print(f"consolidated_records returned:")
        print(f"Count: {len(consolidated_records)}")
        print(consolidated_records)
        
        only_valid_records = remove_completely_empty_records(consolidated_records)
        return only_valid_records
