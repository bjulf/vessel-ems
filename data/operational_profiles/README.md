# Operational Profiles

This folder stores model-ready reconstructed operational load profiles derived
from vessel telemetry exports.

Canonical generation script:

- `data/preprocess.py`

Raw telemetry sources:

- 3-day profile: `data/v01.csv`
- 6-day profile:
  - `data/operational_raw/6day/all-data-types_2026-01-26_to_2026-01-28.csv`
  - `data/operational_raw/6day/all-data-types_2026-01-28_to_2026-01-31.csv`

Current generated profiles:

- `operational_load_profile_1min.csv`: 3-day continuous 1-minute profile
- `operational_load_profile_15min_avg.csv`: 3-day 15-minute average profile
- `operational_load_profile_6day_1min.csv`: 6-day continuous 1-minute profile
- `operational_load_profile_6day_15min_avg.csv`: 6-day 15-minute average profile

Both horizons use the same reconstruction and resampling method:

1. Sort and deduplicate raw timestamps.
2. Forward-fill sparse generator load-percentage telemetry.
3. Reconstruct load from generator load percentage and measured battery power.
4. Clip reconstructed load at zero.
5. Resample to a continuous 1-minute grid.
6. Fill missing 1-minute timestamps by time interpolation, then edge fill.
7. Save rounded 1-minute profiles.
8. Average the rounded 1-minute profiles to 15-minute model inputs.

The 15-minute files are the thesis-facing rolling-horizon model inputs used by
the corresponding configuration files in `config/`.
