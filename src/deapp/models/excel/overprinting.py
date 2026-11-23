from dataclasses import dataclass, field
from datetime import datetime, time

from deapp.models.excel.field import FlaggedValue


@dataclass(frozen=True, slots=True)
class OverprintingRecord:
    """One overprinting activity with per-field consistency flags."""

    date: FlaggedValue[datetime | None]
    line: FlaggedValue[str | None]
    product: FlaggedValue[str | None]
    batch_number: FlaggedValue[str | None]
    start_time: FlaggedValue[time | None]
    stop_time: FlaggedValue[time | None]
    idle_time: FlaggedValue[time | None]
    number_of_cartons: FlaggedValue[float | None]
    officer: FlaggedValue[str | None]
    status: FlaggedValue[str | None]
    remarks: FlaggedValue[str | None]
    challenges: FlaggedValue[str | None]
    shift: FlaggedValue[str | None]
    received_at: datetime
    report_type: str | None
