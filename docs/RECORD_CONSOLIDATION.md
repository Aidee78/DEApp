# Activity-record consolidation

This document records the approved rules for consolidating extracted production-activity records before workbook updates. These rules concern extracted records; they do not decide how duplicate rows already in the workbook are handled.

## Matching records

Two records refer to the same activity only when they have the same record type and the same values **and flags** for all three key fields:

- `date`
- `shift`
- `batch_number`

A `None` value is compared like any other key value. Thus two records with `None` for a key field match on that field when their flags also match. A difference in any key value or key flag keeps the records in separate groups.

## Choosing field values

For each field, resolve its `FlaggedValue` independently:

1. If at least one candidate value is not `None`, ignore candidates whose value is `None`.
2. From the remaining candidates, choose the lowest flag (`0` before `3`).
3. If candidates have the same flag, choose the value from the record with the latest `received_at`.
4. If all candidate values are `None`, use the value and flag from the latest record.

The consolidated record's `received_at` is the latest `received_at` among all records in its group.

If different non-`None` values remain tied on both the winning flag and latest `received_at`, the current `consolidate_records()` implementation raises `ValueError`. The business rule does not define another winner for that exact tie, so it must not be resolved by silently choosing one.

## Officer names

For the `officer` field, combine the names from all non-`None` values. Split comma-separated values, trim surrounding whitespace, remove repeated names, preserve first-seen order, and join the result with `, `. The officer field's flag follows the same lowest-flag and latest-`received_at` rules above. If every officer value is `None`, use the flag from the latest record.

## Current implementation and verification status

The working tree contains `consolidate_records()` in `src/deapp/services/excel/reconciliation.py`, and `Converter.get_dispensing_records()` calls it. The other converter record getters are not implemented yet, so this does not establish that every record type is integrated.

The dispensing converter currently calls `remove_duplicates()` before consolidation. `FlaggedValue` equality ignores flags, so that preliminary filter can remove otherwise equal records whose flags differ—including key-field flags. The conversion path needs verification to ensure the approved key distinctions survive that filter.

`reconcile_records()` and `remove_duplicate_records()` use a separate reconciliation path with different matching and flag behavior. They should not be described as equivalent to `consolidate_records()`.

Before treating the approved rules as verified, add and run focused tests for key values and flags, `None` priority, all-`None` fields, flag and timestamp precedence, officer-name joining and de-duplication, latest `received_at`, and ambiguous timestamp ties.

Workbook duplicate-row handling and retry behavior remain separate unresolved decisions.
