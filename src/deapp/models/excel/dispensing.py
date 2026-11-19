from dataclasses import dataclass
from datetime import datetime, time

@dataclass(frozen=True, slots=True)
class DispensingRecord:
    date: datetime | None
    line: str | None
    shift: str | None
    product: str | None
    batch_number: str | None
    quantity_kg: float | None
    dispensing_room: str | None
    officer: str | None
    start_time: time | None
    stop_time: time | None
    status: str | None
    remarks: str | None
    