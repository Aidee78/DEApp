"""Shared value and quality flag for extracted Excel record fields."""

from dataclasses import dataclass, field
from typing import Generic, Literal, TypeVar


T = TypeVar("T")
FieldFlag = Literal[0, 3]


@dataclass(frozen=True, slots=True)
class FlaggedValue(Generic[T]):
    """Store a field's value and its inconsistency status.

    Equality intentionally compares only ``value`` so flags describe data
    quality without changing value comparisons or record identity.
    """

    value: T
    flag: FieldFlag = field(default=0, compare=False)

    def __post_init__(self) -> None:
        """Reject flag codes outside the currently defined status values."""
        if self.flag not in (0, 3):
            raise ValueError("Field flag must be 0 (consistent) or 3 (inconsistent).")
