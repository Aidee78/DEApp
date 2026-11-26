"""Opt-in live test of Zoho parsing and sifting record conversion."""

from datetime import date
import os

import pytest

from deapp.config.environment import (
    load_zoho_mail_api_base,
    load_zoho_oauth_settings,
)
from deapp.config.secret_store import load_environment
from deapp.models.excel.sifting import SiftingRecord
from deapp.models.extracted_data import ReportExtractedData
from deapp.parsers.report_parser import parse_production_activities
from deapp.services.excel.converter import Converter
from deapp.services.zoho.authentication import ZohoAuthenticator
from deapp.services.zoho.mail_client import ZohoMailClient
from deapp.services.zoho.selection import get_daily_messages_by_subject


def test_live_zoho_processing_and_ipqc_to_sifting_records() -> None:
    """Retrieve processing and IPQC messages and convert their sifting rows."""
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
    processing_messages = messages_by_type.get("processing report", [])
    ipqc_messages = messages_by_type.get("ipqc report", [])

    assert processing_messages, (
        f"No processing reports found for {processing_date}."
    )
    assert ipqc_messages, f"No IPQC reports found for {processing_date}."

    parsed_reports: dict[str, list[ReportExtractedData]] = {
        "processing report": [],
        "ipqc report": [],
    }
    for type_name, messages in (
        ("processing report", processing_messages),
        ("ipqc report", ipqc_messages),
    ):
        for message in messages:
            report = parse_production_activities(
                message.content,
                subject=message.subject,
                received_at=message.received_at,
            )
            assert report.data, (
                f"Parser found no report tables in {type_name}: "
                f"{message.subject!r}"
            )
            parsed_reports[type_name].append(report)

    converter = Converter(
        ipqc_reports=parsed_reports["ipqc report"],
        packaging_reports=[],
        processing_reports=parsed_reports["processing report"],
        store_packaging_reports=[],
    )
    sifting_records = converter.get_sifting_records()

    print(f"Sifting records returned for {processing_date}:")
    print(f"Count: {len(sifting_records)}")
    for index, record in enumerate(sifting_records, start=1):
        print(f"{index}. {record!r}")

    assert sifting_records, (
        f"No sifting activities were converted for {processing_date}."
    )
    assert all(isinstance(record, SiftingRecord) for record in sifting_records)
