"""Tests for values serialized at the Excel writer boundary."""

from datetime import datetime, time
from types import SimpleNamespace

import pytest

from deapp.models.excel.field import FlaggedValue
from deapp.services.excel_writer.serialization import to_excel_value
from deapp.services.excel_writer.writer import ExcelManager


def test_to_excel_value_converts_time_to_fraction_of_day() -> None:
    """A clock time becomes the numeric fraction Excel stores for that time."""
    assert to_excel_value(time(12, 18)) == pytest.approx(0.5125)


@pytest.mark.parametrize(
    "value",
    [None, datetime(2026, 11, 23), "label", 12.5],
)
def test_to_excel_value_preserves_values_that_are_not_times(
    value: object,
) -> None:
    """Dates and ordinary cell values pass through without conversion."""
    assert to_excel_value(value) is value


def test_blending_writer_serializes_time_fields_before_cell_write() -> None:
    """Blending clock and duration values are serialized before cell writes."""
    fields = {
        name: FlaggedValue(None)
        for name in (
            "date",
            "line",
            "product",
            "batch_number",
            "officer",
            "start_time",
            "stop_time",
            "idle_time",
            "quantity_kg",
            "drums",
            "status",
            "remarks",
        )
    }
    fields["start_time"] = FlaggedValue(time(12, 18), 0)
    fields["stop_time"] = FlaggedValue(time(13, 0), 1)
    fields["idle_time"] = FlaggedValue(time(0, 30), 2)
    record = SimpleNamespace(**fields)

    manager = ExcelManager.__new__(ExcelManager)
    manager._get_worksheet = lambda worksheet: object()
    manager._next_row = lambda **kwargs: 12
    written_fields: dict[str, tuple[int, FlaggedValue]] = {}
    manager._write_cell = lambda ws, col, row, field: written_fields.__setitem__(
        col,
        (row, field),
    )

    manager.write_blending_record(record)

    assert written_fields["F"][0] == 12
    assert written_fields["F"][1].value == pytest.approx(0.5125)
    assert written_fields["F"][1].flag == 0
    assert written_fields["G"][1].value == pytest.approx(13 / 24)
    assert written_fields["G"][1].flag == 1
    assert written_fields["H"][1].value == pytest.approx(0.5 / 24)
    assert written_fields["H"][1].flag == 2
