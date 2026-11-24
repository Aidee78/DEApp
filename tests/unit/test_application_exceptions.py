"""Checks for DEApp's public application exception hierarchy."""

import pytest

from deapp.application.exceptions import (
    ApplicationError,
    ConfigurationError,
    DataValidationError,
    DateRangeError,
    DropboxError,
    ExcelWriteError,
    InputError,
    InstanceAlreadyRunningError,
    IntegrationError,
    LockError,
    LoggingError,
    ParsingError,
    RecordTypeError,
    ReconciliationError,
    SelectionError,
    StateError,
    WorkflowError,
    WorkbookError,
    ZohoAuthenticationError,
    ZohoError,
    ZohoMailError,
)


APPLICATION_EXCEPTION_TYPES = (
    InputError,
    ConfigurationError,
    DateRangeError,
    ParsingError,
    SelectionError,
    DataValidationError,
    RecordTypeError,
    ReconciliationError,
    StateError,
    LockError,
    InstanceAlreadyRunningError,
    LoggingError,
    WorkflowError,
    IntegrationError,
    ZohoError,
    ZohoAuthenticationError,
    ZohoMailError,
    DropboxError,
    WorkbookError,
    ExcelWriteError,
)


@pytest.mark.parametrize("error_type", APPLICATION_EXCEPTION_TYPES)
def test_domain_exceptions_share_application_base(error_type: type[Exception]) -> None:
    """Every DEApp-defined failure can be handled at the application boundary."""
    assert issubclass(error_type, ApplicationError)


def test_input_errors_preserve_value_error_compatibility() -> None:
    """Existing callers that catch ValueError still handle invalid inputs."""
    assert issubclass(ConfigurationError, ValueError)
    assert issubclass(DateRangeError, ValueError)
    assert issubclass(ReconciliationError, ValueError)


def test_external_and_record_errors_preserve_builtin_compatibility() -> None:
    """Service and record errors retain their former built-in categories."""
    assert issubclass(ZohoAuthenticationError, RuntimeError)
    assert issubclass(ZohoMailError, RuntimeError)
    assert issubclass(RecordTypeError, TypeError)
