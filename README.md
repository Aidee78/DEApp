# DEApp

DEApp is a Windows Python application under development. Its planned purpose is to retrieve defined emails from Zoho Mail, extract and validate their data, update an Excel workbook stored in Dropbox, and record successful runs.

## Requirements

- Python 3.14.7 or later
- Windows is the target platform.
- Microsoft Excel must be installed on the target Windows machine before using the planned `xlwings` integration. Excel automation is not part of the current configuration-only startup.

## Setup

From the project root, create and activate a virtual environment:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Command-line date options

DEApp accepts optional start and end dates:

```powershell
python -m deapp
python -m deapp --start-date 2026-10-01
python -m deapp --end-date 2026-10-15
python -m deapp --start-date 2026-10-01 --end-date 2026-10-15
```

## Activity-record consolidation

The approved rules for consolidating extracted activity records are in the
[activity-record consolidation guide](docs/RECORD_CONSOLIDATION.md). Records
are grouped only when their type and the values and flags for date, shift,
and batch number match. Workbook duplicate-row and retry behavior remains a
separate open decision.

## Zoho authorization

Zoho desktop OAuth setup and secure token storage are documented in the
[Zoho setup guide](docs/ZOHO_SETUP.md). The authorization utility stores the
refresh token in Windows Credential Manager, not in `.env`.

## Dropbox setup

Dropbox authorization and transfer setup are documented in the
[Dropbox setup guide](docs/DROPBOX_SETUP.md). Configure separate production
and test workbook paths before use. The Dropbox service stores its refresh token
in Windows Credential Manager and uses a remote revision check before replacing
a workbook.
