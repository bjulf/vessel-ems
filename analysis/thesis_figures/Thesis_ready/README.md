# Thesis Ready Bundle

This folder is a packaging area for thesis-facing material copied from the working analysis outputs and curated figure shortlist.

## Structure

- `synthetic validation case/`
  Synthetic-case bundle containing the saved verification run table, verification plots, timing summary, and synthetic-case thesis figures.

- `synthetic validation case updated baseline/`
  Synthetic-case bundle containing the saved verification run table, verification overview, timing summary, and methods figure for the updated baseline configuration.

- `synthetic_full_horizon_milp_oem_sfoc_reference_points_by_module.pdf`
  Thesis-ready PDF showing the retained synthetic full-horizon MILP generator operating
  points against the straight-line OEM SFOC reference. Source:
  `runs/2026-04-26_171631_baseline_model/plots/verification_oem_sfoc_reference_points_by_module.pdf`.
  Origin run records `config/baseline_model.toml`, `main_baseline.jl`,
  `model.jl`, `data/synthetic_profiles/validation_profile.csv`, 15-minute
  timestep, 70% initial SOC, no enforced terminal SOC constraint, 20-80% SOC
  window, 0.95 battery efficiency, and 1000 g/start generator startup cost.

- `operational_load_validation.png`
  Curated methods figure for operational load validation.

- `operational_comparison_load_profile_15min_clean.pdf`
  Curated methods figure for the final 15-minute 3-day operational comparison load profile.
  See `operational_comparison_load_profile_15min_clean.md` for source and generation notes.

- `operational_full_horizon_milp_15min_avg_verification_overview.pdf`
  Three-panel full-horizon MILP verification overview for the 3-day operational
  15-minute averaged telemetry dataset. Generated from
  `analysis/output/verification/operational_no_terminal_startup1000g/milp`,
  whose `params.toml` records `config/operational_model_soc60_no_terminal_startup1000g.toml`
  and `data/operational_profiles/operational_load_profile_15min_avg.csv`.

- `sfoc_regime_thesis_scatter.png`
  Curated results figure for telemetry-based SFOC/regime assessment.

This is a packaging folder. The authoritative working copies remain in their original source locations.
