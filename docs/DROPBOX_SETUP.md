# Dropbox setup

DEApp uses Dropbox's Python SDK to download one configured workbook, update a
local working copy, validate that copy, then upload it only if the Dropbox file
is still at the revision DEApp downloaded.

## Dropbox app

Create a scoped Dropbox app. Choose App Folder access if the workbook can live
inside the app folder. If DEApp must access a workbook elsewhere in the account,
the app needs Full Dropbox access. Grant only these file scopes:

- `files.content.read`
- `files.content.write`

The existing workbook path and a separate test workbook path must be set in
`config/config.toml` under `[dropbox]`. Dropbox paths start with `/` and are
relative to the app's configured access root. Do not use the production path for
integration runs.

```toml
[dropbox]
workbook_path = "/folder/production-workbook.xlsx"
test_workbook_path = "/DEApp-test/test-workbook.xlsx"
```

These are examples only; replace them with the actual paths in the authorized
Dropbox account. `DropboxClient.from_settings(settings, test_mode=True)` requires
the test path and does not fall back to the production path.

## Authorize the Windows account

Set `DROPBOX_APP_KEY` in the local `.env` file, then run:

```powershell
python scripts/authorize_dropbox.py
```

The script uses PKCE, requests offline access, and stores the refresh token in
Windows Credential Manager. It does not print or save the token in `.env`. Run
authorization as the same Windows account that will run DEApp, including the
Task Scheduler account.

## Transfer safeguards

`download_workbook()` writes to a staging file, verifies its size against the
Dropbox metadata, then atomically installs the local copy. It returns the
Dropbox revision captured at download time. The application workflow must call
`WorkbookService.validate()` before `upload_workbook()`.

The upload uses Dropbox `WriteMode.update` with that captured revision,
`autorename=False`, and `strict_conflict=True`. If another user or process
changed or removed the remote file, upload fails with `DropboxConflictError`;
DEApp must not retry with unconditional overwrite or advance execution state.
The SDK's single-request upload is limited to 150 MiB; larger workbooks require
an upload-session implementation, which is not included yet.

The Dropbox client is an injectable workflow dependency. The CLI runner does
not yet construct a complete production workflow; email identification and
workbook validation remain separate unfinished project work.
