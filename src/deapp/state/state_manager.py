"""Read and write DEApp's last successful processing date."""

import json
import os
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile


class StateError(Exception):
    """Raised when the saved execution state cannot be read or written."""


def read_last_successful_date(state_file: Path) -> date | None:
    """Read the last successful date, or return None if no date is saved.

    A missing file or an empty JSON object means that no successful run has
    been recorded. Invalid JSON, an invalid schema, an invalid date, or an
    unreadable file raises StateError instead of silently resetting state.
    """
    try:
        contents = state_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as error:
        raise StateError(f"Could not read state file: {state_file}") from error

    try:
        state = json.loads(contents)
    except json.JSONDecodeError as error:
        raise StateError(f"State file is not valid JSON: {state_file}") from error

    if not isinstance(state, dict):
        raise StateError(f"State file must contain a JSON object: {state_file}")

    # The starter data/state.json file contains {}, which means no run yet.
    if not state:
        return None

    stored_date = state.get("last_successful_date")

    if not isinstance(stored_date, str):
        raise StateError(
            f"State file must contain a string 'last_successful_date': {state_file}"
        )

    try:
        parsed_date = date.fromisoformat(stored_date) # we are usind date for now not the datetime object

    except ValueError as error:
        raise StateError(
            f"State file contains an invalid last_successful_date: {state_file}"
        ) from error

    if parsed_date.isoformat() != stored_date:
        raise StateError(
            f"State file date must use YYYY-MM-DD format: {state_file}"
        )
        # this would me the date was stored as YYYY-DD-MM

    return parsed_date


def write_last_successful_date(state_file: Path, successful_date: date) -> None:
    """Atomically save the date of the last successful processing run."""
    state_file.parent.mkdir(parents=True, exist_ok=True)

    contents = json.dumps(
        {"last_successful_date": successful_date.isoformat()},
        indent=2,
    ) + "\n"

    temporary_file: Path | None = None

    # Writing directly to state.json could destroy the existing state before the new state is
    #  fully written. For example, the file could be truncated and then the process interrupted, 
    # leaving malformed JSON.

    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=state_file.parent,
            prefix=f".{state_file.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_file = Path(file.name)
            file.write(contents)
            file.flush()
            os.fsync(file.fileno())

        # The temporary file is in the same directory, so replacement stays
        # on the same filesystem and avoids exposing a partially written file.
        temporary_file.replace(state_file)

    except OSError as error:
        if temporary_file is not None:
            try:
                temporary_file.unlink(missing_ok=True)
            except OSError as cleanup_error:
                raise StateError(
                    f"Could not write state file or remove its temporary file: "
                    f"{state_file}"
                ) from cleanup_error

        raise StateError(f"Could not write state file: {state_file}") from error