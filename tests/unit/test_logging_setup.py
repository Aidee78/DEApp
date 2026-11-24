"""Tests for centralized rotating logs and safe unexpected-error reporting."""

import logging
from logging.handlers import RotatingFileHandler
from collections.abc import Iterator
from pathlib import Path

import pytest

from deapp.application.exceptions import LoggingError
from deapp.logging.logger import (
    LOG_BACKUP_COUNT,
    MAX_LOG_BYTES,
    log_unexpected_exception,
    setup_logging,
)


@pytest.fixture
def clean_deapp_handlers() -> Iterator[logging.Logger]:
    """Remove only handlers created by DEApp after each logging test."""
    root_logger = logging.getLogger()
    original_level = root_logger.level
    yield root_logger

    for handler in tuple(root_logger.handlers):
        if getattr(handler, "_deapp_logging_handler", False):
            root_logger.removeHandler(handler)
            handler.close()

    if hasattr(root_logger, "_deapp_logging_configuration"):
        delattr(root_logger, "_deapp_logging_configuration")
    root_logger.setLevel(original_level)


def test_setup_logging_adds_console_and_rotating_file_handlers(
    tmp_path: Path,
    clean_deapp_handlers: logging.Logger,
) -> None:
    """The configured file rotates at the approved limit and keeps five backups."""
    log_path = tmp_path / "logs" / "deapp.log"

    setup_logging(log_path, "DEBUG")
    setup_logging(log_path, "DEBUG")

    root_logger = clean_deapp_handlers
    handlers = [
        handler
        for handler in root_logger.handlers
        if getattr(handler, "_deapp_logging_handler", False)
    ]
    file_handlers = [
        handler for handler in handlers if isinstance(handler, RotatingFileHandler)
    ]

    assert len(handlers) == 2
    assert len(file_handlers) == 1
    assert file_handlers[0].maxBytes == MAX_LOG_BYTES == 2 * 1024 * 1024
    assert file_handlers[0].backupCount == LOG_BACKUP_COUNT == 5

    logging.getLogger("deapp.logging.test").info("safe test event")
    for handler in handlers:
        handler.flush()
    assert "safe test event" in log_path.read_text(encoding="utf-8")


def test_setup_logging_rejects_unknown_level(tmp_path: Path) -> None:
    """An invalid level is raised as an application-level logging failure."""
    with pytest.raises(LoggingError, match="log level"):
        setup_logging(tmp_path / "deapp.log", "VERBOSE")


def test_unexpected_error_logging_omits_arbitrary_exception_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Unexpected exception details include type and location, not its message."""
    logger = logging.getLogger("deapp.logging.test.unexpected")

    try:
        raise RuntimeError("private response payload")
    except RuntimeError as error:
        log_unexpected_exception(logger, error)

    assert "RuntimeError" in caplog.text
    assert "Failure location" in caplog.text
    assert "private response payload" not in caplog.text
