from dataclasses import dataclass
from datetime import datetime, time

@dataclass(frozen=True, slots=True)
class Packaging:
    date: datetime
    line: str
    product: str
    batch_number: str
    start_time: time
    stop_time: time
    idle_time: time
    number_of_cartons: float
    officer: str
    status: str
    remarks: str
    challenges: str