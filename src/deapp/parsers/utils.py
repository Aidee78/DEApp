"""Shared helpers for reading HTML report tables."""

import re
from datetime import date, datetime
from typing import Literal, cast

from bs4 import BeautifulSoup, Comment, Tag
from dateparser.search import search_dates

from deapp.models.extracted_data import ProductionActivity


Shift = Literal["day", "night"]

_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)

_NUMERIC_DATE = re.compile(
    r"(?<!\d)(?P<first>\d{1,2})(?P<separator>[./-])"
    r"(?P<second>\d{1,2})(?P=separator)(?P<year>\d{4})(?!\d)"
)

_SHIFT_CUE = re.compile(
    r"\b(?P<shift>day|night)[\s-]+(?:shift|duty|report)\b",
    re.IGNORECASE,
)

_WEEKDAY_SHIFT_CUE = re.compile(
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
    r"\s+(?P<shift>day|night)\b",
    re.IGNORECASE,
)


def _text_outside_tables(html: str) -> str:
    """Return visible email text outside tables, excluding transport headers."""
    soup = BeautifulSoup(html, "lxml")
    pieces: list[str] = []

    for node in soup.find_all(string=True):
        if isinstance(node, Comment):
            continue
        if node.find_parent(["table", "script", "style"]) is not None:
            continue

        value = str(node).strip()
        if value:
            pieces.append(value)

    text = re.sub(r"\s+", " ", " ".join(pieces)).strip()

    # Saved email HTML contains From/To/Date/Subject before the message body.
    greeting = re.search(r"\bDear\b", text, flags=re.IGNORECASE)
    return text[greeting.start():] if greeting else text


def _normalize_report_date_text(text: str) -> str:
    """Repair date words split by HTML formatting in saved reports."""
    text = text.replace("\ufffd", " ").replace("\u200b", " ").replace("\xa0", " ")
    text = re.sub(
        r"\b(\d{1,2})\s*(?:st|nd|rd|th)\b",
        r"\1",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\b((?:19|20)\d)\s+(\d)\b", r"\1\2", text)

    for month in _MONTHS:
        spaced_month = r"\b" + r"\s*".join(map(re.escape, month)) + r"\b"
        text = re.sub(spaced_month, month, text, flags=re.IGNORECASE)

    return re.sub(r"\s+", " ", text).strip()


def _find_date_candidates(text: str) -> set[date]:
    """Find complete dates, including both interpretations of numeric dates."""
    candidates: set[date] = set()

    matches = search_dates(
        text,
        languages=["en"],
        settings={
            "REQUIRE_PARTS": ["day", "month", "year"],
            "STRICT_PARSING": True,
        },
    )
    for _, parsed in matches or []:
        candidates.add(parsed.date())

    # search_dates may choose only one interpretation of a value such as
    # 03/04/2026. Add both valid day/month interpretations before comparing.
    for match in _NUMERIC_DATE.finditer(text):
        first = int(match.group("first"))
        second = int(match.group("second"))
        year = int(match.group("year"))

        for day, month in ((first, second), (second, first)):
            try:
                candidates.add(date(year, month, day))
            except ValueError:
                continue

    return candidates


def _choose_report_date(
    candidates: set[date],
    received_at: datetime | None,
) -> date | None:
    """Choose a unique date, using mail receipt date to resolve ambiguity."""
    if not candidates:
        return None
    if received_at is None:
        return next(iter(candidates)) if len(candidates) == 1 else None

    received_date = received_at.date()
    distances = {
        candidate: abs((candidate - received_date).days)
        for candidate in candidates
    }
    shortest_distance = min(distances.values())
    closest = [
        candidate
        for candidate, distance in distances.items()
        if distance == shortest_distance
    ]

    return closest[0] if len(closest) == 1 else None


def extract_report_date_and_shift(
    html: str,
    *,
    subject: str | None = None,
    received_at: datetime | None = None,
) -> tuple[date | None, Shift | None]:
    """Extract report date and shift from subject and non-table email text.

    A date must include day, month, and year. If multiple dates are found,
    the one nearest the mail receipt date is selected; a tie returns None.
    Conflicting shift cues also return None.
    """
    outside_text = _text_outside_tables(html)

    # Keep support for saved HTML files that include a Subject header.
    embedded_subject = ""
    if subject is None:
        subject_match = re.search(
            r"\bSubject\s*:\s*(.*?)(?=\bDear\b|$)",
            outside_text,
            flags=re.IGNORECASE,
        )
        embedded_subject = subject_match.group(1) if subject_match else ""

    subject_text = subject if subject is not None else embedded_subject
    date_text = _normalize_report_date_text(f"{subject_text} {outside_text}")
    report_date = _choose_report_date(
        _find_date_candidates(date_text),
        received_at,
    )

    shifts: set[Shift] = set()
    for source in (subject_text, outside_text):
        for pattern in (_SHIFT_CUE, _WEEKDAY_SHIFT_CUE):
            for match in pattern.finditer(source):
                shifts.add(cast(Shift, match.group("shift").casefold()))

    shift = next(iter(shifts)) if len(shifts) == 1 else None
    return report_date, shift


def extract_html_tables(mail_content: str) -> list[Tag]:
    soup = BeautifulSoup(mail_content, "lxml")
    tables = soup.find_all("table")

    if not tables:
        raise ValueError("The email did not contain any HTML tables.")

    return tables


def normalize_report_table(table: Tag) -> list[list[str]]:
    """Convert an HTML table with row and column spans to a rectangular matrix.

    A cell with ``rowspan`` occupies the same logical column in subsequent
    rows. A cell with ``colspan`` occupies multiple logical columns: its text
    is placed in the first column and the remaining covered columns are blank.

    Empty values in the first two columns carry forward from the preceding row,
    preserving the report-table behavior used by the parser.
    """

    def read_span(cell: Tag, attribute: str) -> int:
        """Read a positive span value or explain which attribute is invalid."""
        raw_value = cell.get(attribute, 1)
        try:
            span = int(raw_value)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Invalid {attribute} value in HTML table: {raw_value!r}"
            ) from error

        if span < 1:
            raise ValueError(
                f"HTML table {attribute} must be at least 1; got {span}."
            )
        return span

    html_rows = table.find_all("tr")
    if not html_rows:
        return []

    # Maps each occupied column in the next row to its value and the number
    # of additional rows it remains occupied.
    active_rowspans: dict[int, tuple[str, int]] = {}
    grid_rows: list[dict[int, str]] = []
    column_count = 0

    for html_row in html_rows:
        row: dict[int, str] = {}
        next_rowspans: dict[int, tuple[str, int]] = {}

        # First reserve columns occupied by cells that began in an earlier row.
        for column, (value, remaining_rows) in active_rowspans.items():
            row[column] = value
            if remaining_rows > 1:
                next_rowspans[column] = (value, remaining_rows - 1)

        next_column = 0

        for cell in html_row.find_all(["td", "th"], recursive=False):
            colspan = read_span(cell, "colspan")
            rowspan = read_span(cell, "rowspan")

            # Place this cell in the next contiguous set of unoccupied columns.
            while any(
                column in row
                for column in range(next_column, next_column + colspan)
            ):
                next_column += 1

            value = " ".join(cell.stripped_strings).replace("\n", " ")

            for offset in range(colspan):
                column = next_column + offset

                # Keep a colspan value once, then reserve blank covered columns.
                cell_value = value if offset == 0 else ""
                row[column] = cell_value

                if rowspan > 1:
                    next_rowspans[column] = (cell_value, rowspan - 1)

            next_column += colspan

        if row:
            column_count = max(column_count, max(row) + 1)

        grid_rows.append(row)
        active_rowspans = next_rowspans

    # Fill missing positions so each row has the same number of columns.
    matrix = [
        [row.get(column, "") for column in range(column_count)]
        for row in grid_rows
    ]

    # Preserve the existing rule that blank Stage/Item cells continue the
    # preceding value.
    previous_values: dict[int, str] = {}
    for row in matrix:
        for column, value in enumerate(row):
            if column in (0, 1) and value == "":
                row[column] = previous_values.get(column, "")
            elif value != "":
                previous_values[column] = value

    return matrix


