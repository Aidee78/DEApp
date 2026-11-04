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

## Command-line date options

DEApp accepts optional start and end dates:

```powershell
python -m deapp
python -m deapp --start-date 2026-10-01
python -m deapp --end-date 2026-10-15
python -m deapp --start-date 2026-10-01 --end-date 2026-10-15