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
