from dataclasses import dataclass
from datetime import datetime, time

@dataclass(frozen=True, slots=True)
class Dispensing:
    date: datetime
    line: str
    product: str
    batch_number: str
    quantity_kg: float
    dispensing_room: str
    officer: str
    start_time: time
    stop_time: time
    status: str
    remarks: str
    