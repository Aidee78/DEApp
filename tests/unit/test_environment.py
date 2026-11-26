"""Tests for environment-based secrets."""

from unittest.mock import patch

import pytest

from deapp.application.exceptions import ConfigurationError
from deapp.config.environment import load_secrets, load_zoho_oauth_settings


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


def test_zoho_oauth_settings_load_tokens_from_keyring() -> None:
    with patch(
        "deapp.config.environment.keyring.get_password",
        side_effect=["saved-refresh", "saved-client-secret"],
    ) as get_password:
        settings = load_zoho_oauth_settings(
            environ={
                "ZOHO_CLIENT_ID": "test-client",
                "ZOHO_ACCOUNTS_SERVER": "https://accounts.zoho.eu",
                "ZOHO_MAIL_API_BASE": "https://mail.zoho.eu/api",
            }
        )

    assert settings.client_id == "test-client"
    assert settings.refresh_token == "saved-refresh"
    assert settings.client_secret == "saved-client-secret"
    assert settings.accounts_server == "https://accounts.zoho.eu"
    assert get_password.call_count == 2


def test_legacy_zoho_tokens_are_not_loaded_from_environment() -> None:
    with patch(
        "deapp.config.environment.keyring.get_password",
        side_effect=[None, None],
    ):
        settings = load_zoho_oauth_settings(
            environ={
                "ZOHO_CLIENT_ID": "test-client",
                "ZOHO_CLIENT_SECRET": "legacy-secret",
                "ZOHO_REFRESH_TOKEN": "legacy-refresh",
                "ZOHO_AUTH_CODE": "old-code",
            }
        )

    assert settings.client_secret is None
    assert settings.refresh_token is None
