"""Unit tests for Zoho OAuth and subject-based selection."""

from datetime import date
from unittest.mock import Mock, patch

import pytest

from deapp.services.zoho.authentication import (
    ZohoAuthenticationError,
    ZohoAuthenticator,
    ZohoOAuthSettings,
)
from deapp.services.zoho.models import ZohoMessage
from deapp.services.zoho.selection import get_daily_messages_by_subject


def make_settings(
    *,
    refresh_token: str | None = None,
    authorization_code: str | None = None,
) -> ZohoOAuthSettings:
    return ZohoOAuthSettings(
        accounts_server="https://accounts.zoho.com",
        client_id="test-client",
        client_secret="test-secret",
        refresh_token=refresh_token,
        authorization_code=authorization_code,
        redirect_uri="https://example.test/callback",
        timeout_seconds=2,
    )


def mock_response(
    payload: dict[str, object],
    *,
    ok: bool = True,
    status_code: int = 200,
) -> Mock:
    response = Mock()
    response.ok = ok
    response.status_code = status_code
    response.json.return_value = payload
    return response


def test_get_access_token_exchanges_auth_code_and_saves_refresh_token() -> None:
    session = Mock()
    session.post.return_value = mock_response(
        {
            "access_token": "access-value",
            "refresh_token": "refresh-value",
            "expires_in": 3600,
        }
    )
    auth = ZohoAuthenticator(
        make_settings(authorization_code="one-time-code"),
        session=session,
    )

    with (
        patch(
            "deapp.services.zoho.authentication.save_secret"
        ) as save_secret,
        patch(
            "deapp.services.zoho.authentication.remove_secret"
        ) as remove_secret,
    ):
        assert auth.get_access_token() == "access-value"

    save_secret.assert_called_once_with(
        "ZOHO_REFRESH_TOKEN",
        "refresh-value",
    )
    remove_secret.assert_called_once_with("ZOHO_AUTH_CODE")
    assert session.post.call_args.kwargs["data"]["grant_type"] == (
        "authorization_code"
    )


def test_refresh_token_takes_precedence_over_auth_code() -> None:
    session = Mock()
    session.post.return_value = mock_response(
        {"access_token": "refreshed-access", "expires_in": 3600}
    )
    auth = ZohoAuthenticator(
        make_settings(
            refresh_token="saved-refresh",
            authorization_code="unused-code",
        ),
        session=session,
    )

    assert auth.get_access_token() == "refreshed-access"
    assert session.post.call_args.kwargs["data"]["grant_type"] == (
        "refresh_token"
    )


def test_failed_refresh_does_not_retry_with_auth_code() -> None:
    session = Mock()
    session.post.return_value = mock_response(
        {"error": "invalid_code"},
        ok=False,
        status_code=400,
    )
    auth = ZohoAuthenticator(
        make_settings(
            refresh_token="revoked-refresh",
            authorization_code="old-one-time-code",
        ),
        session=session,
    )

    with pytest.raises(ZohoAuthenticationError):
        auth.get_access_token()

    session.post.assert_called_once()
    assert session.post.call_args.kwargs["data"]["grant_type"] == (
        "refresh_token"
    )


class FakeMailClient:
    """Minimal fake for testing the subject-selection behavior."""

    def __init__(self, metadata_rows: list[dict[str, object]]) -> None:
        self.metadata_rows = metadata_rows
        self.retrieved_ids: list[str] = []

    def search_messages(
        self,
        account_id: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, object]]:
        assert start_date == end_date
        return self.metadata_rows

    def get_message(
        self,
        account_id: str,
        metadata: dict[str, object],
    ) -> ZohoMessage:
        message_id = str(metadata["messageId"])
        self.retrieved_ids.append(message_id)
        return ZohoMessage(
            uri=None,
            fromAddress=None,
            message_id=message_id,
            folder_id=str(metadata["folderId"]),
            sender=None,
            summary=None,
            status2=None,
            status=None,
            subject=str(metadata["subject"]),
            received_at=None,
            content="test content",
            raw_metadata=dict(metadata),
        )


def test_selection_keeps_duplicates_and_returns_none_for_missing_types() -> None:
    mail_client = FakeMailClient(
        [
            {
                "messageId": 11,
                "folderId": 20,
                "subject": "Subject for type one",
            },
            {
                "messageId": 12,
                "folderId": 20,
                "subject": "Subject for type one",
            },
            {
                "messageId": 13,
                "folderId": 20,
                "subject": "Subject for type three",
            },
        ]
    )

    result = get_daily_messages_by_subject(
        mail_client,  # type: ignore[arg-type]
        "account-1",
        date(2026, 11, 10),
        {
            "type_1": "Subject for type one",
            "type_2": "Subject for type two",
            "type_3": "Subject for type three",
            "type_4": "Subject for type four",
        },
    )

    assert result["type_1"] is not None
    assert [message.message_id for message in result["type_1"]] == ["11", "12"]
    assert result["type_2"] is None
    assert result["type_3"] is not None
    assert [message.message_id for message in result["type_3"]] == ["13"]
    assert result["type_4"] is None
