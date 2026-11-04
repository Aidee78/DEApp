"""Prepare an application run's processing date range."""

from collections.abc import Sequence
from datetime import date

from deapp.cli.arguments import parse_arguments
from deapp.config import Settings, load_settings
from deapp.state.state_manager import read_last_successful_date
from deapp.utils.dates import resolve_date_range


def prepare_execution(
    argv: Sequence[str] | None = None,
    *,
    settings: Settings | None = None,
    today: date | None = None,
) -> tuple[date, date]:
    """Parse options and resolve the processing range for this invocation.

    ``settings`` and ``today`` can be supplied by tests to make the function
    independent of the working directory and clock.
    """
    arguments = parse_arguments(argv)
    active_settings = load_settings() if settings is None else settings

    last_successful_date = None
    
    if arguments.start_date is None:
        last_successful_date = read_last_successful_date(
            active_settings.state_file
        )

    return resolve_date_range(
        start_date=arguments.start_date,
        end_date=arguments.end_date,
        last_successful_date=last_successful_date,
        today=today,
    )