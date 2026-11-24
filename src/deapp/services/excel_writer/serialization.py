"""Convert application values into representations accepted by Excel."""

from datetime import time


_SECONDS_PER_DAY = 24 * 60 * 60


def to_excel_value(value: object) -> object:
    """Convert time-only values to Excel's fraction-of-a-day representation.

    Excel stores a time as a fraction of one day. The conversion happens at
    the Excel service boundary so application records keep their ``time`` type.
    """
    if isinstance(value, time):
        seconds = (
            value.hour * 60 * 60
            + value.minute * 60
            + value.second
            + value.microsecond / 1_000_000
        )
        return seconds / _SECONDS_PER_DAY

    return value
