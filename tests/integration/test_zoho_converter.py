"""Opt-in live test of Zoho mail parsing and dispensing conversion."""

from datetime import date
import os

import pytest

from deapp.config.environment import (
    load_zoho_mail_api_base,
    load_zoho_oauth_settings,
)
from deapp.config.secret_store import load_environment
from deapp.models.extracted_data import ReportExtractedData
from deapp.parsers.report_parser import parse_production_activities
from deapp.services.excel.converter import Converter
from deapp.services.zoho.authentication import ZohoAuthenticator
from deapp.services.zoho.mail_client import ZohoMailClient
from deapp.services.zoho.selection import get_daily_messages_by_subject


def test_live_zoho_messages_through_parser_and_converter() -> None:
    """Retrieve, parse, and convert real Zoho reports for one configured date."""
    load_environment()
    settings = load_zoho_oauth_settings()

    if not settings.refresh_token:
        pytest.fail("Run scripts/authorize_zoho.py for the Zoho test mailbox.")

    account_id = os.environ.get("ZOHO_TEST_ACCOUNT_ID", "").strip()
    date_text = os.environ.get("ZOHO_TEST_DATE", "").strip()

    if not account_id:
        pytest.fail("Set ZOHO_TEST_ACCOUNT_ID to the test mailbox account ID.")
    if not date_text:
        pytest.fail("Set ZOHO_TEST_DATE in YYYY-MM-DD format.")

    try:
        processing_date = date.fromisoformat(date_text)
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

    messages_by_type = get_daily_messages_by_subject(
        mail_client=mail_client,
        account_id=actual_account_id,
        processing_date=processing_date,
    )

    selected_count = sum(len(messages) for messages in messages_by_type.values())
    assert selected_count > 0, f"No target messages found for {processing_date}."

    parsed_reports: dict[str, list[ReportExtractedData]] = {
        type_name: []
        for type_name in messages_by_type
    }

    for type_name, messages in messages_by_type.items():
        for message in messages:
            report = parse_production_activities(
                message.content,
                subject=message.subject,
                received_at=message.received_at,
            )
            print()
            print(report)
            print()
            assert report.data, (
                f"Parser found no report tables in {type_name}: "
                f"{message.subject!r}"
            )
            parsed_reports[type_name].append(report)

    # The current converter method references processing_report while
    # processing store packaging reports, so both groups are needed to run it.
    assert parsed_reports["processing report"], (
        f"No processing reports found for {processing_date}."
    )
    assert parsed_reports["store packaging report"], (
        f"No store packaging reports found for {processing_date}."
    )

    converter = Converter(
        ipqc_reports=parsed_reports["ipqc report"],
        packaging_reports=parsed_reports["packaging report"],
        processing_reports=parsed_reports["processing report"],
        store_packaging_reports=parsed_reports["store packaging report"],
    )

    dispensing_records = converter.get_dispensing_records()

    print(f"Dispensing records returned for {processing_date}:")
    print(f"Count: {len(dispensing_records)}")
    for index, record in enumerate(dispensing_records, start=1):
        print(f"{index}. {record!r}")

    assert isinstance(dispensing_records, list)
