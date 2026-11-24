"""Load and validate environment-based secrets and Zoho settings."""

import math
import os
from collections.abc import Mapping
from urllib.parse import urlsplit

from deapp.application.exceptions import ConfigurationError
from deapp.config.secret_store import load_environment
from deapp.services.zoho.authentication import ZohoOAuthSettings


def _environment(
    environ: Mapping[str, str] | None,
) -> Mapping[str, str]:
    """Return the supplied environment or load the project's .env file."""
    if environ is not None:
        return environ

    try:
        load_environment()
    except OSError as error:
        raise ConfigurationError(
            "Could not read the project environment file."
        ) from error
    return os.environ


def load_secrets(
    required_names: tuple[str, ...],
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return required secrets or report missing variable names."""
    source = _environment(environ)

    missing = [
        name
        for name in required_names
        if not source.get(name, "").strip()
    ]
    if missing:
        raise ConfigurationError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    return {name: source[name].strip() for name in required_names}


def load_zoho_oauth_settings(
    environ: Mapping[str, str] | None = None,
) -> ZohoOAuthSettings:
    """Load Zoho OAuth settings for either initial setup or normal runs.

    A refresh token takes precedence at runtime. An authorization code is
    used only when no refresh token is configured.
    """
    source = _environment(environ)
    secrets = load_secrets(
        ("ZOHO_CLIENT_ID", "ZOHO_CLIENT_SECRET"),
        environ=source,
    )

    refresh_token = source.get("ZOHO_REFRESH_TOKEN", "").strip() or None
    authorization_code = (
        source.get("ZOHO_AUTH_CODE", "").strip() or None
    )

    if refresh_token is None and authorization_code is None:
        raise ConfigurationError(
            "Configure ZOHO_REFRESH_TOKEN or ZOHO_AUTH_CODE."
        )

    accounts_server = source.get(
        "ZOHO_ACCOUNTS_SERVER",
        "https://accounts.zoho.com",
    ).strip()
    redirect_uri = source.get("ZOHO_REDIRECT_URI", "").strip()

    try:
        timeout_seconds = float(source.get("ZOHO_TIMEOUT_SECONDS", "30"))
    except ValueError as exc:
        raise ConfigurationError(
            "Invalid setting: ZOHO_TIMEOUT_SECONDS"
        ) from exc

    if not _is_https_url(accounts_server):
        raise ConfigurationError("Invalid setting: ZOHO_ACCOUNTS_SERVER")
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ConfigurationError("Invalid setting: ZOHO_TIMEOUT_SECONDS")

    return ZohoOAuthSettings(
        accounts_server=accounts_server.rstrip("/"),
        client_id=secrets["ZOHO_CLIENT_ID"],
        client_secret=secrets["ZOHO_CLIENT_SECRET"],
        refresh_token=refresh_token,
        authorization_code=authorization_code,
        redirect_uri=redirect_uri,
        timeout_seconds=timeout_seconds,
    )


def load_zoho_mail_api_base(
    environ: Mapping[str, str] | None = None,
) -> str:
    """Return the configured regional Zoho Mail API base URL."""
    source = _environment(environ)
    api_base = source.get(
        "ZOHO_MAIL_API_BASE",
        "https://mail.zoho.com/api",
    ).strip()

    if not _is_https_url(api_base):
        raise ConfigurationError("Invalid setting: ZOHO_MAIL_API_BASE")

    return api_base.rstrip("/")


def load_zoho_account_id(
    environ: Mapping[str, str] | None = None,
) -> str | None:
    """Return a configured account ID, if the user supplied one."""
    source = _environment(environ)
    value = source.get("ZOHO_ACCOUNT_ID", "").strip()
    return value or None


def _is_https_url(value: str) -> bool:
    """Check that a configured service URL has an HTTPS scheme and host."""
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return parsed.scheme == "https" and bool(parsed.netloc)
