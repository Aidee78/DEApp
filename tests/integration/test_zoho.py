"""Opt-in, read-only checks against a dedicated Zoho test mailbox."""

from datetime import date
import os

import pytest

from deapp.config.secret_store import load_environment
from deapp.config.environment import load_zoho_mail_api_base
from deapp.services.zoho.authentication import ZohoAuthenticator
from deapp.services.zoho.mail_client import ZohoMailClient


def test_zoho_test_mailbox_connection_and_search() -> None:
    """Confirm Zoho auth and message search work for the configured test mailbox."""
    load_environment()

    if os.environ.get("DEAPP_ZOHO_INTEGRATION") != "1":
        pytest.skip("Set DEAPP_ZOHO_INTEGRATION=1 to enable this live test.")

    from deapp.config.environment import load_zoho_oauth_settings

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

    authenticator = ZohoAuthenticator(settings)
    mail_client = ZohoMailClient(
        authenticator=authenticator,
        api_base_url=load_zoho_mail_api_base(),
        timeout_seconds=settings.timeout_seconds,
    )

    actual_account_id = mail_client.get_account_id(
        preferred_account_id=account_id,
    )
    assert actual_account_id == account_id

    messages = mail_client.search_messages(
        account_id=actual_account_id,
        start_date=search_date,
        end_date=search_date,
    )
    assert isinstance(messages, list)