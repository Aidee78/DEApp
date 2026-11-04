"""Date parsing and processing-range resolution for DEApp."""

from datetime import date


def parse_iso_date(value: str) -> date:
    """Parse a date in the exact YYYY-MM-DD format."""
    try:
        parsed_date = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(
            f"invalid date {value!r}; expected YYYY-MM-DD"
        ) from error

    if parsed_date.isoformat() != value:
        raise ValueError(
            f"invalid date {value!r}; expected YYYY-MM-DD"
        )

    return parsed_date


def resolve_date_range(
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    last_successful_date: date | None = None,
    today: date | None = None,
) -> tuple[date, date]:
    """Resolve optional date overrides into a validated processing range.

    A missing end date defaults to today. A missing start date defaults to
    the last successful processing date, which is included again for now.
    On a first run without a saved date, the caller must provide a start date.
    """
    current_date = date.today() if today is None else today
    resolved_end = current_date if end_date is None else end_date
    resolved_start = (
        last_successful_date if start_date is None else start_date
    )

    if resolved_start is None:
        raise ValueError(
            "A start date is required when there is no last successful date."
        )

    if resolved_start > resolved_end:
        raise ValueError("The start date must be on or before the end date.")

    return resolved_start, resolved_end