# DEApp Development Plan

## 1. Project Overview

**DEApp (Data Extraction Application)** is a Windows-based Python application that will:

1. Run manually from the command line or automatically through Windows Task Scheduler.
2. Determine the processing date range.
3. Connect to a Zoho Mail account.
4. Retrieve four specific types of emails.
5. Use a dedicated parser for each email type.
6. Extract the required data from those emails.
7. Download a specified Excel workbook from Dropbox.
8. Update the workbook using `xlwings`.
9. Validate the updated workbook.
10. Upload the successfully processed workbook back to Dropbox.
11. Record the successful execution state.
12. Display progress through a minimal GUI and maintain detailed logs.

The application must ensure that only one instance runs at a time and that the Dropbox workbook is not updated when processing fails.

---

# 2. Development Principles

- Build the application incrementally.
- Keep business logic separate from external-service code.
- Keep the GUI separate from application logic.
- Use structured logging instead of relying on `print()` for the finished application.
- Keep secrets separate from normal configuration.
- Keep runtime state separate from configuration.
- Test components independently before integrating them.
- Do not update the Dropbox workbook until the complete processing operation succeeds.
- Design the application so it can later be packaged as a Windows `.exe`.

---

# 3. Development Phases

## Phase 1 — Project Setup

### Objectives

Establish the Python project and development environment.

### Tasks

- [ ] Create the Python virtual environment.
- [ ] Configure `pyproject.toml`.
- [ ] Verify the `src/deapp/` package structure.
- [ ] Verify that the application can be executed as a Python module.
- [ ] Configure `.gitignore`.
- [ ] Create/update `README.md`.
- [ ] Create the `docs/` directory.
- [ ] Confirm the project runs without external integrations.

### Expected result

The project has a clean Python structure and can be started locally.

---

# Phase 2 — Configuration and Environment

### Objectives

Establish how DEApp receives configuration and secrets.

### Tasks

- [ ] Define required environment variables.
- [ ] Configure `.env` for local development.
- [ ] Create `.env.example`.
- [ ] Create `config/config.toml`.
- [ ] Implement configuration loading.
- [ ] Separate secrets from ordinary application configuration.
- [ ] Validate required configuration at application startup.

### Important distinction

**Configuration** describes what the application should use.

**State** describes what happened during previous executions.

---

# Phase 3 — Execution State

### Objectives

Implement persistent application state.

### Tasks

- [ ] Create `data/state.json`.
- [ ] Implement reading the last successful execution date.
- [ ] Implement saving successful execution state.
- [ ] Handle missing state files.
- [ ] Handle invalid/corrupted state files.
- [ ] Ensure failed executions do not update the successful-execution state.

### Expected result

DEApp can determine where the previous successful processing ended.

---

# Phase 4 — Command-Line Interface

### Objectives

Implement command-line execution.

### Supported execution forms

No arguments:

```text
python -m deapp
```

Start date only:

```text
python -m deapp --start-date YYYY-MM-DD
```

End date only:

```text
python -m deapp --end-date YYYY-MM-DD
```

Both dates:

```text
python -m deapp --start-date YYYY-MM-DD --end-date YYYY-MM-DD
```

### Tasks

- [ ] Implement argument parsing with `argparse`.
- [ ] Validate `YYYY-MM-DD`.
- [ ] Implement start-date-only behavior.
- [ ] Implement end-date-only behavior.
- [ ] Implement both-date behavior.
- [ ] Implement no-argument behavior.
- [ ] Reject invalid date ranges.
- [ ] Define appropriate exit codes.

### Date rules

No arguments:

```text
start = date after/based on the last successful execution according to the finalized business rule
end   = current date
```

Start only:

```text
start = supplied date
end   = current date
```

End only:

```text
start = last successful execution date
end   = supplied date
```

Both:

```text
start = supplied start date
end   = supplied end date
```

The exact inclusive/exclusive interpretation of the last successful date will be finalized before implementation.

---

# Phase 5 — Application Logging

### Objectives

Implement production-quality logging.

### Log levels

- DEBUG
- INFO
- WARNING
- ERROR
- CRITICAL

### Tasks

- [ ] Create centralized logging configuration.
- [ ] Create file logging.
- [ ] Configure console logging for development.
- [ ] Define log formatting.
- [ ] Add timestamps.
- [ ] Log application startup and shutdown.
- [ ] Log important workflow stages.
- [ ] Log exceptions with useful context.
- [ ] Decide on log rotation/retention.

