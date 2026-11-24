"""Tests for the command-line application's final error boundary."""

from datetime import date
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

import deapp.__main__ as entrypoint
from deapp.application import runner
from deapp.application.exceptions import ApplicationError


@pytest.fixture
def configured_entrypoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip filesystem logging setup while exercising main's control flow."""
    monkeypatch.setattr(entrypoint, "setup_logging", lambda *args: None)
    monkeypatch.setattr(
        entrypoint,
        "load_settings",
        lambda: SimpleNamespace(log_file=Path("deapp.log"), log_level="INFO"),
    )


def test_main_returns_success_and_logs_completion(
    configured_entrypoint: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Successful workflow results are logged and return exit code zero."""
    monkeypatch.setattr(
        runner,
        "run_application",
        lambda: SimpleNamespace(
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 2),
        ),
        raising=False,
    )
    caplog.set_level(logging.INFO, logger=entrypoint.__name__)

    assert entrypoint.main() == 0
    assert "DEApp completed" in caplog.text


def test_main_handles_expected_application_error(
    configured_entrypoint: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Expected failures are reported without escaping the CLI boundary."""
    def fail_workflow() -> None:
        raise ApplicationError("Workflow could not continue safely.")

    monkeypatch.setattr(runner, "run_application", fail_workflow, raising=False)
    caplog.set_level(logging.ERROR, logger=entrypoint.__name__)

    assert entrypoint.main() == 1
    assert "Workflow could not continue safely." in caplog.text


def test_main_omits_unexpected_exception_text_from_logs(
    configured_entrypoint: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Unexpected exception messages can contain private response data."""
    def fail_workflow() -> None:
        raise RuntimeError("private email response contents")

    monkeypatch.setattr(runner, "run_application", fail_workflow, raising=False)
    caplog.set_level(logging.ERROR, logger=entrypoint.__name__)

    assert entrypoint.main() == 1
    assert "RuntimeError" in caplog.text
    assert "Failure location" in caplog.text
    assert "private email response contents" not in caplog.text
