"""Group activity records and resolve field inconsistencies by email time."""

from collections.abc import Iterable
from dataclasses import fields, is_dataclass, replace
from datetime import datetime
from typing import Any, TypeVar, cast

from deapp.models.excel.field import FieldFlag, FlaggedValue


T = TypeVar("T")
_ACTIVITY_KEY_FIELDS = ("date", "shift", "batch_number")
CONSISTENT_FLAG: FieldFlag = 0
INCONSISTENT_FLAG: FieldFlag = 3


class ReconciliationError(ValueError):
    """Raised when conflicting values cannot be ordered safely."""



RecordT = TypeVar("RecordT")
Candidate = tuple[FlaggedValue[Any], Any]


def consolidate_records(records: Iterable[RecordT]) -> list[RecordT]:
    """Merge matching records only when every activity key value is present."""
    groups: list[tuple[bool, list[RecordT]]] = []
    group_positions: dict[tuple[Any, ...], int] = {}

    for record in records:
        if not is_dataclass(record) or isinstance(record, type):
            raise TypeError("Each record must be a dataclass instance.")

        key: list[Any] = [type(record)]
        has_complete_activity_key = True

        for name in ("date", "shift", "batch_number"):
            value = getattr(record, name, None)
            if not isinstance(value, FlaggedValue):
                raise TypeError(f"Record field {name!r} must be a FlaggedValue.")
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
        value_conflict = any(
            value.value != candidates[0][0].value
            for value, _ in candidates[1:]
        )

        # If every value is None, use the latest record's flag unless an input
        # flag conflicts, in which case mark the consolidated field inconsistent.
        if not populated:
            finalists = newest(candidates)
            chosen = finalists[0][0]
            if flag_conflict or value_conflict:
                return replace(chosen, flag=INCONSISTENT_FLAG)
            return chosen

        # Otherwise, non-None values take priority, then the lowest flag.
        lowest_flag = min(value.flag for value, _ in populated)
        finalists = newest([
            (value, record)
            for value, record in populated
            if value.flag == lowest_flag
        ])

        chosen = finalists[0][0]
        if flag_conflict or value_conflict:
            # If priority and timestamp both tie, keep the first candidate's
            # value while flagging the disagreement as inconsistent.
            return replace(chosen, flag=INCONSISTENT_FLAG)
        return chosen

    def merge_officers(candidates: list[Candidate]) -> FlaggedValue[Any]:
        populated = [
            (value, record)
            for value, record in candidates
            if value.value is not None
        ]
        if not populated:
            return choose_field(candidates)
        flag_conflict = len({value.flag for value, _ in candidates}) > 1

        # Officer names are combined, and only differing input flags make the
        # consolidated officer field inconsistent.
        lowest_flag = min(value.flag for value, _ in populated)
        finalists = newest([
            (value, record)
            for value, record in populated
            if value.flag == lowest_flag
        ])
        chosen = finalists[0][0]

        # Split existing comma-separated names, trim whitespace, and keep
        # the first occurrence of each name.
        names: list[str] = []
        seen: set[str] = set()

        for value, _ in populated:
            if not isinstance(value.value, str):
                raise TypeError("Officer values must be strings or None.")

            for part in value.value.split(","):
                name = part.strip()
                if name and name not in seen:
                    seen.add(name)
                    names.append(name)

        if not names:
            return choose_field(candidates)

        result_flag = (
            INCONSISTENT_FLAG
            if flag_conflict
            else chosen.flag
        )
        return replace(chosen, value=", ".join(names), flag=result_flag)

    consolidated: list[RecordT] = []

    for can_consolidate, group in groups:
        if not can_consolidate:
            consolidated.append(group[0])
            continue

        updates: dict[str, Any] = {}

        for record_field in fields(group[0]):
            name = record_field.name
            if name == "received_at":
                continue

            candidates: list[Candidate] = []
            for record in group:
                value = getattr(record, name)
                if not isinstance(value, FlaggedValue):
                    raise TypeError(f"Record field {name!r} must be a FlaggedValue.")
                candidates.append((value, record))

            updates[name] = (
                merge_officers(candidates)
                if name == "officer"
                else choose_field(candidates)
            )

        updates["received_at"] = max(record.received_at for record in group)
        consolidated.append(cast(RecordT, replace(group[0], **updates)))

    return consolidated
