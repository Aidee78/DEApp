# DEApp Development Plan

## 1. Project Overview

**DEApp (Data Extraction Application)** is a Windows-based Python application that retrieves four defined types of emails from Zoho Mail, extracts and validates their data, updates an Excel workbook stored in Dropbox, and records successful execution state.

The application is intended to:

- Run manually through the command line.
- Run automatically through Windows Task Scheduler, targeting approximately 08:30 daily.
- Determine the appropriate processing date range for each execution.
- Authenticate securely with Zoho Mail and retrieve the required emails.
- Parse the four email types with one generic parser because their formats and extraction rules are substantially the same. Confirm that the shared parser handles each type using representative samples.
- Validate extracted data before using it to update the workbook.
- Download the target Excel workbook from Dropbox to a local working location.
- Modify the workbook using `xlwings` and Microsoft Excel.
- Validate the updated workbook before uploading it.
- Upload the workbook to Dropbox only after the required processing and validation succeed.
- Record successful execution state only after the upload succeeds.
- Provide useful logs and a minimal GUI showing execution progress.
- Prevent multiple DEApp instances from processing concurrently.
- Eventually be packaged as a Windows executable.

This plan orders development by **increasing complexity**. Each phase establishes a usable layer that can be tested before the next major layer is introduced.

## 2. Development Principles

1. **Build incrementally.** Implement and test each phase before moving to the next major phase.
2. **Preserve the modular architecture.** Extend the existing `src/deapp/` structure rather than replacing it with a monolithic or simplified design.
3. **Inspect before modifying.** Check the relevant source files, tests, configuration, and documentation before making changes. A file's existence does not mean its functionality is implemented.
4. **Separate concerns.** Keep application orchestration, external-service integrations, parsing, workbook operations, GUI, configuration, and state management in their appropriate modules.
5. **Keep secrets separate.** Never commit credentials, tokens, authorization codes, or real email content.
6. **Keep configuration and state separate.** Configuration describes how the application should operate; state records the outcome of previous executions.
7. **Protect production data.** Do not upload a workbook unless the required processing and validation succeed.
8. **Advance state only after success.** Save successful execution state only after the Dropbox upload succeeds.
9. **Test independently before integration.** Use unit tests for component logic and safe, explicitly configured integration tests for external services.
10. **Keep documentation synchronized.** Update the README, configuration examples, tests, and this plan when implementation changes make them inaccurate.
11. **Do not invent business rules.** Identify unresolved decisions and ask for clarification when an assumption could affect extracted data, workbook contents, date ranges, or production behavior.
12. **Report verified behavior accurately.** Distinguish documented requirements from implemented and tested functionality.

## 3. Target Architecture

Retain the existing modular Python package and extend its modules as required.

```text
DEApp/
├── config/
│   └── config.toml
├── data/
│   └── state.json
├── docs/
│   └── DEVELOPMENT_PLAN.md
├── logs/
├── scripts/
├── tests/
│   ├── unit/
│   └── integration/
└── src/deapp/
    ├── application/
    │   ├── exceptions.py
    │   ├── runner.py
    │   └── workflow.py
    ├── cli/
    ├── config/
    ├── gui/
    ├── locking/
    ├── logging/
    ├── models/
    ├── parsers/
    │   └── report_parser.py  # Generic parser for the four similar email types
    ├── services/
    │   ├── dropbox/
    │   ├── excel/
    │   └── zoho/
    ├── state/
    └── utils/
```

Module responsibilities:

- `application/`: application orchestration, workflow, and application-level exceptions.
- `cli/`: command-line arguments and validation.
- `config/`: ordinary settings, environment variables, and startup configuration validation.
- `gui/`: progress display and user interaction only.
- `locking/`: single-instance coordination.
- `logging/`: centralized logging configuration.
- `models/`: structured email and extracted-data representations.
- `parsers/`: generic email parsing and shared parsing helpers; use one parser for the four similar email types, with explicit type-specific handling only where verified samples require it.
- `services/zoho/`: Zoho OAuth and Mail API integration.
- `services/dropbox/`: Dropbox authentication and file transfer.
- `services/excel/`: workbook manipulation and validation.
- `state/`: persistent successful-execution state.
- `utils/`: small, reusable helpers with clear responsibilities.