### Expected result

DEApp can explain what happened during an execution without relying on `print()` statements.

---

# Phase 6 — Application Locking

### Objectives

Prevent multiple DEApp instances from running simultaneously.

### Scenarios to protect against

- Manual execution while Task Scheduler is running.
- Two command windows launching DEApp.
- Task Scheduler starting while a previous execution is still running.
- Accidental double-click execution of the executable.

### Tasks

- [ ] Implement a Windows application-wide lock.
- [ ] Acquire the lock at application startup.
- [ ] Exit cleanly if another instance owns the lock.
- [ ] Release the lock when execution finishes.
- [ ] Test normal and abnormal termination behavior.

### Expected result

Only one DEApp execution can be active at a time.

---

# Phase 7 — Application Workflow

### Objectives

Create the central orchestration layer.

### Target workflow

```text
Start
  ↓
Validate configuration
  ↓
Determine dates
  ↓
Acquire application lock
  ↓
Authenticate with Zoho
  ↓
Retrieve required emails
  ↓
Parse emails
  ↓
Validate extracted data
  ↓
Download Excel workbook
  ↓
Update workbook
  ↓
Validate workbook
  ↓
Upload workbook to Dropbox
  ↓
Record successful execution
  ↓
Notify completion
  ↓
Exit
```

### Tasks

- [ ] Implement the application runner.
- [ ] Implement workflow orchestration.
- [ ] Define workflow-level exceptions.
- [ ] Define failure handling.
- [ ] Ensure successful state is only recorded after successful workbook upload.
- [ ] Ensure failures do not cause a Dropbox upload.

---

# Phase 8 — Zoho Authentication

### Objectives

Implement secure Zoho authentication and token management.

### Credentials/state to handle

- `ZOHO_CLIENT_ID`
- `ZOHO_CLIENT_SECRET`
- `ZOHO_REDIRECT_URI`
- `ZOHO_AUTH_CODE`
- `ZOHO_REFRESH_TOKEN`
- `ZOHO_ACCESS_TOKEN`
- `ZOHO_ACCESS_TOKEN_EXPIRES_AT`

### Tasks

- [ ] Confirm the current Zoho Mail API and OAuth requirements.
- [ ] Implement authentication management.
- [ ] Implement access-token handling.
- [ ] Implement access-token expiration handling.
- [ ] Implement refresh-token flow.
- [ ] Prevent secrets from appearing in logs.
- [ ] Test authentication independently.

### Expected result

The application can obtain a valid Zoho access token when required.

---

# Phase 9 — Zoho Mail Integration

### Objectives

Connect to Zoho Mail and retrieve the required emails.

### Tasks

- [ ] Confirm how the four target emails will be identified.
- [ ] Implement Zoho Mail client.
- [ ] Implement email search.
- [ ] Implement email retrieval.
- [ ] Retrieve required message content.
- [ ] Handle missing emails.
- [ ] Handle duplicate/multiple matching emails.
- [ ] Handle API failures.
- [ ] Add appropriate logging.

### Important business decision

The exact identification rules for each of the four email types must be finalized before the parsers are implemented.

Possible criteria include:

- sender
- subject
- folder
- date
- subject pattern
- sender + subject
- other deterministic criteria

---

# Phase 10 — Email Data Models

### Objectives

Define structured representations for retrieved emails and extracted data.

### Tasks

- [ ] Define email model.
- [ ] Define extracted-data model.
- [ ] Define validation rules.
- [ ] Define how parser results are represented.
- [ ] Ensure parser output can be consumed by the Excel layer.

---

# Phase 11 — Email Parsers

### Objectives

Implement one parser for each target email type.

### Structure

```text
parser_1.py
parser_2.py
parser_3.py
parser_4.py
```

### Tasks

- [ ] Document the expected structure of email type 1.
- [ ] Implement parser 1.
- [ ] Test parser 1 with representative email samples.

- [ ] Document the expected structure of email type 2.
- [ ] Implement parser 2.
- [ ] Test parser 2.

- [ ] Document the expected structure of email type 3.
- [ ] Implement parser 3.
- [ ] Test parser 3.

- [ ] Document the expected structure of email type 4.
- [ ] Implement parser 4.
- [ ] Test parser 4.

