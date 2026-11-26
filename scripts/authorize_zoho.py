"""Authorize this Windows user for Zoho Mail using OAuth PKCE."""

from dataclasses import replace
from getpass import getpass
import os
import secrets
import webbrowser

import keyring
from keyring.errors import KeyringError

from deapp.application.exceptions import ConfigurationError, InputError
from deapp.config.environment import load_zoho_oauth_settings
from deapp.config.secret_store import load_environment, remove_secret
from deapp.services.zoho.authentication import (
    KEYRING_SERVICE,
    ZOHO_CLIENT_SECRET_CREDENTIAL,
    ZohoAuthenticationError,
    ZohoAuthenticator,
    ZohoOAuthSettings,
    zoho_credential_username,
)
from deapp.services.zoho.oauth_flow import (
    authorization_code_from_callback,
    build_authorization_url,
    create_pkce_pair,
    validate_redirect_uri,
)


LEGACY_SECRET_NAMES = (
    "ZOHO_CLIENT_SECRET",
    "ZOHO_AUTH_CODE",
    "ZOHO_REFRESH_TOKEN",
)


def main() -> int:
    """Run interactive authorization and securely save Zoho credentials."""
    try:
        load_environment()
        settings = load_zoho_oauth_settings()
        validate_redirect_uri(settings.redirect_uri)
        settings = _configure_optional_client_secret(settings)

        code_verifier, code_challenge = create_pkce_pair()
        state = secrets.token_urlsafe(32)
        authorization_url = build_authorization_url(
            accounts_server=settings.accounts_server,
            client_id=settings.client_id,
            redirect_uri=settings.redirect_uri,
            code_challenge=code_challenge,
            state=state,
        )

        print("Opening Zoho authorization in your browser.")
        try:
            browser_opened = webbrowser.open(
                authorization_url,
                new=1,
                autoraise=True,
            )
        except webbrowser.Error:
            browser_opened = False
        if not browser_opened:
            print("Open this Zoho authorization URL:")
            print(authorization_url)
        print(
            "After approving access, paste the full URL from the browser's "
            "redirect page below. The input is hidden."
        )
        callback_url = getpass("Redirect URL: ").strip()
        code = authorization_code_from_callback(
            callback_url,
            redirect_uri=settings.redirect_uri,
            expected_state=state,
        )

        authenticator = ZohoAuthenticator(settings)
        authenticator.exchange_authorization_code(code, code_verifier)
    except (
        ConfigurationError,
        InputError,
        ZohoAuthenticationError,
        KeyringError,
        ValueError,
    ) as error:
        print(f"Zoho authorization failed: {error}")
        return 1

    failed_removals = _remove_legacy_environment_secrets()
    if failed_removals:
        print(
            "Zoho authorization succeeded, but these legacy .env entries "
            "could not be removed: "
            + ", ".join(failed_removals)
        )
    else:
        print(
            "Zoho authorization saved in Windows Credential Manager. "
            "Legacy Zoho token and secret entries were removed from .env."
        )
    return 0


def _configure_optional_client_secret(
    settings: ZohoOAuthSettings,
) -> ZohoOAuthSettings:
    """Offer to move a legacy secret or enter one without echoing it.

    Zoho's desktop PKCE guidance treats native apps as public clients, while
    its token endpoint documentation still lists client_secret as required.
    Keeping this value optional supports either Zoho registration behavior
    without embedding a secret in DEApp or writing one to .env.
    """
    credential_name = zoho_credential_username(
        ZOHO_CLIENT_SECRET_CREDENTIAL,
        settings.client_id,
    )
    if settings.client_secret:
        use_stored = input(
            "Use the Zoho client secret stored in Windows Credential "
            "Manager? [Y/n]: "
        ).strip().casefold()
        if use_stored not in {"n", "no"}:
            return settings

        client_secret = getpass(
            "Replacement Zoho client secret (press Enter if not required): "
        ).strip()
        if client_secret:
            keyring.set_password(
                KEYRING_SERVICE,
                credential_name,
                client_secret,
            )
        else:
            keyring.delete_password(KEYRING_SERVICE, credential_name)
        return replace(settings, client_secret=client_secret or None)

    legacy_secret = os.environ.get("ZOHO_CLIENT_SECRET", "").strip()
    if legacy_secret:
        use_legacy = input(
            "A legacy ZOHO_CLIENT_SECRET is present in .env. Move it to "
            "Windows Credential Manager and use it? [y/N]: "
        ).strip().casefold() in {"y", "yes"}
        if use_legacy:
            client_secret = legacy_secret
        else:
            client_secret = getpass(
                "Zoho client secret (press Enter if not required): "
            ).strip()
    else:
        client_secret = getpass(
            "Zoho client secret (press Enter if not required): "
        ).strip()

    if client_secret:
        keyring.set_password(
            KEYRING_SERVICE,
            credential_name,
            client_secret,
        )
    return replace(settings, client_secret=client_secret or None)


def _remove_legacy_environment_secrets() -> list[str]:
    """Remove migrated OAuth secrets from the project .env file."""
    failures: list[str] = []
    for name in LEGACY_SECRET_NAMES:
        try:
            remove_secret(name)
        except OSError:
            failures.append(name)
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
