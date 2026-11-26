"""Download and revision-guarded upload for the configured Dropbox workbook."""

from __future__ import annotations

import logging
from pathlib import Path
import os
import tempfile

import keyring
from dropbox import Dropbox
from dropbox.exceptions import ApiError, DropboxException
from dropbox.files import WriteMode
from keyring.errors import KeyringError

from deapp.application.exceptions import (
    ConfigurationError,
    DropboxConflictError,
    DropboxError,
)
from deapp.config.environment import load_secrets
from deapp.config.settings import Settings
from deapp.services.dropbox.models import DropboxSnapshot


DROPBOX_SCOPES = ["files.content.read", "files.content.write"]
KEYRING_SERVICE = "DEApp"
KEYRING_USERNAME = "dropbox_refresh_token"
MAX_SINGLE_UPLOAD_BYTES = 150 * 1024 * 1024
logger = logging.getLogger(__name__)


class DropboxClient:
    """Transfer one explicitly configured workbook to and from Dropbox.

    The caller must validate the closed local workbook before calling
    ``upload_workbook``. Uploads use the revision captured by
    ``download_workbook`` so a newer remote revision is never silently lost.
    """

    def __init__(
        self,
        *,
        app_key: str,
        refresh_token: str,
        remote_path: str,
    ) -> None:
        app_key = app_key.strip()
        refresh_token = refresh_token.strip()
        remote_path = remote_path.strip()
        if not remote_path.startswith("/") or remote_path.endswith("/"):
            raise ConfigurationError(
                "Dropbox workbook path must be an absolute Dropbox file path."
            )
        if not app_key:
            raise ConfigurationError("Missing required setting: DROPBOX_APP_KEY")
        if not refresh_token:
            raise ConfigurationError("Dropbox authorization is not configured.")

        self._remote_path = remote_path
        self._client = Dropbox(
            app_key=app_key,
            oauth2_refresh_token=refresh_token,
            scope=DROPBOX_SCOPES,
            timeout=60,
            max_retries_on_error=3,
            max_retries_on_rate_limit=3,
            user_agent="DEApp/0.1.0",
        )

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        test_mode: bool = False,
    ) -> DropboxClient:
        """Create a client using the selected configured path and local secrets.

        Test mode requires its own Dropbox path and never falls back to the
        production workbook path.
        """
        remote_path = (
            settings.dropbox_test_workbook_path
            if test_mode
            else settings.dropbox_workbook_path
        )
        setting_name = (
            "dropbox.test_workbook_path"
            if test_mode
            else "dropbox.workbook_path"
        )
        if remote_path is None:
            raise ConfigurationError(f"Missing required setting: {setting_name}")

        app_key = load_secrets(("DROPBOX_APP_KEY",))["DROPBOX_APP_KEY"]
        try:
            refresh_token = keyring.get_password(
                KEYRING_SERVICE,
                KEYRING_USERNAME,
            )
        except KeyringError as error:
            raise ConfigurationError(
                "Could not read Dropbox authorization from Windows Credential Manager."
            ) from error

        if not refresh_token:
            raise ConfigurationError(
                "Dropbox authorization is missing; run scripts/authorize_dropbox.py."
            )

        return cls(
            app_key=app_key,
            refresh_token=refresh_token,
            remote_path=remote_path,
        )

    def download_workbook(self, destination: Path) -> DropboxSnapshot:
        """Download to a temporary sibling and atomically install the local copy."""
        destination = Path(destination)
        staging_path: Path | None = None

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                dir=destination.parent,
                prefix=".deapp-",
                suffix=".download",
                delete=False,
            ) as temporary_file:
                staging_path = Path(temporary_file.name)

            metadata = self._client.files_download_to_file(
                str(staging_path),
                self._remote_path,
            )
            if staging_path.stat().st_size != metadata.size:
                raise DropboxError(
                    "The downloaded Dropbox workbook has an unexpected size."
                )
            if not metadata.rev:
                raise DropboxError(
                    "Dropbox did not return a revision for the downloaded workbook."
                )

            os.replace(staging_path, destination)
            return DropboxSnapshot(revision=metadata.rev)
        except DropboxError:
            raise
        except ApiError as error:
            raise DropboxError("Dropbox workbook download failed.") from error
        except DropboxException as error:
            raise DropboxError(
                "Dropbox workbook download failed due to an API or network error."
            ) from error
        except OSError as error:
            raise DropboxError(
                "Could not save the downloaded workbook locally."
            ) from error
        finally:
            if staging_path is not None:
                try:
                    staging_path.unlink(missing_ok=True)
                except OSError as error:
                    logger.warning(
                        "Could not remove a Dropbox download staging file (%s).",
                        type(error).__name__,
                    )

    def upload_workbook(
        self,
        source: Path,
        snapshot: DropboxSnapshot,
    ) -> str:
        """Conditionally replace the remote workbook after caller validation."""
        source = Path(source)

        try:
            content = source.read_bytes()
        except OSError as error:
            raise DropboxError("Could not read the local workbook.") from error

        if len(content) > MAX_SINGLE_UPLOAD_BYTES:
            raise DropboxError(
                "The workbook exceeds Dropbox's single-upload limit; "
                "an upload-session implementation is required."
            )

        try:
            metadata = self._client.files_upload(
                content,
                self._remote_path,
                mode=WriteMode.update(snapshot.revision),
                autorename=False,
                strict_conflict=True,
            )
        except ApiError as error:
            if _is_revision_conflict(error):
                raise DropboxConflictError(
                    "The Dropbox workbook changed after download; "
                    "the local copy was not uploaded."
                ) from error
            raise DropboxError("Dropbox workbook upload failed.") from error
        except DropboxException as error:
            raise DropboxError(
                "Dropbox workbook upload failed due to an API or network error."
            ) from error

        if not metadata.rev:
            raise DropboxError(
                "Dropbox did not confirm the uploaded workbook revision."
            )
        return metadata.rev

    def close(self) -> None:
        """Release the Dropbox SDK's network session."""
        self._client.close()

    def __enter__(self) -> DropboxClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _is_revision_conflict(error: ApiError) -> bool:
    """Return whether an upload error reports a file-path conflict."""
    try:
        upload_error = error.error
        return upload_error.is_path() and upload_error.get_path().is_conflict()
    except AttributeError:
        return False
