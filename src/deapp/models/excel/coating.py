from dataclasses import dataclass, field
from datetime import datetime, time

from deapp.models.excel.field import FlaggedValue


@dataclass(frozen=True, slots=True)
class CoatingRecord:
    """One coating activity with per-field consistency flags."""

    date: FlaggedValue[datetime | None]
    line: FlaggedValue[str | None]
    product: FlaggedValue[str | None]
    batch_number: FlaggedValue[str | None]
    officer: FlaggedValue[str | None]
    start_time: FlaggedValue[time | None]
    stop_time: FlaggedValue[time | None]
    idle_time: FlaggedValue[time | None]
    quantity_kg: FlaggedValue[float | None]
    quantity_tabs: FlaggedValue[float | None]
    status: FlaggedValue[str | None]
    remarks: FlaggedValue[str | None]
    received_at: datetime
    shift: FlaggedValue[str | None] 
