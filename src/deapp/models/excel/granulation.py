from dataclasses import dataclass
from datetime import datetime, time

@dataclass(frozen=True, slots=True)
class GranulationRecord:
    date: datetime
    line: str
    product: str
    batch_number: str
    officer: str
    start_time: time
    stop_time: time
    idle_time: time
    coarse_kg: float
    powder_kg: float
    status: str
    remarks: str
    