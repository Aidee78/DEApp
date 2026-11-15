"""Structured parser output."""

from dataclasses import dataclass, field
from typing import TypeAlias

FieldValue: TypeAlias = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class ProductionActivity:
    stage: str | None = None
    product_name: str | None = None
    batch_no: str | None = None
    quantity: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    idle_time: str | None = None
    status: str | None = None
    challenges: str | None = None
    action_taken_remarks: str | None = None
    extra_fields: dict[str, FieldValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExtractedData:
    """Parent class for data extracted from emails.
    """
    production_line: str
    personnels_responsible: list[str]
    activities: tuple[ProductionActivity, ...]

@dataclass(frozen=True, slots=True)
class IpqcReportExtractedData(ExtractedData):
    """Data extracted from the IPQC Daily Report.
    """

@dataclass(frozen=True, slots=True)
class PackagingReportExtractedData(ExtractedData):
    """Data extracted from the Daily Packaging Report.
    """

@dataclass(frozen=True, slots=True)
class PackagingStoreIpqcReportExtractedData(ExtractedData):
    """Data extracted from the Beta-Lactam Packaging / Store IPQC Area Day Report.
    """

@dataclass(frozen=True, slots=True)
class ProcessingReportExtractedData(ExtractedData):
    """Data extracted from the Daily Processing Report.
    """

@dataclass(frozen=True, slots=True)
class MaintenanceReportExtractedData():
    """Data extracted from the Maintenance Report.
    """
    shift: str
    date: str
    report: str