### Important rule

Each parser should focus on converting its specific email format into structured application data.

It should not:

- download Dropbox files
- modify Excel
- control the GUI
- manage application scheduling

---

# Phase 12 — Dropbox Integration

### Objectives

Implement Dropbox workbook synchronization.

### Tasks

- [ ] Confirm Dropbox API requirements.
- [ ] Implement Dropbox authentication.
- [ ] Implement workbook download.
- [ ] Store downloaded workbook in a temporary location.
- [ ] Implement upload.
- [ ] Handle upload failures.
- [ ] Handle download failures.
- [ ] Verify the uploaded result where appropriate.
- [ ] Clean temporary files.

### Transaction rule

The original Dropbox workbook must remain unchanged if processing fails before the upload step.

---

# Phase 13 — Excel Integration

### Objectives

Implement workbook manipulation using `xlwings`.

### Tasks

- [ ] Confirm Microsoft Excel requirements.
- [ ] Implement workbook opening.
- [ ] Implement workbook modification.
- [ ] Implement workbook saving.
- [ ] Implement proper workbook closing.
- [ ] Handle Excel process failures.
- [ ] Handle workbook lock/open conflicts.
- [ ] Handle missing sheets.
- [ ] Handle missing cells/tables/ranges.
- [ ] Handle corrupted workbooks.
- [ ] Validate workbook contents after modification.

### Important dependency

Because `xlwings` controls Microsoft Excel, the target Windows machine will require a compatible Microsoft Excel installation.

---

# Phase 14 — Excel/Dropbox Transaction

### Objectives

Combine the Excel and Dropbox operations safely.

### Target behavior

```text
Download workbook
      ↓
Create local working copy
      ↓
Modify workbook
      ↓
Validate workbook
      ↓
Everything successful?
   /             NO              YES
 ↓                ↓
Discard          Upload
local copy       to Dropbox
                  ↓
               Success
```

### Tasks

- [ ] Implement local working copy.
- [ ] Ensure original Dropbox file is not modified during processing.
- [ ] Validate workbook before upload.
- [ ] Upload only after validation succeeds.
- [ ] Handle upload failure safely.
- [ ] Clean temporary files.
- [ ] Record successful execution only after upload succeeds.

---

# Phase 15 — Minimal GUI

### Objectives

Provide a minimal visual interface showing execution progress.

### GUI responsibilities

The GUI should display status, not perform business logic.

### Example statuses

```text
Starting DEApp
Connecting to Zoho
Retrieving emails
Processing email 1 of 4
Processing email 2 of 4
Processing email 3 of 4
Processing email 4 of 4
Downloading workbook
Updating Excel
Validating workbook
Uploading workbook
Execution completed
```

### Tasks

- [ ] Implement Tkinter window.
- [ ] Display application status.
- [ ] Display progress.
- [ ] Handle application completion.
- [ ] Handle user closing the window.
- [ ] Ensure closing/cancellation does not cause an invalid Dropbox update.
- [ ] Ensure scheduled executions also display the window.

---

# Phase 16 — Error Handling and Exit Codes

### Objectives

Make failures predictable and diagnosable.

### Tasks

- [ ] Define application exception hierarchy.
- [ ] Define standard exit codes.
- [ ] Log exceptions.
- [ ] Display appropriate user-facing errors.
- [ ] Ensure failed executions do not update successful state.
- [ ] Ensure failed executions do not upload invalid workbooks.
- [ ] Test failures at each major workflow stage.

---

# Phase 17 — Unit Testing

### Objectives

Test individual components independently.

### Areas

- [ ] CLI argument parsing.
- [ ] Date handling.
- [ ] State management.
- [ ] Application locking.
- [ ] Configuration loading.
- [ ] Email models.
- [ ] Parser 1.
- [ ] Parser 2.
- [ ] Parser 3.
- [ ] Parser 4.
- [ ] Workflow logic.
- [ ] Error handling.

---

# Phase 18 — Integration Testing

### Objectives

Test communication between DEApp and external systems.

### Areas

- [ ] Zoho authentication.
- [ ] Zoho Mail retrieval.
- [ ] Dropbox authentication.
- [ ] Dropbox download.
- [ ] Excel processing.
- [ ] Dropbox upload.
- [ ] End-to-end workflow.

### Safety requirement

