"""DEApp command-line entry point."""

import sys

from deapp.config import load_settings


def main() -> int:
    """Load configuration and report whether application startup can proceed."""
    try:
        settings = load_settings()
    except ValueError as error:
        print(f"DEApp configuration error: {error}", file=sys.stderr)
        return 2

    print(f"{settings.app_name} started successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
    # This is equivalent to calling sys.exit(main()); sys.exit
    # () raises SystemExit internally. Using raise SystemExit
    # (...) makes that behavior explicit.