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

_TIME_FIELDS = ("start_time", "end_time", "stop_time", "idle_time")
_MEASURE_FIELDS = (
    "quantity_kg",
    "output",
    "quantity_tabs",
    "drums",
    "coarse_percent",
    "powder_percent",
    "number_of_cartons",
    "number_of_packs",
    "number_of_bundles",
    "number_of_pieces",
)


def remove_duplicates(records: Iterable[T]) -> list[T]:
    """Return distinct records in their original order."""
    unique: list[T] = []

    for record in records:
        if record not in unique:
            unique.append(record)

    return unique


def consolidate_records(records: Iterable[RecordT]) -> list[RecordT]:
    """Apply the same-time blending pass, then merge cross-report records.

    Activity keys match by their values, regardless of key-field flags.
    Records with an incomplete key remain separate.
    """
    from deapp.models.excel.blending import BlendingRecord

    record_list: list[RecordT] = []
    for record in records:
        if not is_dataclass(record) or isinstance(record, type):
            raise TypeError("Each record must be a dataclass instance.")
        record_list.append(record)

    def activity_key(record: RecordT) -> tuple[Any, ...] | None:
        """Return the value-based key, or None when the key is incomplete."""
        key: list[Any] = [type(record)]

        for name in _ACTIVITY_KEY_FIELDS:
            value = getattr(record, name, None)
            if not isinstance(value, FlaggedValue):
                raise TypeError(f"Record field {name!r} must be a FlaggedValue.")
            if value.value is None:
                return None
            key.append(value.value)

        return tuple(key)

    def merge_fields(
        first: RecordT,
        second: RecordT,
        *,
        same_report_same_time: bool = False,
    ) -> RecordT:
        """Merge two records using the Stage 1 and Stage 2 field rules."""
        updates: dict[str, Any] = {}
        latest = second if second.received_at >= first.received_at else first

        for record_field in fields(first):
            name = record_field.name
            if name in {"received_at", "report_type"}:
                continue

            left = getattr(first, name)
            right = getattr(second, name)

            if not isinstance(left, FlaggedValue) or not isinstance(
                right, FlaggedValue
            ):
                raise TypeError(f"Record field {name!r} must be a FlaggedValue.")

            if same_report_same_time:
                # Stage 1: the last processed record's field wins.
                updates[name] = right
                continue

            if name == "remarks":
                if left.value is None and right.value is None:
                    updates[name] = FlaggedValue(
                        None, max(left.flag, right.flag)
                    )
                elif left.value is None:
                    updates[name] = right
                elif right.value is None:
                    updates[name] = left
                else:
                    updates[name] = FlaggedValue(
                        f"{left.value}. {right.value}",
                        0,
                    )
                continue

            if name == "officer":
                if left.value is None and right.value is None:
                    updates[name] = FlaggedValue(
                        None, max(left.flag, right.flag)
                    )
                elif left.value is None:
                    updates[name] = right
                elif right.value is None:
                    updates[name] = left
                else:
                    names: list[str] = []
                    for source in (left.value, right.value):
                        for officer_name in source.split(","):
                            officer_name = officer_name.strip()
                            if officer_name and officer_name not in names:
                                names.append(officer_name)

                    updates[name] = FlaggedValue(
                        ", ".join(names),
                        min(left.flag, right.flag),
                    )
                continue

            if left.value is None and right.value is None:
                updates[name] = FlaggedValue(
                    None, max(left.flag, right.flag)
                )
            elif left.value is None:
                updates[name] = right
            elif right.value is None:
                updates[name] = left
            elif left.value == right.value:
                updates[name] = FlaggedValue(
                    left.value,
                    min(left.flag, right.flag),
                )
            else:
                # Different populated values use the latest value and flag 3.
                selected = getattr(latest, name)
                updates[name] = FlaggedValue(selected.value, 3)

        updates["received_at"] = latest.received_at
        updates["report_type"] = latest.report_type

        return cast(RecordT, replace(first, **updates))

    # Stage A: combine same-key BlendingRecords from the same report and
    # identical receipt timestamp. Sequential folding makes input order the
    # tie-breaker when more than two records match.
    stage_a: list[RecordT] = []
    blending_positions: dict[tuple[Any, ...], int] = {}

    for record in record_list:
        key = activity_key(record)
        if (
            key is None
            or not isinstance(record, BlendingRecord)
            or not hasattr(record, "report_type")
        ):
            stage_a.append(record)
            continue

        stage_a_key = (*key, record.report_type, record.received_at)
        position = blending_positions.get(stage_a_key)

        if position is None:
            blending_positions[stage_a_key] = len(stage_a)
            stage_a.append(record)
        else:
            stage_a[position] = merge_fields(
                stage_a[position],
                record,
                same_report_same_time=True,
            )

    # return stage_a

    # Stage B: group remaining complete-key records and merge only when
    # multiple report types are represented.
    groups: list[list[RecordT]] = []
    group_positions: dict[tuple[Any, ...], int] = {}

    for record in stage_a:
        key = activity_key(record)
        if key is None:
            groups.append([record])
            continue

        position = group_positions.get(key)
        if position is None:
            group_positions[key] = len(groups)
            groups.append([record])
        else:
            groups[position].append(record)

    consolidated: list[RecordT] = []

    for group in groups:
        report_types = {getattr(record, "report_type", None) for record in group}

        # A group consolidates only across distinct report types.
        if len(report_types) < 2:
            consolidated.extend(group)
            continue

        merged = group[0]
        for record in group[1:]:
            merged = merge_fields(merged, record)

        consolidated.append(merged)

    return consolidated


def _all_present_fields_are_empty(
    record: object,
    field_names: tuple[str, ...],
    *,
    require_flag_one: bool = True,
) -> bool:
    """Return whether every present field meets the selected empty rule."""
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
        value.value is None and (not require_flag_one or value.flag == 1)
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
            (batch_number.value is None
            and batch_number.flag == 1)
            and _all_present_fields_are_empty(
                record,
                _TIME_FIELDS,
                require_flag_one=False,
            )
            and _all_present_fields_are_empty(record, _MEASURE_FIELDS)
        )

        if not should_remove:
            kept.append((received_at, record))

    # Python's sort is stable, so equal timestamps retain their input order.
    kept.sort(key=lambda entry: entry[0])
    return [record for _, record in kept]
