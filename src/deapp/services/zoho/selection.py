"""Group daily Zoho messages by their configured email subject."""

from collections.abc import Mapping
from datetime import date

from deapp.services.zoho.mail_client import ZohoMailClient
from deapp.services.zoho.models import ZohoMessage


def get_daily_messages_by_subject(
    mail_client: ZohoMailClient,
    account_id: str,
    processing_date: date,
    subject_by_type: Mapping[str, str],
) -> dict[str, list[ZohoMessage] | None]:
    """Group messages by exact subject, retaining duplicates.

    Subject matching is exact and case-sensitive. A message type with no
    matching message is returned as None.
    """
    if not subject_by_type:
        raise ValueError("At least one subject rule must be provided.")

    if any(not name.strip() or not subject.strip()
           for name, subject in subject_by_type.items()):
        raise ValueError("Message type names and subjects must be non-empty.")

    if len(set(subject_by_type.values())) != len(subject_by_type):
        raise ValueError("Each message type must have a distinct subject.")

    metadata_rows = mail_client.search_messages(
        account_id=account_id,
        start_date=processing_date,
        end_date=processing_date,
    )

    grouped: dict[str, list[ZohoMessage]] = {
        type_name: []
        for type_name in subject_by_type
    }

    for metadata in metadata_rows:
        subject = metadata.get("subject")
        if not isinstance(subject, str):
            continue

        for type_name, expected_subject in subject_by_type.items():
            if subject == expected_subject:
                grouped[type_name].append(
                    mail_client.get_message(account_id, metadata)
                )
                break

    return {
        type_name: messages or None
        for type_name, messages in grouped.items()
    }