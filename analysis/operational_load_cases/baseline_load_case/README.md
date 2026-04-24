# Baseline Load Case

This case keeps the raw exports, prepared datasets, and working figures together.

## Source Files

- `raw/all-data-types_2026-01-26_to_2026-01-28.csv`
- `raw/all-data-types_2026-01-28_to_2026-01-31.csv`

## Prepared Outputs

- `prepared/combined_1min.csv`: timestamp-sorted combination of the raw exports
- `prepared/cleaned_1min.csv`: cleaned minute-level dataset with derived load columns
- `prepared/load_profile_15min_avg.csv`: 15-minute average reconstructed load profile

## Figure

- `figures/operational_load_validation_6day.png`: 2-panel operational load reconstruction figure

## Notes

- Combined span: 2026-01-26 01:00:00 to 2026-01-31 14:19:00
- Total duration: 133.32 h
- 15-minute profile steps: 534
- Reconstructed load range: 0.0 to 334.1 kW
- Battery power range: -292.4 to 189.5 kW
- Gen 2 proxy max in this case: 0.0 kW

The current export behaves like a `gen1`-dominated operational case: `gen2` remains at zero throughout the prepared dataset.
The figure therefore preserves the same structure as the existing validation plot while making that operating pattern visible.