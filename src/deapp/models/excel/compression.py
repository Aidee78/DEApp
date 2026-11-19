from dataclasses import dataclass
from datetime import datetime, time

@dataclass(frozen=True, slots=True)
class Compression:
    date: datetime
    line: str
    product: str
    batch_number: str
    officer: str
    start_time: time
    stop_time: time
    idle_time: time
    quantity_kg: float
    quantity_tabs: float
    status: str
    remarks: str
    