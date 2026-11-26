"""Application exception hierarchy for expected, actionable DEApp failures."""


class ApplicationError(Exception):
    """Base class for expected DEApp failures.

    Messages passed to this class and its subclasses may be shown to users and
    written to logs, so they must not contain credentials or email contents.
    """


class InputError(ApplicationError, ValueError):
    """Base for invalid configuration, dates, and extracted input data."""


class ConfigurationError(InputError):
    """Raised when application settings or required environment values are invalid."""


class DateRangeError(InputError):
    """Raised when a requested processing date or date range is invalid."""


class ParsingError(InputError):
    """Raised when source email content cannot be parsed safely."""


class SelectionError(InputError):
    """Raised when message-selection rules are invalid or ambiguous to configure."""


class DataValidationError(InputError):
    """Raised when extracted or reconciled application data is invalid."""


class RecordTypeError(ApplicationError, TypeError):
    """Raised when an API receives an object of an unsupported record type."""


class ReconciliationError(DataValidationError):
    """Raised when conflicting record values cannot be resolved safely."""


class StateError(ApplicationError):
    """Raised when persistent execution state cannot be read or written."""


class LockError(ApplicationError):
    """Raised when application-instance coordination fails."""


class InstanceAlreadyRunningError(LockError):
    """Raised when another DEApp process already owns the application lock."""


class LoggingError(ApplicationError):
    """Raised when DEApp logging cannot be initialized."""


class WorkflowError(ApplicationError):
    """Raised when the application workflow cannot safely continue."""


class IntegrationError(ApplicationError, RuntimeError):
    """Base for expected failures while communicating with an external service."""


class ZohoError(IntegrationError):
    """Base for Zoho integration failures."""


class ZohoAuthenticationError(ZohoError):
    """Raised when Zoho cannot provide usable OAuth tokens."""


class ZohoMailError(ZohoError):
    """Raised when a Zoho Mail API operation fails."""


class DropboxError(IntegrationError):
    """Raised when a Dropbox operation fails."""


class DropboxConflictError(DropboxError):
    """Raised when the remote workbook changed after it was downloaded."""


class WorkbookError(ApplicationError):
    """Base for workbook access, modification, and validation failures."""


class ExcelWriteError(WorkbookError):
    """Raised when a workbook cannot be opened, updated, saved, or closed."""
