"""Group activity records and resolve field inconsistencies by email time."""

from collections.abc import Iterable
from dataclasses import fields, is_dataclass, replace
from datetime import datetime
from typing import Any, TypeVar, cast

from deapp.application.exceptions import (
    RecordTypeError,
    ReconciliationError,
)
from deapp.models.excel.field import FieldFlag, FlaggedValue


T = TypeVar("T")
_ACTIVITY_KEY_FIELDS = ("date", "shift", "batch_number")
CONSISTENT_FLAG: FieldFlag = 0
INCONSISTENT_FLAG: FieldFlag = 3

RecordT = TypeVar("RecordT")
Candidate = tuple[FlaggedValue[Any], Any]

_TIME_FIELDS = ("start_time", "end_time", "stop_time")
_MEASURE_FIELDS = (
    "quantity_kg",
    "output",
    "quantity_tabs",
    "drums",
    "coarse_percent",
    "powder_percent",
    "number_of_cartons",
)

def remove_duplicates(records: Iterable[T]) -> list[T]:
    """Return distinct records in their original order."""
    unique: list[T] = []

    for record in records:
        if record not in unique:
            unique.append(record)

    return unique


def consolidate_records(records: Iterable[RecordT]) -> list[RecordT]:
    """Merge complete-key records only when their report types differ."""
    groups: list[tuple[bool, list[RecordT]]] = []
    group_positions: dict[tuple[Any, ...], int] = {}

    for record in records:
        if not is_dataclass(record) or isinstance(record, type):
            raise RecordTypeError("Each record must be a dataclass instance.")

        key: list[Any] = [type(record)]
        has_complete_activity_key = True

        for name in ("date", "shift", "batch_number"):
            value = getattr(record, name, None)
            if not isinstance(value, FlaggedValue):
                raise RecordTypeError(
                    f"Record field {name!r} must be a FlaggedValue."
                )
            if value.value is None:
                has_complete_activity_key = False
            key.extend((value.value, value.flag))
                
        if not has_complete_activity_key:
            # Keep incomplete-key records as individual, unchanged records.
            groups.append((False, [record]))
            continue

        group_key = tuple(key)
        position = group_positions.get(group_key)
        if position is None:
            group_positions[group_key] = len(groups)
            groups.append((True, [record]))
        else:
            groups[position][1].append(record)

    def newest(candidates: list[Candidate]) -> list[Candidate]:
        latest_time = max(record.received_at for _, record in candidates)
        return [
            (value, record)
            for value, record in candidates
            if record.received_at == latest_time
        ]

    def choose_field(candidates: list[Candidate]) -> FlaggedValue[Any]:
        populated = [
            (value, record)
            for value, record in candidates
            if value.value is not None
        ]
        flag_conflict = len({value.flag for value, _ in candidates}) > 1

        # If every value is None, keep the latest record's field unless the
        # input flags conflict.
        if not populated:
            finalists = newest(candidates)
            chosen = finalists[0][0]
            if flag_conflict:
                return replace(chosen, flag=INCONSISTENT_FLAG)
            return chosen

        # Any comparison involving a populated value is marked inconsistent.
        # If the latest timestamps tie, input order chooses the first value.
        latest_time = max(record.received_at for _, record in populated)
        chosen = next(
            value
            for value, record in populated
            if record.received_at == latest_time
        )
        return replace(chosen, flag=INCONSISTENT_FLAG)

    consolidated: list[RecordT] = []

    for can_consolidate, group in groups:
        if not can_consolidate:
            consolidated.append(group[0])
            continue

        report_types = {
            getattr(record, "report_type", None)
            for record in group
        }
        if len(report_types) < 2:
            # Repeated records from one report type remain separate.
            consolidated.extend(group)
            continue

        updates: dict[str, Any] = {}
        updates["report_type"] = None

        for record_field in fields(group[0]):
            name = record_field.name
            if name in {"received_at", "report_type"}:
                continue

            candidates: list[Candidate] = []
            for record in group:
                value = getattr(record, name)
                if not isinstance(value, FlaggedValue):
                    raise RecordTypeError(
                        f"Record field {name!r} must be a FlaggedValue."
                    )
                candidates.append((value, record))

            updates[name] = choose_field(candidates)

        updates["received_at"] = max(record.received_at for record in group)
        consolidated.append(cast(RecordT, replace(group[0], **updates)))

    return consolidated

def _all_present_fields_are_empty_flagged_1(
    record: object,
    field_names: tuple[str, ...],
) -> bool:
    """Return whether at least one listed field exists and all such fields are empty."""
    present_fields: list[FlaggedValue[object]] = []

    for name in field_names:
        if not hasattr(record, name):
            continue

        value = getattr(record, name)
        if not isinstance(value, FlaggedValue):
            raise RecordTypeError(
                f"Record field {name!r} must be a FlaggedValue."
            )

        present_fields.append(value)

    # An absent field group should not count as empty.
    return bool(present_fields) and all(
        value.value is None and value.flag == 1
        for value in present_fields
    )


def remove_completely_empty_records(records: Iterable[RecordT]) -> list[RecordT]:
    """Remove completely empty unbatched records and order the rest by receipt time."""
    kept: list[tuple[datetime, RecordT]] = []

    for record in records:
        if not is_dataclass(record) or isinstance(record, type):
            raise RecordTypeError("Each record must be a dataclass instance.")

        batch_number = getattr(record, "batch_number", None)
        if not isinstance(batch_number, FlaggedValue):
            raise RecordTypeError(
                "Record field 'batch_number' must be a FlaggedValue."
            )

        received_at = getattr(record, "received_at", None)
        if not isinstance(received_at, datetime):
            raise RecordTypeError(
                "Record field 'received_at' must be a datetime."
            )

        should_remove = (
            batch_number.value is None
            and batch_number.flag == 1
            and _all_present_fields_are_empty_flagged_1(record, _TIME_FIELDS)
            and _all_present_fields_are_empty_flagged_1(record, _MEASURE_FIELDS)
        )

        if not should_remove:
            kept.append((received_at, record))

    # Python's sort is stable, so equal timestamps retain their input order.
    kept.sort(key=lambda entry: entry[0])
    return [record for _, record in kept]
