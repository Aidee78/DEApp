# AGENTS.md --- DEApp

## 1. Project purpose

DEApp (Data Extraction Application) is a Windows-based Python
application that processes four defined types of emails from Zoho Mail,
extracts and validates their data, updates an Excel workbook stored in
Dropbox, and records successful execution state.

Do not modify any file in this codebase without my permission and review, no matter what. Alway let me know if a step requires modification of the codebase.

The intended production workflow is:

1.  Load and validate configuration.
2.  Determine the processing date range.
3.  Prevent concurrent application instances.
4.  Authenticate with Zoho and retrieve the required emails.
5.  Parse emails and validate extracted data.
6.  Download the target workbook from Dropbox to a local working
    location.
7.  Update the local workbook using `xlwings` and Microsoft Excel.
8.  Validate the updated workbook.
9.  Upload the workbook to Dropbox only after processing and validation
    succeed.
10. Record successful execution state only after the upload succeeds.
11. Report completion and exit with an appropriate status.

The application must support manual command-line execution and scheduled
execution through Windows Task Scheduler. The longer-term deployment
target is a Windows executable.

## 2. How to work in this repository

-   Treat this file and the approved development plan in
    `docs/DEVELOPMENT_PLAN.md` as project guidance. If they conflict
    with an explicit, newer instruction from the user, follow the newer
    instruction and update the relevant documentation when appropriate.
-   Before changing code, inspect the relevant implementation, tests,
    configuration, and documentation. Do not assume a file is
    implemented just because it exists.
-   Work incrementally. Prefer the smallest coherent change that
    advances the current phase.
-   Preserve the existing modular architecture. Do not replace it with a
    simplified or monolithic design without explicit approval.
-   Do not implement future phases merely because they appear in the
    roadmap. Work on the current task and its necessary dependencies.
-   Do not claim that a feature works unless the implementation has been
    inspected and relevant tests or checks have been run.
-   Distinguish clearly between documented requirements, implemented
    behavior, assumptions, and unresolved business decisions.
-   If a requirement is ambiguous and could affect business data,
    workbook contents, date boundaries, or production behavior, identify
    the ambiguity and ask for clarification rather than inventing a
    rule.
-   Do not make unrelated changes, broad refactors, or formatting-only
    edits outside the requested scope.
-   Never overwrite the user's work. Inspect the working tree and
    existing changes before editing; preserve unrelated modifications.

## 3. Development roadmap

The current proposed development order is:

1.  **Project Foundation and Configuration** --- project setup,
    settings, secrets boundaries, startup validation.
2.  **CLI, Dates and Execution State** --- command-line arguments, date
    resolution, persistent successful-execution state.
3.  **Zoho Authentication and Mail Integration** --- OAuth/token
    management, mail search and retrieval.
4.  **Email Models, Parsing and Business Logic** --- structured models,
    four dedicated parsers, extraction validation.
5.  **Dropbox and Excel Integration** --- Dropbox operations, local
    workbook handling, `xlwings`, workbook validation.
6.  **End-to-End Application Workflow** --- orchestration and safe
    workbook transaction.
7.  **Reliability, Logging, Error Handling and GUI** --- application
    locking, diagnostics, Tkinter status interface, recovery behavior.
8.  **Documentation, Scheduling, Packaging and Deployment** --- Task
    Scheduler, Windows executable, production verification.

Use the roadmap as a sequence of increasing complexity, not as
permission to skip tests or introduce unverified behavior. Confirm with
the user before replacing the existing committed development plan if the
change has not already been approved.

## 4. Architecture and separation of concerns

Keep responsibilities separated according to the existing package
structure. Prefer extending existing modules over introducing parallel
implementations.

-   `application/`: orchestration, workflow, and application-level
    exceptions.
-   `cli/`: command-line parsing and argument validation.
-   `config/`: loading and validating ordinary settings and
    environment-based secrets.
-   `gui/`: display and user interaction only; do not place business
    logic here.
-   `locking/`: single-instance coordination.
-   `logging/`: centralized logging setup.
-   `models/`: typed application data structures.
-   `parsers/`: one dedicated parser per target email type.
-   `services/zoho/`: Zoho OAuth and Mail API integration.
-   `services/dropbox/`: Dropbox authentication and file transfer.
-   `services/excel/`: workbook opening, updating, saving, and
    validation.
-   `state/`: persistent state for previous successful executions.
-   `utils/`: small, reusable helpers with a clear purpose.

Keep parsers independent of Zoho API calls, Dropbox file operations,
Excel modification, GUI behavior, and scheduling. Parsers should
transform email content into structured data and report invalid or
incomplete input clearly.

