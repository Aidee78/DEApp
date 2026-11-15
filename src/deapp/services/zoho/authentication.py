"""Zoho OAuth authorization-code exchange and access-token management."""

from collections.abc import Callable
from dataclasses import dataclass
import logging
import time
from typing import Protocol

import requests

from deapp.config.secret_store import remove_secret, save_secret


logger = logging.getLogger(__name__)


class ZohoAuthenticationError(RuntimeError):
    """Raised when Zoho cannot provide usable OAuth tokens."""


class TokenResponse(Protocol):
    """Response interface used by the token manager."""

    @property
    def ok(self) -> bool: ...

    @property
    def status_code(self) -> int: ...

    def json(self) -> object: ...


@dataclass(frozen=True, slots=True)
class ZohoOAuthSettings:
    """Zoho OAuth configuration and credentials."""

    accounts_server: str
    client_id: str
    client_secret: str
    refresh_token: str | None = None
    authorization_code: str | None = None
    redirect_uri: str = ""
    timeout_seconds: float = 30.0


@dataclass(frozen=True, slots=True)
class ZohoTokenSet:
    """Tokens returned by an authorization-code exchange."""

    access_token: str
    refresh_token: str
    expires_in: int


class ZohoAuthenticator:
    """Cache access tokens and acquire them through refresh or authorization."""

    def __init__(
        self,
        settings: ZohoOAuthSettings,
        session: requests.Session | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
        expiry_buffer_seconds: int = 300,
    ) -> None:
        if expiry_buffer_seconds < 0:
            raise ValueError("expiry_buffer_seconds cannot be negative.")

        self._settings = settings
        self._session = session or requests.Session()
        self._clock = clock
        self._expiry_buffer_seconds = expiry_buffer_seconds
        self._refresh_token = settings.refresh_token
        self._authorization_code = settings.authorization_code
        self._access_token: str | None = None
        self._expires_at: float | None = None

    def get_access_token(self) -> str:
        """Return a cached token, refresh it, or perform the initial exchange."""
        if (
            self._access_token is not None
            and self._expires_at is not None
            and self._clock()
            < self._expires_at - self._expiry_buffer_seconds
        ):
            return self._access_token

        if self._refresh_token:
            # A failed refresh raises. A one-time code is not a fallback.
            return self._refresh_access_token()

        if self._authorization_code:
            return self.exchange_authorization_code(
                self._authorization_code
            ).access_token

        raise ZohoAuthenticationError(
            "Configure ZOHO_REFRESH_TOKEN or ZOHO_AUTH_CODE."
        )

    def exchange_authorization_code(self, code: str) -> ZohoTokenSet:
        """Exchange a one-time code, save its refresh token, and clear the code."""
        if not code.strip():
            raise ValueError("Authorization code must not be empty.")

        payload = {
            "code": code.strip(),
            "grant_type": "authorization_code",
            "client_id": self._settings.client_id,
            "client_secret": self._settings.client_secret,
        }

        # Server-based OAuth clients require the same redirect URI used during
        # authorization. Some self-client flows do not use a redirect URI.
        if self._settings.redirect_uri:
            payload["redirect_uri"] = self._settings.redirect_uri

        data = self._post_token_request(payload)
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_in = self._parse_expiry(data.get("expires_in"))

        if not isinstance(access_token, str) or not access_token:
            raise ZohoAuthenticationError(
                "Zoho OAuth response did not contain an access token."
            )
        if not isinstance(refresh_token, str) or not refresh_token:
            raise ZohoAuthenticationError(
                "Zoho did not return a refresh token. Ensure offline access "
                "was requested."
            )

        try:
            save_secret("ZOHO_REFRESH_TOKEN", refresh_token)
        except OSError as exc:
            raise ZohoAuthenticationError(
                "Could not persist the Zoho refresh token."
            ) from exc

        self._refresh_token = refresh_token
        self._authorization_code = None

        try:
            remove_secret("ZOHO_AUTH_CODE")
        except OSError:
            # The saved refresh token takes precedence on later runs.
            logger.warning("Could not remove the consumed Zoho auth code.")

        self._cache_access_token(access_token, expires_in)
        logger.info("Zoho authorization-code exchange succeeded.")

        return ZohoTokenSet(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )

    def invalidate_access_token(self) -> None:
        """Clear the cached token so the next call obtains a fresh one."""
        self._access_token = None
        self._expires_at = None

    def _refresh_access_token(self) -> str:
        """Obtain a new access token using the stored refresh token."""
        if not self._refresh_token:
            raise ZohoAuthenticationError("No Zoho refresh token is available.")

        data = self._post_token_request(
            {
                "refresh_token": self._refresh_token,
                "client_id": self._settings.client_id,
                "client_secret": self._settings.client_secret,
                "grant_type": "refresh_token",
            }
        )

        access_token = data.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise ZohoAuthenticationError(
                "Zoho OAuth response did not contain an access token."
            )

        expires_in = self._parse_expiry(data.get("expires_in"))
        self._cache_access_token(access_token, expires_in)
        logger.info("Zoho access token refreshed and cached in memory.")
        return access_token

    def _post_token_request(
        self,
        payload: dict[str, str],
    ) -> dict[str, object]:
        """Send a token request without logging credentials or response data."""
        token_url = (
            f"{self._settings.accounts_server.rstrip('/')}/oauth/v2/token"
        )

        try:
            response: TokenResponse = self._session.post(
                token_url,
                data=payload,
                timeout=self._settings.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise ZohoAuthenticationError(
                "Could not connect to the Zoho OAuth server."
            ) from exc

        if not response.ok:
            raise ZohoAuthenticationError(
                "Zoho OAuth request failed with HTTP status "
                f"{response.status_code}."
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ZohoAuthenticationError(
                "Zoho OAuth returned invalid JSON."
            ) from exc

        if not isinstance(data, dict):
            raise ZohoAuthenticationError(
                "Zoho OAuth returned an unexpected response."
            )

        return data

    @staticmethod
    def _parse_expiry(value: object) -> int:
        """Validate Zoho's access-token lifetime."""
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise ZohoAuthenticationError(
                "Zoho OAuth response contained an invalid token lifetime."
            )

        try:
            lifetime = int(value)
        except ValueError as exc:
            raise ZohoAuthenticationError(
                "Zoho OAuth response contained an invalid token lifetime."
            ) from exc

        if lifetime <= 0:
            raise ZohoAuthenticationError(
                "Zoho OAuth returned a non-positive token lifetime."
            )

        return lifetime

    def _cache_access_token(self, token: str, lifetime: int) -> None:
        """Cache an access token and its monotonic expiration time."""
        self._access_token = token
        self._expires_at = self._clock() + lifetime