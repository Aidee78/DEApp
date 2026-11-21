"""Structured parser output."""
from datetime import datetime
from dataclasses import dataclass, field
from typing import TypeAlias

FieldValue: TypeAlias = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class ProductionActivity:
    stage: str | None = None
    product_name: str | None = None
    batch_no: str | None = None
    no: str | None = None
    no_of_cartons: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    idle_time: str | None = None
    mc_no: str | None = None
    waste: str | None = None
    status: str | None = None
    challenges: str | None = None
    action_taken_remarks: str | None = None
    extra_fields: dict[str, FieldValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExtractedData:
    """Parent class for data extracted from emails.
    """
    production_line: str | None
    personnels_responsible: str | None
    activities: list[ProductionActivity]


@dataclass(frozen=True, slots=True)
class ReportExtractedData:
    """Parent class for the reports.
    """
    date_received: str | None
    report_date: str | None
    shift: str | None
    data: list[ExtractedData] | None
    received_at: datetime
