"""Manually run DEApp's Zoho-to-Excel flow against a Dropbox test workbook."""

import argparse
from datetime import date
import os
from pathlib import Path
import re
import sys
import tempfile
import zipfile

import requests

from deapp.application.exceptions import (
    ApplicationError,
    ConfigurationError,
    ExcelWriteError,
    WorkflowError,
)
from deapp.config.environment import (
    load_zoho_mail_api_base,
    load_zoho_oauth_settings,
)
from deapp.config.secret_store import load_environment
from deapp.config.settings import load_settings
from deapp.models.extracted_data import ReportExtractedData
from deapp.parsers.report_parser import parse_production_activities
from deapp.services.dropbox.client import DropboxClient
from deapp.services.excel.converter import Converter
from deapp.services.excel_writer.writer import ExcelManager
from deapp.services.zoho.authentication import ZohoAuthenticator
from deapp.services.zoho.mail_client import ZohoMailClient
from deapp.services.zoho.selection import get_daily_messages_by_subject


PROJECT_ROOT = Path(__file__).resolve().parents[2]

# These sheet and table names match the mappings in the existing
# tests/integration/test_app.py and ExcelManager writer methods.
RECORD_WRITERS = (
    ("blending", "write_blending_record", "BLENDING", "Table7"),
    ("blistering", "write_blistering_record", "BLISTERING", "Table20"),
    ("coating", "write_coating_record", "COATING", "Table715"),
    ("compression", "write_compression_record", "COMPRESSION", "Table16"),
    ("dispensing", "write_dispensing_record", "DISPENSING", "Table5"),
    ("filling", "write_filling_record", "FILLING", "Table18"),
    ("granulation", "write_granulation_record", "GRANULATION", "Table13"),
    ("overprinting", "write_overprinting_record", "OVERPRINTING", "Table21"),
    ("packaging", "write_packaging_record", "PACKAGING", "Table17"),
    ("sifting", "write_sifting_record", "SIFTING", "Table6"),
)


def parse_iso_date(value: str) -> date:
    """Parse the required processing date supplied on the command line."""
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Date must use YYYY-MM-DD format."
        ) from error


def require_test_path(path: str | None) -> str:
    """Require a configured Dropbox path with a test/testing path component."""
    if not path:
        raise ConfigurationError(
            "Set dropbox.test_workbook_path in config/config.toml."
        )

    has_test_component = any(
        re.search(r"(?<![a-z])test(?:ing)?(?![a-z])", component, re.IGNORECASE)
        for component in path.strip("/").split("/")
    )
    if not has_test_component:
        raise ConfigurationError(
            "The Dropbox test path must contain a folder named with "
            "'test' or 'testing'."
        )

    return path