Parsers must not call Zoho, Dropbox, or Excel directly, control the GUI, or manage scheduling. The generic parser should transform the four similar email formats into structured application data and report unsupported or invalid input clearly.

## 4. Development Phases

# Phase 1 — Project Foundation and Configuration

### Objective

Establish a runnable Python project with a clear structure and validated configuration before implementing the application's business functionality.

### Tasks

#### 1.1. Establish the project environment

- [ ] Verify the supported Python version and local development environment.
- [ ] Configure `pyproject.toml`, including project metadata, dependencies, and development tools.
- [ ] Verify the existing `src/deapp/` package structure.
- [ ] Verify that `python -m deapp` reaches the application entry point.
- [ ] Configure `.gitignore` for virtual environments, secrets, temporary files, logs as appropriate, and generated artifacts.
- [ ] Ensure the required project and test directories exist.

#### 1.2. Implement configuration management

- [ ] Define ordinary application settings.
- [ ] Implement loading of `config/config.toml`.
- [ ] Implement environment-variable loading for secrets.
- [ ] Create or update `.env.example` using placeholder values only.
- [ ] Separate secrets from ordinary settings.
- [ ] Validate required settings at startup.
- [ ] Report missing or invalid setting names without exposing their values.
- [ ] Define how configuration paths are resolved in development and in a packaged application.

#### 1.3. Establish basic application structure

- [ ] Verify the entry point, CLI, runner, and workflow responsibilities.
- [ ] Preserve separation between application logic and external integrations.
- [ ] Add useful docstrings and Python 3.14-compatible type annotations to new or modified code.
- [ ] Add initial tests for configuration loading and startup behavior.
- [ ] Update setup instructions in `README.md`.

#### 1.4. Record foundational requirements

- [ ] Identify the target Windows environment.
- [ ] Confirm the expected Microsoft Excel installation for `xlwings`.
- [ ] Identify the intended Zoho account/API access requirements.
- [ ] Identify the target Dropbox workbook and path, when known.
- [ ] Record unresolved business decisions without guessing their answers.

### Acceptance criteria

- DEApp starts as a Python module.
- Configuration is loaded and validated.
- Missing or invalid configuration produces actionable errors.
- Secrets are not stored in committed files or printed in logs.
- Initial tests pass, and setup instructions match the actual project.

**Deliverable:** A runnable, configurable application foundation.

---

# Phase 2 — Command-Line Interface, Dates and Execution State

### Objective

Enable DEApp to determine the processing period and retain the outcome of previous successful executions without requiring external services.

### Tasks

#### 2.1. Implement command-line arguments

Support the following forms:

```text
python -m deapp
python -m deapp --start-date YYYY-MM-DD
python -m deapp --end-date YYYY-MM-DD
python -m deapp --start-date YYYY-MM-DD --end-date YYYY-MM-DD
```

- [ ] Implement argument parsing with `argparse`.
- [ ] Validate dates in `YYYY-MM-DD` format.
- [ ] Reject invalid date ranges.
- [ ] Define appropriate exit codes for invalid arguments.
- [ ] Provide clear command-line help.

#### 2.2. Implement date resolution

Define and implement the date range for each invocation.

| Invocation | Start date | End date |
|---|---|---|
| No arguments | Based on the last successful execution, according to the finalized boundary rule | Current date |
| Start date only | Supplied start date | Current date |
| End date only | Last successful execution date, according to the finalized boundary rule | Supplied end date |
| Both dates | Supplied start date | Supplied end date |

- [ ] Centralize date parsing and range resolution.
- [ ] Validate impossible dates and invalid ranges.
- [ ] Test date boundaries, including month/year changes.
- [ ] Finalize whether the last successful date is included or excluded before relying on it in production.

#### 2.3. Implement execution-state management

- [ ] Implement reading and writing `data/state.json`.
- [ ] Store the last successful processing state using a documented schema.
- [ ] Handle a missing state file.
- [ ] Handle malformed, corrupted, or unreadable state files explicitly.
- [ ] Prevent failed executions from advancing successful state.
- [ ] Make state writes robust against partial writes where practical.
- [ ] Test state persistence and recovery.

