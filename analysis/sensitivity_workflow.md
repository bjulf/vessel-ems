# Sensitivity Workflow

This note defines the standardized output structure and KPI set for the thesis-facing sensitivity runs.

## Storage

- Raw case outputs belong in `runs/`.
- Sweep-level reproducibility artifacts belong in `analysis/output/sensitivity/<sweep_name>/`.
- Thesis-candidate figures should be copied into `analysis/thesis_figures/` only after review.

Each sweep folder should contain:

- `generated_configs/`
- `run_manifest.csv`
- `summary.csv`
- `summary.txt`
- `overview.png`
- optional companion figures such as `fuel_vs_starts.png`

## Main KPIs

- `total_fuel_kg`
- `total_starts`
- `time_two_gensets_online_h`
- `min_soc_pct`
- `terminal_soc_pct`
- `battery_throughput_kwh`

Secondary KPIs:

- `total_online_genset_hours`
- `total_stops`
- `solve_time_s`

## Sweep Scripts

- `analysis/startup_cost_sensitivity.py`
- `analysis/terminal_reserve_sensitivity.py`
- `analysis/soc_min_sensitivity.py`
- `analysis/initial_soc_sensitivity.py`

These scripts all inherit from `config/baseline_model.toml`, generate case configs under the sweep-specific output folder, run `main.jl`, and summarize the resulting run directories.
