# src/deapp/__main__.py

"""DEApp command-line entry point."""

import sys

from deapp.application.runner import run_application
from deapp.application.exceptions import ApplicationError


def main() -> int:
    """Start the application and return its process exit code."""
    try:
        result = run_application()
    except ApplicationError as error:
        print(f"DEApp failed: {error}", file=sys.stderr)
        return 1

    print(
        f"DEApp completed for {result.start_date} through {result.end_date}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())