At this phase, test state management independently. Later workflow integration must enforce the exact point at which an execution is considered successful.

### Acceptance criteria

- All supported CLI forms behave as documented.
- Date ranges are validated and resolved consistently.
- State survives application restarts.
- Missing or corrupted state is handled explicitly.
- Tests verify that unsuccessful operations do not advance successful state.

**Deliverable:** A tested execution foundation with CLI, date resolution, and persistent state.

---

# Phase 3 — Zoho Authentication and Mail Integration

### Objective

Connect to Zoho Mail and retrieve the required emails for a specified processing period.

### Tasks

#### 3.1. Confirm Zoho API requirements

- [ ] Verify the current Zoho Mail API and OAuth requirements for the target account and region.
- [ ] Confirm required OAuth scopes and application registration settings.
- [ ] Define where client credentials and refresh tokens will be stored.
- [ ] Document the authorization setup without recording real secrets.

#### 3.2. Implement authentication

- [ ] Implement the Zoho authentication manager.
- [ ] Obtain and manage access tokens.
- [ ] Track access-token expiry where required.
- [ ] Implement refresh-token handling.
- [ ] Handle authentication errors and invalid/revoked tokens.
- [ ] Prevent client secrets, authorization codes, access tokens, and refresh tokens from appearing in logs.
- [ ] Test token acquisition, expiration handling, and refresh behavior independently.

#### 3.3. Define email identification rules

- [ ] Establish deterministic identification criteria for each of the four email types.
- [ ] Confirm the relevant sender, subject, folder, date, patterns, or combinations of criteria.
- [ ] Define expected behavior when no message matches.
- [ ] Define expected behavior when multiple messages match.
- [ ] Define how duplicate messages are recognized and handled.

Do not implement guessed matching rules. Resolve these requirements before depending on the retrieval results.

#### 3.4. Implement the Zoho Mail client

- [ ] Implement email search over the resolved date range.
- [ ] Retrieve required message metadata and content.
- [ ] Handle API failures, timeouts, rate limits, and authorization errors as appropriate.
- [ ] Handle missing and multiple matching emails according to the agreed rules.
- [ ] Add useful, secret-safe logging.
- [ ] Test retrieval using controlled test messages or mocked API responses.

### Acceptance criteria

- DEApp can authenticate with Zoho using the approved credential and token flow.
- Expired access tokens are handled correctly.
- The client retrieves the expected messages for a specified period.
- Missing messages, multiple matches, and API failures have defined behavior.
- Credentials and tokens are not exposed in logs.

**Deliverable:** A tested Zoho integration.

---

# Phase 4 — Email Models, Parsing and Business Logic

### Objective

Convert retrieved emails into validated, structured data that can be consumed by the Excel layer.

### Tasks

#### 4.1. Define data models

- [ ] Define the email model.
- [ ] Define the extracted-data model.
- [ ] Define parser result representations.
- [ ] Establish field types, required fields, and validation rules.
- [ ] Define how validation errors are reported to the workflow.
- [ ] Ensure model interfaces are suitable for the Excel layer.

#### 4.2. Document and implement the generic parser

The four target email types are expected to share substantially the same layout and extraction rules, so the current design uses one generic parser rather than four separate implementations. Verify this shared design against representative examples of all four types. If an example reveals a material format or rule difference, document and implement that difference explicitly without duplicating the full parser unnecessarily.

- [ ] Obtain representative email samples.
- [ ] Document the expected shared structure and any verified differences among the four types.
- [ ] Confirm the fields to extract and their meanings.
- [ ] Implement the generic parser for the shared structure.
- [ ] Validate required fields and data types.
- [ ] Handle missing fields, malformed content, and unexpected formatting.
- [ ] Add unit tests using representative and invalid samples from each of the four types.

The parser module is:

- `report_parser.py` (generic parser for the four similar email types)

The generic parser should interpret the supported email formats and return structured data. It must not download Dropbox files, modify Excel, control the GUI, or manage scheduling.

