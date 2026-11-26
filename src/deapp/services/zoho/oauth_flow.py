"""Pure helpers for the interactive Zoho OAuth PKCE flow."""

import base64
import hashlib
import hmac
import secrets
from urllib.parse import parse_qs, urlencode, urlsplit

from deapp.application.exceptions import ConfigurationError, InputError

ZOHO_MAIL_SCOPE = "ZohoMail.accounts.READ,ZohoMail.messages.READ"

def create_pkce_pair() -> tuple[str, str]:
    """Create a random PKCE verifier and its S256 challenge."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def validate_redirect_uri(redirect_uri: str) -> None:
    """Require an HTTP(S) callback URI registered with the Zoho client."""
    try:
        parsed = urlsplit(redirect_uri)
        valid_port = parsed.port is None or 1 <= parsed.port <= 65535
    except ValueError:
        valid_port = False
        parsed = urlsplit("")

    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or not valid_port
    ):
        raise ConfigurationError(
            "ZOHO_REDIRECT_URI must be the registered HTTP or HTTPS callback "
            "URI, without query parameters or a fragment."
        )
    if parsed.scheme == "http" and parsed.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise ConfigurationError(
            "An HTTP ZOHO_REDIRECT_URI must use a loopback host; use HTTPS "
            "for any other host."
        )


def build_authorization_url(
    *,
    accounts_server: str,
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
    state: str,
) -> str:
    """Build Zoho's authorization URL with offline access and PKCE S256."""
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": ZOHO_MAIL_SCOPE,
            "code_challenge_method": "S256",
            "code_challenge": code_challenge,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
    )
    return f"{accounts_server.rstrip('/')}/oauth/v2/auth?{query}"


def authorization_code_from_callback(
    callback_url: str,
    *,
    redirect_uri: str,
    expected_state: str,
) -> str:
    """Validate the returned redirect URL and extract its one-time code."""
    callback = urlsplit(callback_url)
    expected = urlsplit(redirect_uri)
    if (
        callback.scheme.casefold() != expected.scheme.casefold()
        or callback.netloc.casefold() != expected.netloc.casefold()
        or callback.path != expected.path
    ):
        raise InputError(
            "The pasted URL does not match ZOHO_REDIRECT_URI. Paste the full "
            "URL Zoho redirected to after approval."
        )

    parameters = parse_qs(callback.query, keep_blank_values=True)
    returned_states = parameters.get("state", [])
    if len(returned_states) != 1 or not hmac.compare_digest(
        returned_states[0],
        expected_state,
    ):
        raise InputError(
            "Zoho's redirect state did not match this authorization attempt. "
            "Run the authorization command again."
        )

    if parameters.get("error"):
        raise InputError(
            "Zoho did not grant authorization. Review the requested access "
            "and try again."
        )

    codes = parameters.get("code", [])
    if len(codes) != 1 or not codes[0].strip():
        raise InputError(
            "The Zoho redirect did not contain an authorization code."
        )
    return codes[0].strip()
