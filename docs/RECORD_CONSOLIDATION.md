# Activity-record consolidation and field status

This document records approved rules for classifying extracted field values, consolidating activity records, and removing completely empty unbatched records before workbook updates. These rules concern extracted records; they do not decide how duplicate rows already in the workbook are handled.

## Field status flags

Each extracted value has a value and a status flag:

| Flag | Meaning |
| --- | --- |
| `0` | The value was parseable and in the right format, producing a valid result that is not `None`. |
| `1` | The value was parseable but empty, producing `None`. |
| `2` | The value was not parseable. |
| `3` | Multiple sources of truth conflicted for that value. |

These flags describe status. For a non-empty field in a consolidated group, the selected value receives flag `3`, even if the populated values agree. If every candidate is empty, the latest candidate's flag is retained unless the candidate flags differ, in which case the result receives flag `3`.

**Implementation status:** `src/deapp/models/excel/field.py` accepts all four flags. Consistent status assignment during conversion still needs to be verified across record types.

## Parser field preservation and collisions

The generic parser maps recognized table headers to `ProductionActivity` fields. Headers it does not recognize are retained in `extra_fields`. A missing value in a generic field therefore does not prove that the corresponding activity measure is absent: a stage-specific header may hold that value in `extra_fields`. Resolve the actual source field for the target measure before assigning an empty-value flag.

For example, a parsed activity had `quantity=None` while `extra_fields` contained `NO. OF CARTONS: "2 CARTONS 34 BUNDLES"`. The carton and bundle meaning of such a mixed-unit value, and which part should populate a workbook field, must follow an explicit extraction rule. Do not silently discard a count or treat the whole value as empty.

There are two possible silent-overwrite points in the current parser:

- `record_to_production_activity()` builds a dictionary keyed by model-field name. If multiple headers map to the same field and appear in one row, the later mapping entry overwrites the earlier value. This can replace a nonempty value with an empty one, or hide differing values. The overwritten header is not retained in `extra_fields` because it was recognized.
- `matrix_to_records()` builds a dictionary keyed by header. If the source table repeats the exact same header, the later column overwrites the earlier one before activity mapping.

Header aliases and repeated headers must be detected and their values preserved until a resolution is made. Matching nonempty values may be treated as one value. Differing nonempty values are conflicting sources and must not be silently resolved; flag `3` represents that conflict. The rule for choosing between an empty alias and a nonempty alias has not yet been specified.

## Removing completely empty unbatched records

After record consolidation, remove a record only when all of these conditions hold:

1. `batch_number.value` is `None` and `batch_number.flag` is `1`.
2. At least one applicable time field exists, and every applicable time field is `None` with flag `1`. Recognized names are `start_time`, `end_time`, and the model alias `stop_time`.
3. At least one applicable measure field exists, and every applicable measure field is `None` with flag `1`. Check only fields present on the record from this set: `quantity_kg`, `output`, `quantity_tabs`, `drums`, `coarse_kg`, `powder_kg`, and `number_of_cartons`.

The time group and measure group must both be empty; a missing field on a record type is ignored. A value with another flag, or any non-`None` value, means the record does not meet this removal rule. The filter removes records only; it does not change the values or flags on records it keeps.

This filter concerns extracted records only. It does not establish workbook duplicate-row or repeated-processing behavior.

## Matching records

Records can be consolidated only within the same dataclass class and when all three activity-key fields are present and match in both value and flag:

- `date`
- `shift`
- `batch_number`

Records with an incomplete activity key remain separate. A complete-key group is consolidated only when it contains at least two distinct `report_type` values. Records with only one `report_type` remain separate. When a group is consolidated, the resulting `report_type` is set to `None` because it represents more than one source.

## Choosing field values

For each `FlaggedValue` field in a cross-report group:

1. If at least one candidate is populated, choose the populated value from the candidate with the latest `received_at` and set the resulting flag to `3`. This applies even when the populated values agree.
2. If every candidate value is `None`, keep the field from the latest record. If candidate flags differ, set the resulting flag to `3`; otherwise preserve the chosen field's flag.
3. If multiple populated candidates tie at the latest `received_at`, keep the first candidate in input order and set the resulting flag to `3`.

`officer` and `remarks` follow the same field-selection rules as other fields; their text is not joined across records.

The consolidated record's `received_at` is the latest `received_at` among all records in its group.

## Officer names

Officer names are not combined. A consolidated record keeps the populated officer value selected by the latest-`received_at` rule and receives flag `3`.

## Current implementation and verification status

`consolidate_records()` is in `src/deapp/services/excel/reconciliation.py`. Converter getters call it as part of record processing. The working tree also includes a post-consolidation empty-record filter.

The dispensing converter currently calls `remove_duplicates()` before consolidation. `FlaggedValue` equality ignores flags, so that preliminary filter can remove otherwise equal records whose flags differ, including key-field flags. The conversion path needs verification to ensure the approved key distinctions survive that filter.

`reconcile_records()` and `remove_duplicate_records()` use a separate reconciliation path with different matching and flag behavior. They should not be described as equivalent to `consolidate_records()`.

Before treating the rules as verified, add and run focused tests for key values and flags, status assignment for all four flags, `None` priority, all-`None` fields, officer-name joining and de-duplication, latest `received_at`, ambiguous timestamp ties, parser header aliases and repeated headers, and the empty-record filter (including that retained flags remain unchanged).

Workbook duplicate-row handling and retry behavior remain separate unresolved decisions.