#### 4.3. Implement extraction validation and business rules

- [ ] Connect each identified email type to the generic parser using confirmed identification rules; keep email identification separate from parsing where practical.
- [ ] Validate parser output before it proceeds to workbook processing.
- [ ] Define how invalid records are handled.
- [ ] Implement the four field-status flags: `0` for parseable non-`None` values, `1` for parseable empty values, `2` for unparseable values, and `3` for conflicting sources.
- [ ] Assign flags `0`, `1`, and `2` in the Excel conversion helpers that inspect and convert each raw source value; assign flag `3` only where multiple sources are compared.
- [ ] Preserve the raw source value needed to distinguish an empty field from a nonempty but unparseable field.
- [ ] Resolve stage-specific measurement headers and `extra_fields` before assigning a status to a target measurement.
- [ ] Detect aliases and repeated source headers that target the same field; do not silently overwrite or discard their values.
- [ ] After consolidation, remove a record only when its batch number is `None` with flag `1`, every applicable time field is `None` with flag `1`, and every applicable measure field is `None` with flag `1`. The filter must leave retained values and flags unchanged.
- [x] Define extracted activity-record consolidation rules; see [RECORD_CONSOLIDATION.md](RECORD_CONSOLIDATION.md).
- [ ] Verify the conversion path preserves key-field flags before consolidation.
- [ ] Define workbook duplicate-row and repeated-processing behavior separately.
- [ ] Define the behavior when expected emails or required fields are missing.
- [ ] Prevent invalid or incomplete data from silently proceeding.
- [ ] Ensure extraction failures are visible in logs and workflow results.

#### 4.4. Test extraction independently

- [ ] Test the generic parser's normal cases using representative samples from all four email types.
- [ ] Test missing and malformed fields.
- [ ] Test flag assignment for parseable values, empty values, unparseable values, and conflicting sources.
- [ ] Test header aliases and repeated headers, including that valid values are not overwritten by empty values and differing values are reported as conflicts.
- [ ] Test stage-specific measurements found in `extra_fields` and the completely-empty unbatched-record filter.
- [ ] Test unexpected email formatting.
- [ ] Verify extracted values against source samples.
- [ ] Test email-type routing to the generic parser and combined extraction.
- [ ] Ensure tests do not require live Zoho credentials.
- [ ] Test activity grouping against exact record type, key values, and key flags.
- [ ] Test missing-value priority, all-`None` field flags, officer-name joining, and latest `received_at`.
- [ ] Test that tied conflicting values are reported instead of silently selected.

### Acceptance criteria

- One generic parser correctly handles all four target email types and is tested independently against representative samples for each type.
- Extracted data matches the agreed field definitions.
- Field statuses distinguish valid values, empty values, unparseable values, and conflicting sources without silently losing source values.
- Header aliases and repeated headers cannot silently overwrite other source values.
- Completely empty unbatched records are filtered by the approved rule without changing flags on retained records.
- Invalid or incomplete data is reported explicitly.
- Parser output has a stable structure suitable for workbook updates.
- Extracted activity records follow the approved consolidation rules in [RECORD_CONSOLIDATION.md](RECORD_CONSOLIDATION.md).

**Deliverable:** One tested generic parser and a validated extraction layer for all four email types.

---

# Phase 5 — Dropbox and Excel Integration

### Objective

Implement and test workbook retrieval, local modification, validation, and transfer independently of the full application workflow.

### Tasks

#### 5.1. Implement Dropbox authentication and access

- [ ] Confirm current Dropbox API requirements.
- [ ] Implement Dropbox authentication using the approved secret-storage approach.
- [ ] Configure the target workbook path.
- [ ] Handle authentication, permissions, missing-file, network, and API errors.
- [ ] Test access to the intended file without modifying the production workbook.

#### 5.2. Implement workbook download and upload

- [ ] Download the workbook to a controlled temporary location.
- [ ] Handle incomplete or failed downloads.
- [ ] Implement workbook upload.
- [ ] Handle failed or interrupted uploads.
- [ ] Verify upload success where appropriate.
- [ ] Implement safe temporary-file cleanup.
- [ ] Keep test files and production files clearly separated.

