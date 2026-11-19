"""Opt-in live test of parsing selected Zoho messages for one date."""

from datetime import date
import os

import pytest

from deapp.config.environment import (
    load_zoho_mail_api_base,
    load_zoho_oauth_settings,
)
from deapp.config.secret_store import load_environment
from deapp.parsers.report_parser import parse_production_activities
from deapp.services.zoho.authentication import ZohoAuthenticator
from deapp.services.zoho.mail_client import ZohoMailClient
from deapp.services.zoho.selection import get_daily_messages_by_subject


def test_parser_on_zoho_messages_for_configured_date() -> None:
    """Select and parse Zoho messages received on a configured date."""
    load_environment()

    settings = load_zoho_oauth_settings()
    if not settings.refresh_token:
        pytest.fail(
            "Set ZOHO_REFRESH_TOKEN for the test mailbox. "
            "This test will not consume ZOHO_AUTH_CODE."
        )

    account_id = os.environ.get("ZOHO_TEST_ACCOUNT_ID", "").strip()
    search_date_text = os.environ.get("ZOHO_TEST_DATE", "").strip()

    if not account_id:
        pytest.fail("Set ZOHO_TEST_ACCOUNT_ID to the test mailbox account ID.")
    if not search_date_text:
        pytest.fail("Set ZOHO_TEST_DATE in YYYY-MM-DD format.")

    try:
        search_date = date.fromisoformat(search_date_text)
    except ValueError:
        pytest.fail("ZOHO_TEST_DATE must use YYYY-MM-DD format.")

    mail_client = ZohoMailClient(
        authenticator=ZohoAuthenticator(settings),
        api_base_url=load_zoho_mail_api_base(),
        timeout_seconds=settings.timeout_seconds,
    )

    actual_account_id = mail_client.get_account_id(
        preferred_account_id=account_id,
    )
    assert actual_account_id == account_id

    grouped_messages = get_daily_messages_by_subject(
        mail_client=mail_client,
        account_id=actual_account_id,
        processing_date=search_date,
    )

    selected_count = sum(
        len(messages)
        for messages in grouped_messages.values()
    )

    
    assert selected_count > 0, (
        f"No target messages were selected for {search_date}. "
        "Choose a date known to contain target mail."
    )

    parsed_counts = {
        type_name: 0
        for type_name in grouped_messages
    }
    failures: list[str] = []

    for type_name, messages in grouped_messages.items():
        for message in messages:
            try:
                parsed = parse_production_activities(
                    message.content,
                    subject=message.subject,
                    received_at=message.received_at,
                )
                print(message.subject)
                print(parsed)
            except Exception as error:
                failures.append(
                    f"{type_name}, message {message.message_id}: "
                    f"{type(error).__name__}: {error}"
                )
                continue

            if not parsed.data:
                failures.append(
                    f"{type_name}, message {message.message_id}: "
                    "parser returned no report tables"
                )
                continue

            if not any(report.activities for report in parsed.data):
                failures.append(
                    f"{type_name}, message {message.message_id}: "
                    "parser found tables but no activity rows"
                )
                continue

            parsed_counts[type_name] += 1

    print(f"Zoho parser results for {search_date}:")
    for type_name, messages in grouped_messages.items():
        print(
            f"  {type_name}: "
            f"{parsed_counts[type_name]} parsed / {len(messages)} selected"
        )

    assert not failures, "Parser failures:\n" + "\n".join(failures)
