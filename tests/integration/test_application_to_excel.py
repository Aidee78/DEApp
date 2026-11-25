"""Opt-in live test of Zoho parsing, conversion, and Excel writing."""

from datetime import date
import os
from pathlib import Path

import pytest
import xlwings as xw

from deapp.config.environment import (
    load_zoho_mail_api_base,
    load_zoho_oauth_settings,
)
from deapp.config.secret_store import load_environment
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

_DEFAULT_ROOT_WORKBOOK = (
    Path(__file__).resolve().parents[2]
    / "BL_-_Processing___Packaging_Report_-_renamed_tables.xlsx"
)
ROOT_WORKBOOK = Path(
    os.environ.get("DEAPP_EXCEL_TEST_WORKBOOK", str(_DEFAULT_ROOT_WORKBOOK))
).resolve()

RECORD_WRITERS = (
    ("blending", "write_blending_record", "BLENDING", "Table7", "M"),
    ("blistering", "write_blistering_record", "BLISTERING", "Table20", "L"),
    ("coating", "write_coating_record", "COATING", "Table715", "K"),
    ("compression", "write_compression_record", "COMPRESSION", "Table16", "K"),
    ("dispensing", "write_dispensing_record", "DISPENSING", "Table5", "L"),
    ("filling", "write_filling_record", "FILLING", "Table18", "N"),
    ("granulation", "write_granulation_record", "GRANULATION", "Table13", "K"),
    (
        "overprinting",
        "write_overprinting_record",
        "OVERPRINTING",
        "Table21",
        "O",
    ),
    ("packaging", "write_packaging_record", "PACKAGING", "Table17", "L"),
    ("sifting", "write_sifting_record", "SIFTING", "Table6", "L"),
)


def _next_write_row(
    worksheet: xw.Sheet,
    table_name: str,
    last_column: str,
) -> int:
    """Predict the first row ExcelManager will use for this record family."""
    table = worksheet.tables[table_name]
    body = table.data_body_range
    if body is None:
        return table.range.last_cell.row + 1

    last_row = body.last_cell.row
    values = worksheet.range(f"A{last_row}:{last_column}{last_row}").options(
        ndim=1,
    ).value
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


def test_live_zoho_records_are_written_to_root_workbook() -> None:
    """Retrieve Zoho reports, convert every record family, and write them."""
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
    selected_count = sum(len(messages) for messages in messages_by_type.values())
    assert selected_count, f"No target messages found for {processing_date}."

    parsed_reports: dict[str, list[ReportExtractedData]] = {
        type_name: [] for type_name in messages_by_type
    }
    for type_name, messages in messages_by_type.items():
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
        packaging_reports=parsed_reports["packaging report"],
        processing_reports=parsed_reports["processing report"],
        store_packaging_reports=parsed_reports["store packaging report"],
    )
    records_by_type = {
        "blending": converter.get_blending_records(),
        "blistering": converter.get_blistering_records(),
        "coating": converter.get_coating_records(),
        "compression": converter.get_compression_records(),
        "dispensing": converter.get_dispensing_records(),
        "filling": converter.get_filling_records(),
        "granulation": converter.get_granulation_records(),
        "overprinting": converter.get_overprinting_records(),
        "packaging": converter.get_packaging_records(),
        "sifting": converter.get_sifting_records(),
    }

    record_filter = os.environ.get(
        "DEAPP_EXCEL_TEST_RECORD_TYPE", ""
    ).strip().lower()

    if record_filter and record_filter not in records_by_type:
        pytest.fail(f"Unknown record type: {record_filter}")
    if record_filter and not records_by_type[record_filter]:
        pytest.fail(f"No {record_filter} records were produced.")
    

    total_records = sum(len(records) for records in records_by_type.values())
    assert total_records, f"No Excel records were produced for {processing_date}."

    with ExcelManager(ROOT_WORKBOOK) as excel:
        for (
            record_type,
            writer_name,
            sheet_name,
            table_name,
            last_column,
        ) in RECORD_WRITERS:
            if record_filter and record_type != record_filter:
                continue    

            records = records_by_type[record_type]
            if not records:
                continue

            worksheet = excel.workbook.sheets[sheet_name]
            first_write_row = _next_write_row(
                worksheet,
                table_name,
                last_column,
            )
            writer = getattr(excel, writer_name)

            for record in records:
                writer(record)

            last_write_row = first_write_row + len(records) - 1
            written_rows = worksheet.range(
                f"A{first_write_row}:{last_column}{last_write_row}"
            ).options(ndim=2).value
            assert len(written_rows) == len(records), (
                f"Expected {len(records)} {record_type} rows to be written; "
                f"found {len(written_rows)}."
            )
            assert all(
                any(value is not None for value in row)
                for row in written_rows
            ), f"At least one written {record_type} row is empty."