#### 5.3. Confirm workbook requirements

Before implementing workbook mutations:

- [ ] Identify the actual workbook structure.
- [ ] Confirm required worksheet names.
- [ ] Confirm tables, columns, ranges, and formulas involved.
- [ ] Define where each parser's data belongs.
- [ ] Define whether existing data is appended, overwritten, or transformed.
- [ ] Define how duplicate rows and existing records are handled.
- [ ] Define workbook validation criteria.

Do not infer workbook structure or mutation rules from filenames or assumptions.

#### 5.4. Implement Excel operations

Use `xlwings` to:

- [ ] Open the downloaded workbook.
- [ ] Locate required worksheets and ranges.
- [ ] Apply the agreed data updates.
- [ ] Save the workbook.
- [ ] Close the workbook and release Excel resources.
- [ ] Handle missing sheets, ranges, and tables.
- [ ] Handle workbook locks, Excel failures, and corrupted files.
- [ ] Ensure local modifications do not directly change the production Dropbox file.

#### 5.5. Implement workbook validation

- [ ] Validate required workbook structure.
- [ ] Validate expected changes after modification.
- [ ] Check that required data was written to the intended locations.
- [ ] Detect invalid or incomplete workbook output.
- [ ] Prevent a workbook that fails validation from being considered ready for upload.

#### 5.6. Test Dropbox and Excel separately

- [ ] Test download and upload with a test workbook.
- [ ] Test Excel opening, updating, saving, and closing.
- [ ] Test missing worksheets and invalid workbook structures.
- [ ] Test failure cleanup.
- [ ] Use an explicitly configured test Dropbox location for integration tests.

`xlwings` automates Microsoft Excel, so the target Windows environment must have a compatible Excel installation.

### Acceptance criteria

- DEApp can download a test workbook, modify it according to confirmed requirements, validate it, and upload it to a test Dropbox location.
- Workbook and Excel resources are closed safely.
- Failures are reported without modifying the production workbook.

**Deliverable:** Independently tested Dropbox and Excel components.

---

# Phase 6 — End-to-End Application Workflow

### Objective

Integrate configuration, date resolution, Zoho retrieval, parsing, validation, Excel updates, Dropbox transfer, and execution-state management into the complete business workflow.

### Tasks

#### 6.1. Implement workflow orchestration

Implement the following sequence:

```text
Start
  |
  v
Load and validate configuration
  |
  v
Resolve processing date range
  |
  v
Acquire application lock
  |
  v
Authenticate with Zoho
  |
  v
Retrieve required emails
  |
  v
Parse emails and validate extracted data
  |
  v
Download workbook from Dropbox
  |
  v
Create/use local working copy
  |
  v
Update workbook using Excel
  |
  v
Validate updated workbook
  |
  v
Upload workbook to Dropbox
  |
  v
Record successful execution state
  |
  v
Report result and exit
```

The application lock is introduced and fully hardened in Phase 7. The workflow must integrate with the locking component when it is available; it must not create a competing lock mechanism.

#### 6.2. Define workflow outcomes and failure boundaries

- [ ] Define successful completion criteria.
- [ ] Define the failure result for each major stage.
- [ ] Ensure retrieval, parsing, or validation failures prevent workbook upload.
- [ ] Ensure workbook modification or validation failures prevent upload.
- [ ] Ensure upload failure does not advance successful execution state.
- [ ] Ensure successful execution state is written only after upload succeeds.
- [ ] Ensure temporary files are cleaned up on success and failure.
- [ ] Ensure useful error context is available to the caller.

#### 6.3. Enforce the workbook transaction

The workflow must preserve these invariants:

1. Download the production workbook and work on a local copy.
2. Do not modify the production Dropbox workbook during local processing.
3. Validate extracted data before writing it to Excel.
4. Validate the updated workbook before upload.
5. Upload only after all required processing and validation succeed.
6. Do not record successful execution state until the upload succeeds.
7. If a failure occurs before upload, do not upload the local copy.
8. If upload fails, do not mark the run successful.
9. Close Excel resources and clean temporary files safely.
10. Prevent retries from causing unintended duplicate or destructive updates.