Keep service integrations behind clear interfaces so their behavior can
be tested independently. Avoid circular imports and avoid making modules
depend on GUI state.

## 5. Python and code quality

-   Use Python 3.14-compatible code and type annotations throughout new
    and modified code.
-   Add useful docstrings to modules, public classes, and public
    functions. Explain intent, contracts, and non-obvious behavior
    rather than restating the function name.
-   Add comments when they explain *why* a decision or safeguard exists;
    avoid comments that merely narrate the code.
-   Prefer small functions with explicit inputs and outputs.
-   Use descriptive names and consistent formatting.
-   Handle expected errors explicitly. Do not silently swallow
    exceptions or use broad exception handling without a clear reason
    and appropriate reporting.
-   Avoid unnecessary dependencies. Update `pyproject.toml` when
    dependencies genuinely change, and keep dependency declarations
    consistent with imports and packaging.
-   Keep configuration examples, README instructions, tests, and other
    documentation synchronized with behavior changes.
-   Do not log secrets, access tokens, refresh tokens, authorization
    codes, or sensitive email contents.
-   Do not add credentials or real customer data to tests, fixtures,
    screenshots, logs, or documentation.

## 6. Configuration, secrets, and state

-   Keep ordinary settings in the appropriate configuration file and
    credentials in environment-based secret configuration or an
    explicitly approved secure store.
-   `.env.example` may contain variable names and safe placeholders
    only. Never commit `.env` or real credentials.
-   Validate required settings at startup and identify missing setting
    names without printing their values.
-   Keep runtime state separate from configuration.
-   Treat `data/state.json` as application state, not as a source of
    configuration.
-   Update the last-successful-execution state only after the required
    processing has completed and the Dropbox upload has succeeded.
-   Handle missing, malformed, or unreadable state files explicitly. Do
    not silently reset state in a way that could skip or duplicate
    processing.
-   Make state writes robust against partial writes where practical.

## 7. Email retrieval, date ranges, and parsing

-   Use deterministic rules to identify each of the four target email
    types. Do not guess sender, subject, folder, or date criteria.
-   Preserve the exact source data needed to validate extraction, but
    avoid unnecessary retention of sensitive email content.
-   Validate required fields and data types before passing extracted
    data to Excel.
-   Make missing emails, multiple matches, duplicate messages, malformed
    content, and API failures explicit outcomes governed by documented
    business rules.
-   Do not silently drop invalid records or fabricate missing values.
-   Apply the approved extracted activity-record consolidation rules in
    `docs/RECORD_CONSOLIDATION.md`. These rules do not define duplicate
    workbook-row or repeated-processing behavior.
-   Keep date parsing and date-range resolution centralized.
-   Do not assume whether date ranges or the last successful date are
    inclusive or exclusive. Follow the finalized business rule and test
    boundary cases.
-   Ensure manual date overrides are validated and passed consistently
    through the workflow.

## 8. Excel and Dropbox safety --- critical requirements

The production workbook is important business data. Preserve these
invariants in every change:

1.  Download the workbook and perform modifications on a local working
    copy.
2.  Do not modify the production Dropbox workbook while parsing or
    editing locally.
3.  Validate extracted data before workbook modification.
4.  Validate the updated workbook before upload.
5.  Upload only when all required processing and workbook validation
    steps succeed.
6.  Record successful execution state only after the upload succeeds.
7.  On failures before upload, do not upload the local working copy.
8.  On upload failure, do not record the execution as successful.
9.  Clean up temporary files and close Excel workbooks/process resources
    safely.
10. Avoid duplicate or destructive workbook updates on retries.

Do not assume the workbook's sheet names, columns, tables, cell ranges,
formulas, formatting, or append/overwrite rules. Inspect the actual
workbook or obtain explicit requirements before implementing changes to
its structure.

Use test workbooks and a clearly configured test Dropbox location for
integration tests. Tests must not accidentally overwrite the production
workbook.

Because `xlwings` automates Microsoft Excel, account for the target
machine's Excel installation, workbook locks, Excel process cleanup, and
Windows-specific behavior.

## 9. Workflow, failure handling, and concurrency

-   Keep the application workflow responsible for sequencing components
    and enforcing business invariants.
-   Keep individual service modules responsible for their
    external-system operations.
-   Define failure behavior for each major stage and report failures
    with useful context.
-   Do not continue into workbook upload when required retrieval,
    parsing, validation, or workbook operations fail.
-   Use explicit application exceptions and consistent exit codes where
    appropriate.
-   Prevent concurrent DEApp instances from processing the same date
    range or workbook.
