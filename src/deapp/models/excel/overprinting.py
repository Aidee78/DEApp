from dataclasses import dataclass, field
from datetime import datetime, time

from deapp.models.excel.field import FlaggedValue


@dataclass(frozen=True, slots=True)
class OverprintingRecord:
    """One overprinting activity with per-field consistency flags."""

    date: FlaggedValue[datetime]
    line: FlaggedValue[str]
    product: FlaggedValue[str]
    batch_number: FlaggedValue[str]
    start_time: FlaggedValue[time]
    stop_time: FlaggedValue[time]
    idle_time: FlaggedValue[time]
    number_of_cartons: FlaggedValue[float]
    officer: FlaggedValue[str]
    status: FlaggedValue[str]
    remarks: FlaggedValue[str]
    challenges: FlaggedValue[str]
    received_at: datetime
    shift: FlaggedValue[str | None] = field(
        default_factory=lambda: FlaggedValue[str | None](None),
    )
