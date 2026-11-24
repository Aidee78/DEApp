"""Opt-in live test of Zoho parsing, blending conversion, and Excel writing."""

from datetime import date
import os
from pathlib import Path
from typing import Any

import pytest
import xlwings as xw

from deapp.config.environment import (
    load_zoho_mail_api_base,
    load_zoho_oauth_settings,
)
from deapp.config.secret_store import load_environment
from deapp.models.excel.blending import BlendingRecord
from deapp.models.extracted_data import ReportExtractedData
from deapp.parsers.report_parser import parse_production_activities
from deapp.services.excel.converter import Converter
from deapp.services.excel_writer.writer import ExcelManager
from deapp.services.zoho.authentication import ZohoAuthenticator
from deapp.services.zoho.mail_client import ZohoMailClient
from deapp.services.zoho.selection import get_daily_messages_by_subject


ROOT_WORKBOOK = (
    Path(__file__).resolve().parents[2]
    / "BL_-_Processing___Packaging_Report_-_renamed_tables.xlsx"
)


def _next_blending_row(worksheet: xw.Sheet, table: Any) -> int:
    """Predict where the writer starts before it appends blending records."""
    body = table.data_body_range
    if body is None:
        return table.range.last_cell.row + 1

    last_row = body.last_cell.row
    values = worksheet.range(f"A{last_row}:M{last_row}").options(ndim=1).value
    return last_row if all(value is None for value in values) else last_row + 1


def _assert_root_workbook_is_closed(workbook_path: Path) -> None:
    """Avoid ExcelManager closing a workbook the user already has open."""
    target = workbook_path.resolve()
    for app in xw.apps:
        for workbook in list(app.books):
            if Path(workbook.fullname).resolve() == target:
                pytest.fail(
                    "Close the root workbook in Excel before running this test."
                )


def test_live_zoho_blending_records_are_written_to_root_workbook() -> None:
    """Retrieve, parse, convert, and write Zoho blending records to Excel."""
    load_environment()
    if os.environ.get("DEAPP_ZOHO_EXCEL_INTEGRATION") != "1":
        pytest.skip("Set DEAPP_ZOHO_EXCEL_INTEGRATION=1 to enable live Excel writes.")

    settings = load_zoho_oauth_settings()

    if not settings.refresh_token:
        pytest.fail("Set ZOHO_REFRESH_TOKEN for the test mailbox.")

    account_id = os.environ.get("ZOHO_TEST_ACCOUNT_ID", "").strip()
    date_text = os.environ.get("ZOHO_TEST_DATE", "").strip()

    if not account_id:
        pytest.fail("Set ZOHO_TEST_ACCOUNT_ID to the test mailbox account ID.")
    if not date_text:
        pytest.fail("Set ZOHO_TEST_DATE in YYYY-MM-DD format.")
    if not ROOT_WORKBOOK.is_file():
        pytest.fail(f"Root test workbook not found: {ROOT_WORKBOOK}")

    _assert_root_workbook_is_closed(ROOT_WORKBOOK)

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
                f"Parser found no report tables for a {type_name} message."
            )
            parsed_reports[type_name].append(report)

    converter = Converter(
        ipqc_reports=parsed_reports["ipqc report"],
        packaging_reports=[],
        processing_reports=parsed_reports["processing report"],
        store_packaging_reports=[],
    )
    blending_records: list[BlendingRecord] = converter.get_blending_records()

    assert blending_records, (
        f"No blending records were produced for {processing_date}."
    )

    with ExcelManager(ROOT_WORKBOOK) as excel:
        worksheet = excel.workbook.sheets["BLENDING"]
        table = worksheet.tables["Table7"]
        first_write_row = _next_blending_row(worksheet, table)

        for record in blending_records:
            print(record)
            excel.write_blending_record(record)

        last_write_row = first_write_row + len(blending_records) - 1
        written_rows = worksheet.range(
            f"A{first_write_row}:M{last_write_row}"
        ).options(ndim=2).value

        assert len(written_rows) == len(blending_records)
