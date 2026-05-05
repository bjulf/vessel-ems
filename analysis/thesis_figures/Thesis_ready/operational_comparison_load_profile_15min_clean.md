# Operational Comparison Load Profile Figure

Packaged figure:

- `analysis/thesis_figures/Thesis_ready/operational_comparison_load_profile_15min_clean.pdf`

Curated source figure:

- `analysis/thesis_figures/methods/operational_comparison_load_profile_15min_clean.pdf`

Underlying model input:

- `data/operational_profiles/operational_load_profile_15min_avg.csv`

Case definition:

- 3-day operational comparison profile
- 15-minute average-load controller input
- `K = 265` model steps
- Time window: `2026-03-01 00:00` to `2026-03-03 18:00`

Generation note:

- The figure was regenerated as a thesis-ready methods figure in `analysis/thesis_figures/methods/`.
- It plots the final resampled 15-minute operational load profile used by the full-horizon, rule-based, and rolling-horizon controller comparison cases.
- The dashed horizontal reference line marks the one-generator rated power level, `385 kW`.
