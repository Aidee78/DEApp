from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Email:
    """A retrieved email in a form the parsers can process."""

    message_id: str
    subject: str
    sender: str
    received_at: datetime
    content: str | None = None