A failed upload may leave uncertainty about whether the remote service received the file. Handle that situation explicitly; do not blindly retry destructive operations or advance state without establishing the outcome.

#### 6.4. Test the complete workflow

- [ ] Test a successful end-to-end run using test emails and a test workbook.
- [ ] Test failures at each major stage.
- [ ] Verify no upload occurs after pre-upload failures.
- [ ] Verify successful state changes only after upload success.
- [ ] Verify correct processing date ranges.
- [ ] Verify workbook contents against expected results.
- [ ] Verify retries do not create unintended duplicate updates.

### Acceptance criteria

The complete workflow can retrieve, parse, validate, and apply data to a test workbook, upload the validated result, and record success only after the upload succeeds.

**Deliverable:** A functioning end-to-end DEApp core workflow.

---

# Phase 7 — Reliability, Logging, Error Handling and GUI

### Objective

Harden the working application for reliable manual and unattended execution.

### Tasks

#### 7.1. Implement structured logging

- [ ] Centralize logging configuration.
- [ ] Configure file logging and development console logging.
- [ ] Define log levels, formats, timestamps, and useful workflow context.
- [ ] Log application startup, shutdown, and major workflow stages.
- [ ] Capture exceptions with useful context.
- [ ] Prevent credentials, tokens, and unnecessary sensitive email content from appearing in logs.
- [ ] Define log rotation and retention.
- [ ] Test logging for successful and failed runs.

#### 7.2. Implement application locking

- [ ] Implement a Windows-compatible application-wide lock.
- [ ] Acquire the lock early enough to prevent overlapping processing.
- [ ] Exit cleanly when another instance owns the lock.
- [ ] Release the lock on normal completion.
- [ ] Handle abnormal termination and stale-lock scenarios safely.
- [ ] Test concurrent manual and scheduled execution.

#### 7.3. Standardize error handling and exit codes

- [ ] Define the application exception hierarchy.
- [ ] Define consistent exit codes.
- [ ] Provide actionable user-facing error messages.
- [ ] Ensure exceptions are logged without leaking secrets.
- [ ] Test failure handling at each major workflow stage.
- [ ] Verify that failure paths do not upload invalid workbooks or advance successful state.

#### 7.4. Implement the minimal GUI

Use Tkinter to display status and progress, for example:

```text
Starting DEApp
Connecting to Zoho
Retrieving emails
Processing emails
Downloading workbook
Updating Excel
Validating workbook
Uploading workbook
Execution completed
```

- [ ] Implement the status window.
- [ ] Display meaningful progress and completion/failure status.
- [ ] Keep business logic outside the GUI.
- [ ] Handle window closure and cancellation safely.
- [ ] Ensure closing or cancelling cannot cause an invalid workbook to be uploaded.
- [ ] Ensure manual and scheduled execution use the same underlying workflow.
- [ ] Define behavior when a GUI cannot be displayed in the execution environment.

#### 7.5. Improve recovery and retry safety

- [ ] Handle interrupted runs without falsely advancing state.
- [ ] Define how a subsequent run resumes or repeats work.
- [ ] Prevent duplicate workbook updates on retries.
- [ ] Handle uncertain upload outcomes explicitly.
- [ ] Verify temporary-file and Excel-process cleanup after failure.
- [ ] Test recovery after abnormal termination.

#### 7.6. Expand automated testing

- [ ] Complete unit tests for CLI, dates, configuration, state, models, parsers, validation, locking, and workflow behavior.
- [ ] Complete integration tests for Zoho, Dropbox, and Excel.
- [ ] Test successful and failed end-to-end executions.
- [ ] Test concurrent execution prevention.
- [ ] Test date boundaries and state recovery.
- [ ] Test that integration tests cannot accidentally overwrite the production workbook.

### Acceptance criteria

- Failures are diagnosable from logs and exit codes.
- Concurrent executions are prevented.
- GUI status reflects workflow progress without owning business logic.
- Interrupted and failed runs do not incorrectly advance state or upload invalid workbooks.
- Relevant automated tests pass.

**Deliverable:** A robust application ready for controlled production acceptance testing.

