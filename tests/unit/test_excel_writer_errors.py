"""Tests that the Excel writer reports failures through DEApp exceptions."""

from types import SimpleNamespace

import pytest

from deapp.application.exceptions import ExcelWriteError
from deapp.services.excel_writer.writer import ExcelManager


def test_missing_worksheet_raises_excel_write_error() -> None:
    """A worksheet lookup failure reaches the caller with safe context."""
    manager = ExcelManager.__new__(ExcelManager)
    manager.workbook = SimpleNamespace(sheets={})

    with pytest.raises(ExcelWriteError, match="Could not find worksheet") as error:
        manager._get_worksheet("Missing")

    assert isinstance(error.value.__cause__, KeyError)


def test_blending_write_failure_is_wrapped_and_propagated() -> None:
    """A failed table operation must not be swallowed as a successful write."""
    manager = ExcelManager.__new__(ExcelManager)

    def fail_to_find_row(**kwargs) -> int:
        raise RuntimeError("untrusted Excel error details")

    manager._get_worksheet = lambda worksheet: object()
    manager._next_row = fail_to_find_row

    with pytest.raises(
        ExcelWriteError,
        match="Could not write the blending record",
    ) as error:
        manager.write_blending_record(SimpleNamespace())

    assert isinstance(error.value.__cause__, RuntimeError)
    assert "untrusted Excel error details" not in str(error.value)


def test_close_failure_still_closes_workbook_and_excel_app() -> None:
    """Cleanup attempts every owned resource and reports its first failure."""
    class FakeWorkbook:
        closed = False

        def save(self) -> None:
            raise RuntimeError("save failure")

        def close(self) -> None:
            self.closed = True

    class FakeExcelApp:
        quit_called = False

        def quit(self) -> None:
            self.quit_called = True

    workbook = FakeWorkbook()
    excel_app = FakeExcelApp()
    manager = ExcelManager.__new__(ExcelManager)
    manager._closed = False
    manager._owns_workbook = True
    manager._owns_excel_app = True
    manager.workbook = workbook
    manager.excel_app = excel_app

    with pytest.raises(ExcelWriteError) as error:
        manager.close_workbook(save=True)

    assert isinstance(error.value.__cause__, RuntimeError)
    assert workbook.closed
    assert excel_app.quit_called
    assert manager._closed


def test_unimplemented_record_writer_fails_explicitly() -> None:
    """Unimplemented record types cannot silently appear to succeed."""
    manager = ExcelManager.__new__(ExcelManager)

    with pytest.raises(ExcelWriteError, match="not implemented"):
        manager.write_coating_record(SimpleNamespace())
