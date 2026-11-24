# src/deapp/__main__.py

"""DEApp command-line entry point."""

import logging

from deapp.application.exceptions import ApplicationError
from deapp.config.settings import load_settings
from deapp.logging.logger import log_unexpected_exception, setup_logging


logger = logging.getLogger(__name__)


def main() -> int:
    """Start the application and return its process exit code."""
    try:
        setup_logging()
    except ApplicationError as error:
        logger.error(
            "DEApp could not initialize logging (%s).",
            type(error).__name__,
        )
        return 1

    try:
        settings = load_settings()
        setup_logging(settings.log_file, settings.log_level)
    except ApplicationError as error:
        logger.error("DEApp startup failed: %s", error)
        return 1
    except Exception as error:
        log_unexpected_exception(logger, error)
        return 1

    logger.info("DEApp started.")

    try:
        # Import at runtime so startup failures reach the same error boundary.
        from deapp.application.runner import run_application

        result = run_application()
    except ApplicationError as error:
        logger.error("DEApp stopped with an application error: %s", error)
        logger.info("DEApp stopped.")
        return 1
    except Exception as error:
        log_unexpected_exception(logger, error)
        logger.info("DEApp stopped.")
        return 1

    logger.info(
        "DEApp completed for %s through %s.",
        result.start_date,
        result.end_date,
    )
    logger.info("DEApp stopped successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
