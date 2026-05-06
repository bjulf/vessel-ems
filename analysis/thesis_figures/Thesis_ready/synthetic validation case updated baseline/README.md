# Synthetic Validation Case Updated Baseline

This folder groups the thesis-facing files for the updated synthetic baseline validation case.

PDF additions should be used for final thesis assembly. Existing PNG files in this folder
are retained as historical packaging artifacts from earlier figure curation.

## Included artifacts

- `baseline_full_horizon_milp_verification_overview.pdf`
  Source: `runs/2026-04-26_171631_baseline_model/plots/verification_overview.pdf`
  Purpose: thesis-ready PDF export of the three-panel full-horizon MILP verification overview
  for the current benchmark baseline.
  Origin: generated from `runs/2026-04-26_171631_baseline_model`, using
  `main_baseline.jl`, `model.jl`, and `config/baseline_model.toml`. The recorded
  configuration has no enforced terminal SOC constraint, 1000 g/start startup cost,
  70 percent initial SOC, 20-80 percent SOC window, 0.95 charge/discharge efficiency,
  and `data/synthetic_profiles/validation_profile.csv` at 15-minute resolution.

- `dispatch_results.csv`
  Source: `runs/2026-04-19_160125_baseline_model/dispatch_results.csv`
  Purpose: saved verification run table for the updated baseline synthetic case.

- `2026-04-19_160125_baseline_model_verification_overview.png`
  Source: `runs/2026-04-19_160125_baseline_model/plots/verification_overview.png`
  Purpose: working verification overview plot tied directly to the saved updated-baseline run.

- `synthetic_verification_overview_updated_baseline.png`
  Source: `runs/2026-04-19_160125_baseline_model/plots/verification_overview.png`
  Purpose: packaged thesis-facing verification overview for the updated baseline synthetic case.

- `validation_profile_bars.png`
  Source: `analysis/thesis_figures/methods/validation_profile_bars.png`
  Purpose: synthetic validation-profile design figure for the methods chapter.

- `baseline_model_timing_summary.txt`
  Source: `analysis/output/timing/baseline_model_timing_summary.txt`
  Purpose: timing summary with residual-check notes for the updated baseline synthetic case.

These are copied packaging artifacts. The authoritative source files remain in their original locations.
