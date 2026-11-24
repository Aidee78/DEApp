"""Central logging setup and safe reporting of unexpected exceptions."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import traceback

from deapp.application.exceptions import LoggingError


DEFAULT_LOG_FILE = Path(__file__).resolve().parents[3] / "logs" / "deapp.log"
MAX_LOG_BYTES = 2 * 1024 * 1024
LOG_BACKUP_COUNT = 5
_HANDLER_MARKER = "_deapp_logging_handler"
_CONFIG_MARKER = "_deapp_logging_configuration"


def setup_logging(
    log_file: Path | None = None,
    log_level: str = "INFO",
) -> None:
    """Configure console and rotating file output once for the current process."""
    normalized_level = log_level.upper()
    level = logging.getLevelName(normalized_level)
    if not isinstance(level, int):
        raise LoggingError("The configured application log level is invalid.")

    target = DEFAULT_LOG_FILE if log_file is None else Path(log_file)
    config_key = (str(target.resolve()), level)
    root_logger = logging.getLogger()

    if getattr(root_logger, _CONFIG_MARKER, None) == config_key:
        return

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            target,
            maxBytes=MAX_LOG_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
    except OSError as error:
        raise LoggingError("Could not initialize the application log file.") from error

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    setattr(file_handler, _HANDLER_MARKER, True)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    setattr(console_handler, _HANDLER_MARKER, True)

    for handler in tuple(root_logger.handlers):
        if getattr(handler, _HANDLER_MARKER, False):
            root_logger.removeHandler(handler)
            handler.close()

    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    setattr(root_logger, _CONFIG_MARKER, config_key)


def log_unexpected_exception(
    logger: logging.Logger,
    error: Exception,
) -> None:
    """Log an unexpected exception's type and source locations without its text."""
    logger.error(
        "DEApp stopped after an unexpected error (%s).",
        type(error).__name__,
    )

    cause = error.__cause__ or error.__context__
    if cause is not None and cause is not error:
        logger.error("Underlying error type: %s.", type(cause).__name__)

    for frame in traceback.extract_tb(error.__traceback__):
        logger.error(
            "Failure location: %s:%s in %s.",
            frame.filename,
            frame.lineno,
            frame.name,
        )