---

# Phase 8 — Documentation, Scheduling, Packaging and Deployment

### Objective

Prepare DEApp for regular operation on its intended Windows machine.

### Tasks

#### 8.1. Complete project documentation

- [ ] Update `README.md` with installation and execution instructions.
- [ ] Document the architecture and module responsibilities.
- [ ] Document configuration variables without exposing real secrets.
- [ ] Document credential and token setup.
- [ ] Document CLI arguments and date behavior.
- [ ] Document workbook assumptions and update rules.
- [ ] Document logging, state storage, troubleshooting, and recovery.
- [ ] Keep documentation consistent with verified implementation.
- [ ] Mark unresolved decisions clearly rather than presenting assumptions as requirements.

#### 8.2. Configure Windows Task Scheduler

The intended target is daily execution at approximately **08:30**, with a missed-start configuration that allows execution at the next available opportunity.

- [ ] Create or document the scheduled task configuration.
- [ ] Configure the daily trigger.
- [ ] Configure missed-start behavior.
- [ ] Configure the executable path and working directory.
- [ ] Configure execution permissions.
- [ ] Configure behavior when DEApp is already running.
- [ ] Verify access to configuration, secrets, logs, state, Dropbox, and Excel under the scheduled account.
- [ ] Test normal scheduled execution.
- [ ] Test missed execution.
- [ ] Test failure during scheduled execution.

#### 8.3. Package the Windows executable

Use PyInstaller or another explicitly approved packaging approach.

- [ ] Configure the application entry point.
- [ ] Include required Python dependencies and package resources.
- [ ] Handle configuration files and runtime directories.
- [ ] Keep secrets external to the executable.
- [ ] Ensure logs, temporary files, and state use appropriate runtime paths.
- [ ] Build the executable.
- [ ] Test the packaged application independently of the development environment.

#### 8.4. Verify packaged behavior

- [ ] Test on the target Windows environment.
- [ ] Verify `xlwings` and Microsoft Excel behavior.
- [ ] Verify Zoho authentication and mail retrieval.
- [ ] Verify Dropbox download and upload.
- [ ] Verify state persistence and logging.
- [ ] Verify application locking.
- [ ] Verify the GUI in the intended execution context.
- [ ] Verify Task Scheduler launches the packaged executable correctly.

#### 8.5. Perform production acceptance testing

- [ ] Configure production credentials using the approved method.
- [ ] Configure the production workbook path.
- [ ] Run a controlled manual execution.
- [ ] Verify workbook output independently.
- [ ] Verify logs and successful execution state.
- [ ] Run a scheduled execution.
- [ ] Test a failed run and recovery.
- [ ] Test missed scheduled execution.
- [ ] Verify duplicate execution prevention.
- [ ] Confirm that the production workbook is only updated after successful processing and validation.
- [ ] Record any operational limitations and the recovery procedure.

### Acceptance criteria

- DEApp is documented, packaged, and configured for scheduled execution.
- Manual and scheduled runs behave consistently.
- Production acceptance tests verify workbook correctness, logging, state, and failure recovery.
- The application is ready for routine operation in the target environment.

**Deliverable:** A deployable Windows application verified in its intended production environment.

---

## 5. Cross-Phase Safety and Quality Requirements

These requirements apply throughout development, not only in the phase where they are introduced.

### Secrets and privacy

- Never commit credentials, authorization codes, access tokens, refresh tokens, or `.env` files.
- Use safe placeholders in example configuration.
- Do not log secrets or unnecessary sensitive email content.
- Use test data in tests and documentation.

### Workbook protection

- Perform workbook changes on a local working copy.
- Validate extracted data before modifying the workbook.
- Validate workbook contents before upload.
- Do not upload after a pre-upload failure.
- Do not mark an execution successful after an upload failure.
- Test integration behavior against a test workbook and test Dropbox location.

### State correctness

- Keep configuration separate from execution state.
- Define the state schema and date-boundary semantics.
- Do not advance successful state until the workbook upload succeeds.
- Handle corrupted state explicitly rather than silently resetting it.

### Code quality

