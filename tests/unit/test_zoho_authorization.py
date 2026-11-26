"""Unit tests for the interactive Zoho PKCE setup helpers."""

import base64
import hashlib
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest

from deapp.application.exceptions import ConfigurationError, InputError
from deapp.services.zoho.oauth_flow import (
    authorization_code_from_callback,
    build_authorization_url,
    create_pkce_pair,
    validate_redirect_uri,
)


def test_code_challenge_uses_base64url_sha256_without_padding() -> None:
    generated_verifier, challenge = create_pkce_pair()
    generated_expected = base64.urlsafe_b64encode(
        hashlib.sha256(generated_verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")

    assert challenge == generated_expected


def test_authorization_url_requests_pkce_offline_access_and_read_scope() -> None:
    url = build_authorization_url(
        accounts_server="https://accounts.zoho.eu/",
        client_id="desktop-client-id",
        redirect_uri="http://127.0.0.1:53682/oauth/callback",
        code_challenge="challenge-value",
        state="state-value",
    )
    parameters = parse_qs(urlsplit(url).query)

    assert url.startswith("https://accounts.zoho.eu/oauth/v2/auth?")
    assert parameters["client_id"] == ["desktop-client-id"]
    assert parameters["redirect_uri"] == [
        "http://127.0.0.1:53682/oauth/callback"
    ]
    assert parameters["scope"] == ["ZohoMail.messages.READ"]
    assert parameters["code_challenge_method"] == ["S256"]
    assert parameters["code_challenge"] == ["challenge-value"]
    assert parameters["access_type"] == ["offline"]
    assert parameters["state"] == ["state-value"]


def test_redirect_uri_allows_loopback_http_but_rejects_remote_http() -> None:
    validate_redirect_uri("http://127.0.0.1:53682/oauth/callback")

    with pytest.raises(ConfigurationError, match="loopback"):
        validate_redirect_uri("http://example.test/oauth/callback")


def test_callback_requires_matching_registered_uri_and_state() -> None:
    callback = "http://127.0.0.1:53682/oauth/callback?" + urlencode(
        {"code": "one-time-code", "state": "expected-state"}
    )

    code = authorization_code_from_callback(
        callback,
        redirect_uri="http://127.0.0.1:53682/oauth/callback",
        expected_state="expected-state",
    )

    assert code == "one-time-code"


def test_callback_rejects_mismatched_state() -> None:
    callback = "http://127.0.0.1:53682/oauth/callback?" + urlencode(
        {"code": "one-time-code", "state": "unexpected-state"}
    )

    with pytest.raises(InputError, match="state did not match"):
        authorization_code_from_callback(
            callback,
            redirect_uri="http://127.0.0.1:53682/oauth/callback",
            expected_state="expected-state",
        )