-   Ensure the application lock is released on normal completion and
    handled safely after abnormal termination.
-   Design retries to avoid data loss, duplicate workbook updates, and
    incorrect execution-state advancement.
-   GUI closure or cancellation must never cause an unvalidated workbook
    to be uploaded.

## 10. Logging and user interface

-   Use centralized structured logging rather than `print()` statements
    for production diagnostics.
-   Include timestamps, useful workflow context, and exception details
    without exposing secrets or unnecessary email content.
-   Configure console logging for development and file logging for
    operational diagnosis.
-   Define log retention/rotation rather than allowing logs to grow
    without limit.
-   Keep the Tkinter GUI focused on progress, status, and user-facing
    errors.
-   The GUI must not own or duplicate business logic. Scheduled and
    manual execution should use the same underlying workflow.

## 11. Testing expectations

Add or update tests with every meaningful behavior change.

-   Unit-test pure logic such as argument parsing, date handling,
    models, parser behavior, validation, and state management.
-   Test failure cases as well as successful cases.
-   Use mocks or fakes for external services in unit tests.
-   Keep integration tests explicitly configured and safe to run.
-   Do not rely on production credentials, a production Dropbox
    workbook, or live customer email content in ordinary test runs.
-   Test transaction invariants, including no upload after pre-upload
    failure and no success-state update after upload failure.
-   Test boundary dates, missing messages, duplicate matches, malformed
    email content, invalid workbook structures, and token refresh
    failures as relevant.
-   Test activity-record consolidation using the exact record type, key
    values and flags, missing-value precedence, officer-name de-duplication,
    latest `received_at`, and tied-conflict behavior.
-   Run the narrowest relevant test suite first, followed by broader
    checks when feasible.
-   Report which commands were run and whether they passed. If a test
    cannot be run because of the environment, state that limitation
    rather than implying success.

## 12. Documentation requirements

-   Update documentation when behavior, configuration, commands,
    dependencies, or architecture changes.
-   Document configuration variables without including real secret
    values.
-   Keep setup and execution instructions accurate for the actual
    implementation.
-   Mark unresolved business decisions explicitly; do not present
    assumptions as settled requirements.
-   Avoid claiming that a phase is complete unless its acceptance
    criteria have been met and verified.

## 13. Git and change management

-   Inspect `git status` and relevant diffs before editing or proposing
    commits.
-   Preserve unrelated user changes.
-   Do not reset, clean, force-push, rewrite history, or discard user
    changes unless explicitly instructed.
-   Do not commit, push, create releases, or modify remote repository
    settings unless the user requests that action.
-   Keep changes focused and review the final diff for unintended
    modifications.
-   Do not add generated files, secrets, local state, logs, or temporary
    workbook copies to version control.

## 14. Working procedure for each task

For each implementation task:

1.  Identify the relevant roadmap phase and acceptance criteria.
2.  Inspect the relevant source files, tests, configuration, and
    documentation.
3.  State important ambiguities or risks before making consequential
    assumptions.
4.  Implement the smallest coherent change while preserving
    architecture.
5.  Add or update tests.
6.  Run relevant tests and static checks available in the project.
7.  Inspect the final diff for regressions, unrelated edits, secrets,
    and documentation drift.
8.  Summarize what changed, what was verified, and any remaining issues.

Do not merely provide commands for the user to copy when the task asks
for code changes and the repository tools permit the changes. When
making changes, explain important design decisions and verification
results concisely.

## 15. Business decisions that must not be invented

Unless they are explicitly resolved in project documentation or by the
user, do not invent:

-   The identification criteria for the four email types.
-   Required fields and extraction rules for each email.
-   Behavior when expected emails are missing or multiple messages
    match.
-   Workbook duplicate-row and repeated-processing rules.
-   Resolution for conflicting field values tied on both flag and
    `received_at`; the current consolidator raises an error for this case.
-   The Excel workbook path, sheet names, columns, tables, or cell
    ranges.
-   Whether workbook data is appended, overwritten, or otherwise
    transformed.
-   Date-range inclusivity and last-successful-date semantics.
-   Production secret-storage requirements.
-   Logging retention requirements.
-   GUI cancellation behavior beyond the safety requirement that
    cancellation must not upload invalid work.
-   Production scheduling and deployment settings beyond the stated
    daily target.

The extracted activity-record consolidation rule is specified in
`docs/RECORD_CONSOLIDATION.md`. Keep workbook duplicate-row behavior and
the exact flag/`received_at` tie case explicitly unresolved until decided.

When a decision blocks safe implementation, ask a focused question and
explain why the answer matters.
