# src/deapp/application/workflow.py

"""Coordinate a DEApp execution from mail retrieval through state recording."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol, TypeVar

from deapp.models.email import Email
from deapp.models.extracted_data import ExtractedData


T = TypeVar("T")


class MailService(Protocol):
    """Retrieve source messages for a processing period."""

    def fetch_messages(self, start_date: date, end_date: date) -> list[Email]:
        """Fetch messages; implementation depends on confirmed Zoho criteria."""
        ...


class Parser(Protocol):
    """Convert a source message to structured data."""

    def parse(self, message: Email) -> ExtractedData:
        """Parse one message and raise a clear error if it is invalid."""
        ...


class WorkbookService(Protocol):
    """Operate on the local workbook copy."""

    def update(self, workbook_path: Path, records: list[ExtractedData]) -> None:
        """Apply validated records using confirmed workbook rules."""
        ...

    def validate(self, workbook_path: Path) -> None:
        """Raise an error if the resulting workbook is invalid."""
        ...


class DropboxService(Protocol):
    """Transfer the workbook to and from Dropbox."""

    def download_workbook(self, destination: Path) -> None:
        """Download the remote workbook to a local path."""
        ...

    def upload_workbook(self, source: Path) -> None:
        """Upload a validated local workbook."""
        ...


@dataclass(frozen=True)
class RunResult:
    """Summary returned to the caller after a successful run."""

    start_date: date
    end_date: date
    messages_processed: int


@dataclass
class WorkflowDependencies:
    """Services and operations the workflow coordinates."""

    mail: MailService
    parsers: dict[str, Parser]  # Keying/matching rules still need definition.
    dropbox: DropboxService
    workbook: WorkbookService
    state_writer: Callable[[date], None]
    acquire_lock: Callable[[], AbstractContextManager[object]]
    make_working_path: Callable[[], AbstractContextManager[Path]]


def run_workflow(
    start_date: date,
    end_date: date,
    dependencies: WorkflowDependencies,
) -> RunResult:
    """Run all processing steps; advance successful state only after upload."""

    with dependencies.acquire_lock():
        messages = dependencies.mail.fetch_messages(start_date, end_date)

        # TODO: Define missing-message, multiple-match, and duplicate behavior.
        # TODO: Select the parser for each message using confirmed criteria.
        records: list[ExtractedData] = []
        for message in messages:
            parser = select_parser(message, dependencies.parsers)
            records.append(parser.parse(message))

        # TODO: Add agreed cross-record validation before touching the workbook.
        validate_extracted_records(records)

        # The context manager must clean up the local file after success/failure.
        with dependencies.make_working_path() as local_workbook:
            dependencies.dropbox.download_workbook(local_workbook)
            dependencies.workbook.update(local_workbook, records)
            dependencies.workbook.validate(local_workbook)

            # State must not advance unless upload reports success.
            dependencies.dropbox.upload_workbook(local_workbook)
            dependencies.state_writer(end_date)

    return RunResult(
        start_date=start_date,
        end_date=end_date,
        messages_processed=len(messages),
    )


def select_parser(
    message: Email,
    parsers: dict[str, Parser],
) -> Parser:
    """Choose the parser using finalized sender/subject/type identification rules."""
    # TODO: Implement only after the four email identification rules are settled.
    raise NotImplementedError("Email type identification is not implemented")


def validate_extracted_records(records: list[ExtractedData]) -> None:
    """Validate extracted records before workbook modification."""
    # TODO: Implement confirmed required-field and duplicate rules.
    if not records:
        raise ValueError("No records were extracted; handling policy is not defined")