from dataclasses import dataclass
from datetime import datetime, time

@dataclass(frozen=True, slots=True)
class BlisteringRecord:
    date: datetime
    machine: str
    product: str
    batch_number: str
    officer: str
    start_time: time
    stop_time: time
    idle_time: time
    output: float
    status: str
    remarks: str
    challenges: str