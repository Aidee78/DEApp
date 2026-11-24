"""Tests for environment-based secrets."""

import pytest

from deapp.application.exceptions import ConfigurationError
from deapp.config.environment import load_secrets


def test_load_secrets_returns_requested_values() -> None:
    secrets = load_secrets(
        ("CLIENT_ID", "CLIENT_SECRET"),
        environ={
            "CLIENT_ID": " example-id ",
            "CLIENT_SECRET": " example-secret ",
            "UNUSED": "ignored",
        },
    )

    assert secrets == {
        "CLIENT_ID": "example-id",
        "CLIENT_SECRET": "example-secret",
    }


def test_load_secrets_reports_missing_names_without_values() -> None:
    with pytest.raises(ConfigurationError) as error:
        load_secrets(
            ("CLIENT_ID", "CLIENT_SECRET"),
            environ={"CLIENT_ID": "present"},
        )

    assert "CLIENT_SECRET" in str(error.value)
    assert "present" not in str(error.value)


def test_load_secrets_rejects_blank_values() -> None:
    with pytest.raises(ConfigurationError, match="CLIENT_ID"):
        load_secrets(("CLIENT_ID",), environ={"CLIENT_ID": "   "})
