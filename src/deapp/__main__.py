"""DEApp command-line entry point."""

import sys

from deapp.application.runner import prepare_execution
from deapp.state.state_manager import StateError


def main() -> int:
    """Resolve and display the requested processing period."""
    try:
        start_date, end_date = prepare_execution()
    except (StateError, ValueError) as error:
        print(f"DEApp startup error: {error}", file=sys.stderr)
        return 2

    print(
        "Resolved processing date range: "
        f"{start_date.isoformat()} through {end_date.isoformat()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
    # This is equivalent to calling sys.exit(main()); sys.exit
    # () raises SystemExit internally. Using raise SystemExit
    # (...) makes that behavior explicit.