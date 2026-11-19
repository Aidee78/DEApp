"""Opt-in live test of subject selection against a Zoho mailbox."""

from datetime import date
import os

import pytest

from deapp.config.environment import (
    load_zoho_mail_api_base,
    load_zoho_oauth_settings,
)
from deapp.config.secret_store import load_environment
from deapp.services.zoho.authentication import ZohoAuthenticator
from deapp.services.zoho.mail_client import ZohoMailClient
from deapp.services.zoho.selection import get_daily_messages_by_subject


def test_selector_against_zoho_for_configured_date() -> None:
    """Search Zoho for one date and report messages selected by type."""
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

    expected_types = {
        "ipqc report",
        "packaging report",
        "processing report",
        "store packaging report",
    }
    assert set(grouped_messages) == expected_types
    assert all(isinstance(messages, list) for messages in grouped_messages.values())

    selected_count = sum(
        len(messages)
        for messages in grouped_messages.values()
    )

    # Use a date known to contain at least one target message. Remove this
    # assertion if you also want to test dates where no target mail exists.
    assert selected_count > 0, (
        f"No target subjects were selected for {search_date}. "
        "Check the date and subject rules."
    )

    print(f"Selected messages for {search_date}:")
    for type_name, messages in grouped_messages.items():
        print(f"  {type_name}: {len(messages)}")

    # Subjects help review classification, so print them only when explicitly
    # requested. Message bodies are never printed.

    for type_name, messages in grouped_messages.items():
        for message in messages:
            print(f"    [{type_name}] {message.subject}")