def fetch_and_convert_records(
    processing_date: date,
) -> dict[str, list[object]]:
    """Retrieve, parse, and convert Zoho messages using DEApp services."""
    zoho_settings = load_zoho_oauth_settings()
    if not zoho_settings.refresh_token:
        raise ConfigurationError(
            "Zoho authorization is missing; run scripts/authorize_zoho.py."
        )

    parsed_reports: dict[str, list[ReportExtractedData]] = {
        "ipqc report": [],
        "packaging report": [],
        "processing report": [],
        "store packaging report": [],
    }

    # The authenticator and mail client share a session that closes here.
    with requests.Session() as session:
        authenticator = ZohoAuthenticator(zoho_settings, session=session)
        mail_client = ZohoMailClient(
            authenticator=authenticator,
            api_base_url=load_zoho_mail_api_base(),
            session=session,
            timeout_seconds=zoho_settings.timeout_seconds,
        )

        account_id = mail_client.get_account_id()

        messages_by_type = get_daily_messages_by_subject(
            mail_client=mail_client,
            account_id=account_id,
            processing_date=processing_date,
        )

        selected_count = sum(
            len(messages) for messages in messages_by_type.values()
        )
        if selected_count == 0:
            raise WorkflowError(
                f"No target Zoho messages were found for {processing_date}."
            )

        for type_name, messages in messages_by_type.items():
            for message in messages:
                if message.received_at is None:
                    raise WorkflowError(
                        "A selected Zoho message has no received timestamp."
                    )

                report = parse_production_activities(
                    message.content,
                    subject=message.subject,
                    received_at=message.received_at,
                )
                if not report.data:
                    raise WorkflowError(
                        f"DEApp found no report tables in a {type_name} message."
                    )
                parsed_reports[type_name].append(report)

    converter = Converter(
        ipqc_reports=parsed_reports["ipqc report"],
        packaging_reports=parsed_reports["packaging report"],
        processing_reports=parsed_reports["processing report"],
        store_packaging_reports=parsed_reports["store packaging report"],
    )

    records_by_type: dict[str, list[object]] = {
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

    if sum(len(records) for records in records_by_type.values()) == 0:
        raise WorkflowError(
            f"DEApp produced no Excel records for {processing_date}."
        )

    return records_by_type


def validate_local_workbook(path: Path) -> None:
    """Check XLSX integrity and verify DEApp's expected sheets and tables."""
    if not path.is_file() or path.stat().st_size == 0:
        raise ExcelWriteError("The local workbook is missing or empty.")

    if not zipfile.is_zipfile(path):
        raise ExcelWriteError("The local workbook is not a valid XLSX file.")

    with zipfile.ZipFile(path) as workbook_archive:
        members = set(workbook_archive.namelist())
        required_members = {"[Content_Types].xml", "xl/workbook.xml"}
        if not required_members.issubset(members):
            raise ExcelWriteError(
                "The local workbook is missing required XLSX components."
            )

        damaged_member = workbook_archive.testzip()
        if damaged_member is not None:
            raise ExcelWriteError(
                "The local workbook contains a damaged XLSX component."
            )

    # Reopen through Excel and check the structures used by the writers.
    try:
        with ExcelManager(path) as excel:
            excel.save_progress = False
            for _, _, sheet_name, table_name in RECORD_WRITERS:
                sheet = excel.workbook.sheets[sheet_name]
                _ = sheet.tables[table_name]
    except ExcelWriteError:
        raise
    except Exception as error:
        raise ExcelWriteError(
            "Excel could not verify the workbook's expected sheets and tables."
        ) from error


def confirm_upload(remote_path: str, processing_date: date) -> bool:
    """Require interactive confirmation of the exact test target and date."""
    if not sys.stdin.isatty():
        raise ConfigurationError(
            "Run this test from an interactive terminal to confirm the upload."
        )

    expected = f"UPLOAD {remote_path} FOR {processing_date.isoformat()}"
    print(f"Dropbox test workbook: {remote_path}")
    print(
        "This run writes records into that workbook. Repeating a date can "
        "append duplicate rows; reset the test workbook before rerunning."
    )
    print("The local workbook is validated before upload.")
    print("Enter the confirmation text below. Surrounding quotes are optional:")
    print(expected)
    try:
        answer = input("> ").strip()
    except EOFError:
        return False

    # The previous prompt displayed Python-style quotes, so accept a copied
    # confirmation with one matching pair of surrounding quotes.
    if (
        len(answer) >= 2
        and answer[0] == answer[-1]
        and answer[0] in {"'", '"'}
    ):
        answer = answer[1:-1].strip()

    return answer == expected


def run() -> int:
    """Run the test-only Dropbox transaction."""
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument(
        "--date",
        required=True,
        type=parse_iso_date,
        help="Zoho processing date in YYYY-MM-DD format.",
    )
    args = argument_parser.parse_args()

    load_environment()

    settings = load_settings(PROJECT_ROOT / "config" / "config.toml")
    remote_path = require_test_path(settings.dropbox_test_workbook_path)

    # fetch_and_convert_records asks Zoho for the available account ID and
    # uses that ID to retrieve messages; no account ID is needed from .env.
    records_by_type = fetch_and_convert_records(args.date)
    record_count = sum(len(records) for records in records_by_type.values())
    print(f"DEApp prepared {record_count} records for {args.date}.")

    if not confirm_upload(remote_path, args.date):
        print("Cancelled; nothing was downloaded or uploaded.")
        return 2

    # test_mode=True never selects the production workbook path.
    with DropboxClient.from_settings(settings, test_mode=True) as dropbox:
        with tempfile.TemporaryDirectory(prefix="deapp-dropbox-test-") as folder:
            local_workbook = Path(folder) / "workbook.xlsx"

            snapshot = dropbox.download_workbook(local_workbook)
            validate_local_workbook(local_workbook)

            with ExcelManager(local_workbook) as excel:
                for record_type, writer_name, _, _ in RECORD_WRITERS:
                    writer = getattr(excel, writer_name)
                    for record in records_by_type[record_type]:
                        writer(record)

            # Upload is reached only if Excel saved and this validation passes.
            validate_local_workbook(local_workbook)

            # The Dropbox client rejects the upload if the remote revision changed.
            uploaded_revision = dropbox.upload_workbook(
                local_workbook,
                snapshot,
            )

    print("Dropbox test workbook updated successfully.")
    print(f"Uploaded revision: {uploaded_revision}")
    print("The test runner did not update DEApp's successful-run state.")
    return 0


def main() -> int:
    """Print expected application failures without exposing secrets or email data."""
    try:
        return run()
    except (ApplicationError, OSError, zipfile.BadZipFile) as error:
        print(f"DEApp Dropbox test failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