def matrix_to_records(
    matrix: list[list[str]],
) -> list[dict[str, str]]:
    """Convert a matrix to dictionaries, stripping headers and values."""
    if not matrix:
        return []

    print(matrix)
    headers = [header.strip() for header in matrix[0]]

    return [
        {
            header: value.strip()
            for header, value in zip(headers, row, strict=True)
        }
        for row in matrix[1:]
    ]

def record_to_production_activity(
    record: dict[str, str],
    field_by_header: dict[str, str],
) -> ProductionActivity:
    """Map one table row to a ProductionActivity."""
    activity_fields = {
        model_field: record[header]
        for header, model_field in field_by_header.items()
        if header in record
    }

    extra_fields = {
        header: value
        for header, value in record.items()
        if header not in field_by_header
    }

    return ProductionActivity(
        **activity_fields,
        extra_fields=extra_fields,
    )

def extract_line_and_personnel(text: str) -> tuple[str | None, str | None]:
    """Extract the production line and personnel from a heading."""
    text = text.replace("\n", " ").replace("\r", " ")
    text = text.strip()
    text = re.sub(r"^\*\*|\*\*$", "", text)

    match = re.fullmatch(
        r"\s*(?P<line>[^:]+?)\s*:\s*(?P<personnel>.*?)\s*",
        text,
        flags=re.DOTALL,
    )
    if match is None:
        return None, None

    line = re.sub(
        r"\s+LINE\s*$",
        "",
        match.group("line").strip(),
        flags=re.IGNORECASE,
    )
    personnel = match.group("personnel").strip()

    return line, personnel

def get_line_and_personnel(
    table: Tag,
) -> tuple[str | None, str | None]:
    for tag in table.find_all_previous(["p", "table"]):
        if tag.name == "table":
            break

        text = tag.get_text(" ", strip=True)
        if text:
            return extract_line_and_personnel(text)

    return None, None