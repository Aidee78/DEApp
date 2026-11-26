"""Authorize DEApp to use Dropbox with PKCE and store its refresh token."""

from getpass import getpass
import os
import webbrowser

import keyring
from dropbox import DropboxOAuth2FlowNoRedirect
from keyring.errors import KeyringError

from deapp.config.secret_store import load_environment


DROPBOX_SCOPES = ["files.content.read", "files.content.write"]
KEYRING_SERVICE = "DEApp"
KEYRING_USERNAME = "dropbox_refresh_token"


def main() -> int:
    """Run the interactive one-time OAuth authorization flow."""
    load_environment()
    app_key = os.environ.get("DROPBOX_APP_KEY", "").strip()
    if not app_key:
        print("Set DROPBOX_APP_KEY in the local .env file first.")
        return 1

    flow = DropboxOAuth2FlowNoRedirect(
        consumer_key=app_key,
        token_access_type="offline",
        scope=DROPBOX_SCOPES,
        use_pkce=True,
    )
    authorization_url = flow.start()
    print("Opening Dropbox authorization in your browser.")
    try:
        browser_opened = webbrowser.open(
            authorization_url,
            new=1,
            autoraise=True,
        )
    except webbrowser.Error:
        browser_opened = False
    if not browser_opened:
        print("Open this Dropbox authorization URL and approve DEApp:")
        print(authorization_url)

    authorization_code = getpass("Paste the authorization code: ").strip()
    if not authorization_code:
        print("No authorization code was provided.")
        return 1

    try:
        result = flow.finish(authorization_code)
    except Exception:
        # The OAuth helper can raise request-layer and OAuth-specific errors
        # that do not share one public exception base. Keep details out of output.
        print("Dropbox authorization failed. Check the app settings and try again.")
        return 1

    if not result.refresh_token:
        print("Dropbox returned no refresh token; offline access is required.")
        return 1

    try:
        keyring.set_password(
            KEYRING_SERVICE,
            KEYRING_USERNAME,
            result.refresh_token,
        )
    except KeyringError:
        print("Could not store the Dropbox refresh token in Windows Credential Manager.")
        return 1

    print("Dropbox authorization saved in Windows Credential Manager.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
