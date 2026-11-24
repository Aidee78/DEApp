"""Zoho Mail API operations for account lookup and message retrieval."""

from datetime import date, datetime, timezone
import logging
import time
from typing import Any
from urllib.parse import quote

import requests

from deapp.application.exceptions import (
    DateRangeError,
    InputError,
    ZohoMailError,
)
from deapp.services.zoho.authentication import (
    ZohoAuthenticationError,
    ZohoAuthenticator,
)
from deapp.services.zoho.models import ZohoMessage


logger = logging.getLogger(__name__)


class ZohoMailClient:
    """Search and retrieve messages through the Zoho Mail API."""

    def __init__(
        self,
        authenticator: ZohoAuthenticator,
        api_base_url: str,
        session: requests.Session | None = None,
        *,
        timeout_seconds: float = 30.0,
        max_attempts: int = 3,
        retry_delay_seconds: float = 2.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise InputError("timeout_seconds must be positive.")
        if max_attempts < 1:
            raise InputError("max_attempts must be at least 1.")
        if retry_delay_seconds < 0:
            raise InputError("retry_delay_seconds cannot be negative.")

        self._authenticator = authenticator
        self._api_base_url = api_base_url.rstrip("/")
        self._session = session or requests.Session()
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts
        self._retry_delay_seconds = retry_delay_seconds

    def get_account_id(
        self,
        preferred_account_id: str | None = None,
    ) -> str:
        """Return the configured account, or the only account Zoho returns.

        If multiple accounts are available, a preferred account ID is required
        so the client does not silently choose the wrong mailbox.
        """
        payload = self._request_json("GET", f"{self._api_base_url}/accounts")
        accounts = payload.get("data")

        if not isinstance(accounts, list) or not accounts:
            raise ZohoMailError(
                "Zoho Mail did not return an account for this user."
            )

        account_records: list[dict[str, object]] = []
        for account in accounts:
            if not isinstance(account, dict):
                raise ZohoMailError(
                    "Zoho Mail returned an invalid account record."
                )
            account_records.append(account)

        if preferred_account_id is not None:
            for account in account_records:
                account_id = account.get("accountId")
                if account_id is not None and str(account_id) == preferred_account_id:
                    return preferred_account_id
            raise ZohoMailError(
                "The configured Zoho account ID was not returned."
            )

        if len(account_records) != 1:
            raise ZohoMailError(
                "Zoho Mail returned multiple accounts; configure "
                "ZOHO_ACCOUNT_ID to select the mailbox."
            )

        account_id = account_records[0].get("accountId")
        if account_id is None or not str(account_id).strip():
            raise ZohoMailError(
                "Zoho Mail account response did not contain an account ID."
            )

        return str(account_id)

    def search_messages(
        self,
        account_id: str,
        start_date: date,
        end_date: date,
        *,
        page_size: int = 100,
    ) -> list[dict[str, object]]:
        """Returns metadata for messages Zoho finds in the requested dates."""
        if end_date < start_date:
            raise DateRangeError(
                "end_date must not be earlier than start_date."
            )
        if not 1 <= page_size <= 200:
            raise InputError("page_size must be between 1 and 200.")

        safe_account_id = quote(str(account_id), safe="")
        url = (
            f"{self._api_base_url}/accounts/{safe_account_id}"
            "/messages/search"
        )
        search_key = (
            f"fromDate:{start_date.strftime('%d-%b-%Y')}"
            f"::toDate:{end_date.strftime('%d-%b-%Y')}"
        )

        messages: list[dict[str, object]] = []
        start_index = 1

        while True:
            payload = self._request_json(
                "GET",
                url,
                params={
                    "searchKey": search_key,
                    "start": start_index,
                    "limit": page_size,
                },
            )
            page = payload.get("data", [])

            if not isinstance(page, list):
                raise ZohoMailError(
                    "Zoho Mail returned an invalid message list."
                )

            page_records: list[dict[str, object]] = []
            for item in page:
                if not isinstance(item, dict):
                    raise ZohoMailError(
                        "Zoho Mail returned an invalid message record."
                    )
                page_records.append(item)

            messages.extend(page_records)
            if len(page_records) < page_size:
                break

            start_index += page_size

        logger.info(
            "Retrieved %s candidate Zoho messages for the requested dates.",
            len(messages),
        )
        return messages

    def get_message(
        self,
        account_id: str,
        metadata: dict[str, object],
    ) -> ZohoMessage:
        """Retrieve content for one message using its folder and message IDs."""
        message_id = metadata.get("messageId")
        folder_id = metadata.get("folderId")

        if message_id is None or folder_id is None:
            raise ZohoMailError(
                "Zoho message metadata is missing its message or folder ID."
            )

        safe_account_id = quote(str(account_id), safe="")
        safe_folder = quote(str(folder_id), safe="")
        safe_message = quote(str(message_id), safe="")
        url = (
            f"{self._api_base_url}/accounts/{safe_account_id}"
            f"/folders/{safe_folder}/messages/{safe_message}/content"
        )

        payload = self._request_json("GET", url)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ZohoMailError(
                "Zoho Mail returned an invalid message content response."
            )

        content = data.get("content")
        if not isinstance(content, str):
            raise ZohoMailError(
                "Zoho Mail response did not contain message content."
            )

        return ZohoMessage(
            uri=self._optional_string(metadata.get("URI")),
            fromAddress=self._optional_string(metadata.get("fromAddress")),
            message_id=str(message_id),
            folder_id=str(folder_id),
            sender=self._optional_string(
                metadata.get("fromAddress") or metadata.get("sender")
            ),
            summary=self._optional_string(metadata.get("summary")),
            status2=self._optional_string(metadata.get("status2")),
            status=self._optional_string(metadata.get("status")),
            subject=self._optional_string(metadata.get("subject")),
            received_at=self._received_at(metadata),
            content=content,
            raw_metadata=dict(metadata),
        )

    def get_messages(
        self,
        account_id: str,
        start_date: date,
        end_date: date,
        *,
        page_size: int = 100,
    ) -> list[ZohoMessage]:
        """Search for messages and retrieve each message's full content."""
        metadata_rows = self.search_messages(
            account_id,
            start_date,
            end_date,
            page_size=page_size,
        )
        return [
            self.get_message(account_id, metadata)
            for metadata in metadata_rows
        ]

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str | int] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated request with bounded transient retries."""
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = self._send_request(method, url, params=params)

                if response.status_code == 401:
                    self._authenticator.invalidate_access_token()
                    response = self._send_request(method, url, params=params)

                if (
                    response.status_code == 429
                    or response.status_code >= 500
                ):
                    if attempt < self._max_attempts:
                        self._sleep_before_retry(response)
                        continue

                if not response.ok:
                    raise ZohoMailError(
                        "Zoho Mail API request failed with HTTP status "
                        f"{response.status_code}."
                    )

                try:
                    payload = response.json()
                except ValueError as exc:
                    raise ZohoMailError(
                        "Zoho Mail returned invalid JSON."
                    ) from exc

                if not isinstance(payload, dict):
                    raise ZohoMailError(
                        "Zoho Mail returned an unexpected response."
                    )

                status = payload.get("status")
                if isinstance(status, dict):
                    code = status.get("code")
                    if code is not None and str(code) != "200":
                        raise ZohoMailError(
                            "Zoho Mail reported an unsuccessful API response."
                        )

                return payload

            except (requests.Timeout, requests.ConnectionError) as exc:
                if attempt == self._max_attempts:
                    raise ZohoMailError(
                        "Zoho Mail request failed after transient network errors."
                    ) from exc
                time.sleep(self._retry_delay_seconds)
            except ZohoAuthenticationError as exc:
                raise ZohoMailError(
                    "Zoho authentication failed during a Mail API request."
                ) from exc
            except requests.RequestException as exc:
                raise ZohoMailError("Zoho Mail request failed.") from exc

        raise ZohoMailError("Zoho Mail request retry limit was reached.")

    def _send_request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str | int] | None,
    ) -> requests.Response:
        """Send one request using the current access token."""
        token = self._authenticator.get_access_token()
        return self._session.request(
            method,
            url,
            params=params,
            headers={"Authorization": f"Zoho-oauthtoken {token}"},
            timeout=self._timeout_seconds,
        )

    def _sleep_before_retry(self, response: requests.Response) -> None:
        """Wait briefly before retrying a rate-limited or server-error request."""
        retry_after = response.headers.get("Retry-After")
        try:
            delay = float(retry_after) if retry_after is not None else (
                self._retry_delay_seconds
            )
        except ValueError:
            delay = self._retry_delay_seconds

        time.sleep(min(max(delay, 0.0), 30.0))

    @staticmethod
    def _optional_string(value: object) -> str | None:
        """Return a value only when the API supplied a string."""
        return value if isinstance(value, str) else None

    @staticmethod
    def _received_at(
        metadata: dict[str, object],
    ) -> datetime | None:
        """Convert Zoho's Unix timestamp in milliseconds to UTC."""
        value = metadata.get("receivedtime", metadata.get("receivedTime"))
        if value is None:
            return None

        try:
            timestamp_ms = int(value)
            return datetime.fromtimestamp(
                timestamp_ms / 1000,
                tz=timezone.utc,
            )
        except (TypeError, ValueError, OverflowError, OSError) as exc:
            raise ZohoMailError(
                "Zoho message contained an invalid received timestamp."
            ) from exc
