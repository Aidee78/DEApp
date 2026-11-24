"""Unit tests for the Zoho Mail API client."""

from datetime import date
from unittest.mock import Mock

import pytest

from deapp.application.exceptions import DateRangeError
from deapp.services.zoho.mail_client import (
    ZohoMailClient,
    ZohoMailError,
)


def mock_response(
    payload: dict[str, object],
    *,
    status_code: int = 200,
    ok: bool = True,
) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.ok = ok
    response.headers = {}
    response.json.return_value = payload
    return response


def make_client(session: Mock) -> ZohoMailClient:
    auth = Mock()
    auth.get_access_token.return_value = "fake-access-token"
    return ZohoMailClient(
        authenticator=auth,
        api_base_url="https://mail.zoho.com/api",
        session=session,
        retry_delay_seconds=0,
    )


def test_get_account_id_refuses_to_guess_between_multiple_accounts() -> None:
    session = Mock()
    session.request.return_value = mock_response(
        {
            "data": [
                {"accountId": 10},
                {"accountId": 20},
            ]
        }
    )
    client = make_client(session)

    with pytest.raises(ZohoMailError, match="multiple accounts"):
        client.get_account_id()


def test_search_messages_retrieves_all_pages() -> None:
    session = Mock()
    session.request.side_effect = [
        mock_response({"data": [{"messageId": 1, "folderId": 2}]}),
        mock_response({"data": []}),
    ]
    client = make_client(session)

    messages = client.search_messages(
        "account-1",
        date(2026, 11, 10),
        date(2026, 11, 10),
        page_size=1,
    )

    assert len(messages) == 1
    assert messages[0]["messageId"] == 1
    assert session.request.call_count == 2


def test_get_message_retrieves_content_and_converts_received_time() -> None:
    session = Mock()
    session.request.return_value = mock_response(
        {"data": {"content": "<p>hello</p>"}}
    )
    client = make_client(session)

    message = client.get_message(
        "account-1",
        {
            "messageId": 123,
            "folderId": 456,
            "subject": "A subject",
            "receivedtime": 1794268800000,
        },
    )

    assert message.message_id == "123"
    assert message.folder_id == "456"
    assert message.subject == "A subject"
    assert message.content == "<p>hello</p>"
    assert message.received_at is not None


def test_search_messages_rejects_invalid_date_range() -> None:
    client = make_client(Mock())

    with pytest.raises(DateRangeError, match="end_date"):
        client.search_messages(
            "account-1",
            date(2026, 11, 11),
            date(2026, 11, 10),
        )
