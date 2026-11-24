# Activity-record conversion rules

## Granulation quantities

Granulation reports may give coarse and fine-powder quantities as percentages
in the activity's `NO` value. Convert each percentage to kilograms using the
nearest preceding Sifting activity for the same batch in the same production
line and report:

```text
coarse_kg = preceding_sifting_kg * coarse_percent / 100
powder_kg = preceding_sifting_kg * fine_powder_percent / 100
```

The converter uses an explicitly labeled kilogram value when the granulation
activity supplies one directly. It does not use a Sifting quantity from another
batch. If a percentage is present but no valid preceding Sifting kilogram value
is available, the derived field is `None` with flag `2`. Values are not rounded
during conversion.

## Shift resolution from receipt time

Zoho's timezone-aware `received_at` timestamp is converted to `Africa/Lagos`
before checking the shift windows. Receipt times from 16:00 through 22:00,
inclusive, indicate Day shift; times from 04:00 through 10:00, inclusive,
indicate Night shift. If this inferred shift differs from a clear Day or Night
shift in the report, the inferred shift is used and the shift field receives
flag `3`.

Timestamps outside both windows do not change the report shift or its flag.
Missing or unclear report shifts are also left at their existing parsed value
and flag. When the resolved shift has flag `3`, every time field in the record
inherits flag `3` while retaining its parsed value.
