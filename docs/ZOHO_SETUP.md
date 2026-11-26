# Zoho Mail setup

## Register the OAuth client

Register DEApp in Zoho's API Console as a **Mobile-based Application** for the
desktop OAuth flow. Use the Zoho data center that matches the mailbox. Add the
redirect URI that DEApp will use; Zoho requires the URI in the authorization
request to exactly match a URI registered for the client.

DEApp requests only read access to messages:

```text
ZohoMail.messages.READ
```

Copy the client ID, accounts server, Mail API base URL, and registered redirect
URI into the local `.env` file using `.env.example` as a guide. The client ID is
an identifier, not a secret. Do not put a client secret, authorization code, or
refresh token in `.env`.

Zoho's desktop PKCE guide treats native clients as public clients, while its
token endpoint reference still lists `client_secret` as required. The
authorization command supports either response: it asks for a client secret
only when one is not already stored, and saves it to Windows Credential Manager
for that Zoho client ID. It never embeds the secret in the application or writes
it to `.env`.

## Authorize this Windows user

Install DEApp in the project environment, then run the setup command from the
project root:

```powershell
python scripts/authorize_zoho.py
```

The command creates an S256 PKCE challenge, opens Zoho in the browser, requests
offline access, and validates the OAuth `state` returned in the redirect URL.
After granting consent, paste the **full redirected URL** into the hidden
terminal prompt. If you registered a loopback HTTP URI and the browser reports
that the page cannot be reached, copy the URL from the address bar. The
authorization code is short-lived and is never written to disk. DEApp saves
the refresh token in Windows Credential Manager, scoped to the configured
client ID. Later runs obtain short-lived access tokens from that refresh token
and keep them in memory.

Run authorization as the same Windows account that runs DEApp, including the
account used by Task Scheduler. On successful setup, the command removes old
`ZOHO_CLIENT_SECRET`, `ZOHO_AUTH_CODE`, and `ZOHO_REFRESH_TOKEN` entries from
the local `.env` file. If the keyring cannot save the token, setup fails and
does not remove those legacy entries.

Zoho may return a refresh token only when offline access is requested. The
authorization command requests `access_type=offline` and explicit consent so a
token is returned during setup. Users can revoke DEApp access from Zoho's
Connected Apps settings; after revocation, run the setup command again.

## Runtime configuration

The following values remain ordinary local configuration in `.env`:

- `ZOHO_CLIENT_ID`
- `ZOHO_ACCOUNTS_SERVER`
- `ZOHO_MAIL_API_BASE`
- `ZOHO_REDIRECT_URI`
- `ZOHO_TIMEOUT_SECONDS`
- `ZOHO_ACCOUNT_ID` when the account cannot be selected unambiguously

The `.env` file is not a credential vault. Keep it out of source control and
use Windows Credential Manager for OAuth secrets.
