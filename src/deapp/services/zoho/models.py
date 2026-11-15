"""Typed data returned by the Zoho Mail service."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ZohoMessage:
    """Metadata and content for one Zoho Mail message.

    The raw metadata is retained so later parsing work can use fields
    without making the Mail client responsible for business rules.
    """

    uri: str |None
    fromAddress: str | None
    message_id: str
    folder_id: str 
    sender: str | None
    summary: str | None
    status2: str | None
    status: str | None
    subject: str | None
    received_at: datetime | None
    content: str
    raw_metadata: dict[str, object]


    # all_messages is a list containing:
    # {
    # "URI": "https://mail.zoho.com/api/accounts/123456789/folders/9000000000905/messages/9000000019029",
    # "hasAttachment": 0,
    # "fromAddress": "rebecca@zylker.com",
    # "folderId": 9000000000905,
    # "messageId": 9000000019029,
    # "sender": "Maria Daniel",
    # "summary": "It is extremely important for us to focus on",
    # "status2": "reply",
    # "sentDateInGMT": 1270171976000,
    # "size": 540,
    # "status": "read",
    # "priority": 3,
    # "threadCount": 0,
    # "flagid": 2,
    # "subject": "Marketing Strategy",
    # "threadId": 1,
    # "receivedtime": 1425388373920
    # }