- Use Python 3.14-compatible type annotations in new and modified code.
- Add useful docstrings and comments that explain non-obvious decisions.
- Keep modules focused on their defined responsibilities.
- Avoid unnecessary dependencies and unrelated refactoring.
- Add or update tests for meaningful behavior changes.
- Keep documentation synchronized with implementation.

### Change management

- Inspect the working tree and relevant diffs before editing.
- Preserve unrelated user changes.
- Do not reset, clean, force-push, rewrite history, commit, or change remote settings unless explicitly requested.
- Review the final diff for unintended changes and accidentally included secrets.
- Report which tests and checks were actually run.

---

## 6. Business Decisions to Finalize

The following decisions must be resolved before implementing the components that depend on them:

The extracted activity-record consolidation rules are approved and documented in [RECORD_CONSOLIDATION.md](RECORD_CONSOLIDATION.md). That decision does not resolve duplicate workbook rows or repeated-processing behavior.

1. Exact identification criteria for each of the four email types.
2. Required fields and extraction rules for each parser.
3. Behavior when expected emails are missing.
4. Behavior when multiple messages match or duplicate messages are found.
5. Validation and handling of malformed or incomplete email data.
6. Exact workbook path in Dropbox.
7. Workbook worksheet names, tables, columns, formulas, and ranges that will be changed.
8. Whether data is appended, overwritten, or otherwise transformed.
9. Workbook duplicate-row and repeated-processing rules, separately from extracted activity-record consolidation.
10. Date-range inclusivity and interpretation of the last successful execution date.
11. Behavior after a failed or interrupted run.
12. Secure production credential and token-storage approach.
13. Logging retention requirements.
14. GUI closure and cancellation behavior, beyond the invariant that cancellation must not upload an invalid workbook.
15. Exact Task Scheduler settings and production execution account.
16. Target Windows and Microsoft Excel environment.
17. Resolution for conflicting field values tied on both flag and `received_at` (the current consolidator selects the first candidate and marks flag `3`, making the result input-order-dependent).
18. Precedence for flags `1` and `2` when choosing among consolidated candidates; the four flag definitions do not define a ranking.
19. Handling when multiple header aliases map to one field and one value is empty while another is nonempty.
20. Interpretation and destination of mixed-unit measurements such as `2 CARTONS 34 BUNDLES`, including whether bundle counts need their own field.

Resolve these decisions with explicit requirements or representative samples. Do not invent values or rules to make implementation appear complete.

---

## 7. Development and Verification Procedure

For every implementation task:

1. Identify the current phase and its acceptance criteria.
2. Inspect the relevant source files, tests, configuration, and documentation.
3. Identify ambiguities and risks before making consequential assumptions.
4. Implement the smallest coherent change that advances the current phase.
5. Add or update tests.
6. Run the most relevant tests and available static checks.
7. Inspect the final diff for regressions, unrelated edits, secrets, and documentation drift.
8. Report what changed, what was verified, which commands were run, and what remains unresolved.

Do not mark a phase complete solely because its files exist. Mark it complete only when its acceptance criteria have been met and verified.

---

## 8. Phase Summary

| Phase | Name | Completion milestone |
|---|---|---|
| 1 | Project Foundation and Configuration | The application starts and loads validated settings. |
| 2 | CLI, Dates and Execution State | Processing periods are resolved correctly and state persists safely. |
| 3 | Zoho Authentication and Mail Integration | The application authenticates and retrieves the required emails. |
| 4 | Email Models, Parsing and Business Logic | One generic parser produces validated structured data for all four email types. |
| 5 | Dropbox and Excel Integration | The application can safely modify and transfer a test workbook. |
| 6 | End-to-End Application Workflow | All major components complete the business process together. |
| 7 | Reliability, Logging, Error Handling and GUI | The application is diagnosable, prevents concurrent runs, and handles failures safely. |
| 8 | Documentation, Scheduling, Packaging and Deployment | The application is verified for scheduled production operation. |

The development order deliberately postpones full operational hardening, GUI work, scheduling, and packaging until the core processing layers work. However, production-data safety, secure secret handling, testability, and correct successful-state semantics must be respected from the beginning.