Integration tests should not accidentally overwrite the production Dropbox workbook.

Use test accounts/files or an explicitly configured test environment.

---

# Phase 19 — Windows Task Scheduler

### Objectives

Configure automatic execution.

### Required behavior

DEApp should run automatically every day at approximately 08:30.

If the computer was unavailable at the scheduled time, Windows Task Scheduler should be configured to run the task at the next available opportunity.

### Tasks

- [ ] Create Task Scheduler configuration.
- [ ] Configure daily trigger.
- [ ] Configure missed-start behavior.
- [ ] Configure executable path.
- [ ] Configure working directory.
- [ ] Configure execution permissions.
- [ ] Configure behavior when the application is already running.
- [ ] Test scheduled execution.
- [ ] Test missed execution.
- [ ] Test failure during scheduled execution.

---

# Phase 20 — Packaging as Windows Executable

### Objectives

Package DEApp for deployment as a Windows executable.

### Tasks

- [ ] Select/configure PyInstaller.
- [ ] Configure application entry point.
- [ ] Include required Python dependencies.
- [ ] Include required package resources.
- [ ] Handle configuration files.
- [ ] Handle `.env`/secrets appropriately.
- [ ] Handle runtime directories.
- [ ] Test packaged application.
- [ ] Test the `.exe` on a clean Windows environment.
- [ ] Test `xlwings`/Excel behavior from the packaged application.
- [ ] Test Task Scheduler using the packaged executable.

### Expected result

A deployable Windows application such as:

```text
DEApp.exe
```

can execute the same application workflow without requiring the user to manually run Python source code.

---

# Phase 21 — Deployment and Operational Verification

### Objectives

Verify DEApp in its actual production environment.

### Tasks

- [ ] Install DEApp on the target Windows machine.
- [ ] Configure credentials.
- [ ] Configure Dropbox path.
- [ ] Configure workbook location.
- [ ] Configure logs.
- [ ] Configure state storage.
- [ ] Configure Task Scheduler.
- [ ] Run a manual test.
- [ ] Run a scheduled test.
- [ ] Verify workbook output.
- [ ] Verify logs.
- [ ] Verify successful execution state.
- [ ] Verify failure recovery.
- [ ] Verify duplicate execution prevention.

---

# 4. Final Target Architecture

The final workflow should approximately follow:

```text
User / Windows Task Scheduler
              |
              v
        DEApp Entry Point
              |
              v
       CLI / Execution Setup
              |
              v
       Application Runner
              |
              v
       Application Workflow
              |
     +--------+--------+
     |        |        |
     v        v        v
   Zoho    Parsers   State
     |        |
     v        v
  Emails   Structured Data
              |
              v
          Dropbox
              |
              v
       Local Workbook
              |
              v
            Excel
           xlwings
              |
              v
      Validated Workbook
              |
              v
      Upload to Dropbox
              |
              v
      Save Success State
              |
              v
         GUI / Logging
              |
              v
             Exit
```

---

# 5. Important Business Decisions Still To Be Finalized

Before implementing the corresponding components, we need to establish:

1. Exact identification rules for each of the four emails.
2. What happens when one or more expected emails are missing.
3. Exact data extracted by each parser.
4. Exact Excel workbook structure.
5. Which sheets, tables, cells, or ranges are updated.
6. Whether existing Excel data is appended, overwritten, or otherwise modified.
7. Exact behavior when the user closes the GUI during processing.
8. Exact date-range inclusivity rules.
9. Exact behavior when a previous execution failed.
10. Exact Dropbox workbook path.
11. Exact Zoho Mail folder/mailbox locations.
12. Exact logging retention requirements.
13. Exact production configuration and secret-storage strategy.

These decisions should be resolved before implementing the affected components.

---

# 6. Development Order

The recommended implementation order is:

```text
1.  Project setup
2.  Configuration
3.  State management
4.  CLI and date handling
5.  Logging
6.  Application locking
7.  Application workflow
8.  Zoho authentication
9.  Zoho Mail integration
10. Email models
11. Email parsers
12. Dropbox integration
13. Excel integration
14. Transactional workflow
15. GUI
16. Error handling refinement
17. Unit tests
18. Integration tests
19. Windows Task Scheduler
20. PyInstaller packaging
21. Deployment
```

We will implement and test each phase before moving to the next major phase.
