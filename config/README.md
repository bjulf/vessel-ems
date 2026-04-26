# Config Reference

The current main benchmark baseline is `config/baseline_model.toml`.

It uses:

- synthetic 24 h validation profile at `15 min` resolution
- `70%` initial battery SOC (`658 kWh`)
- no enforced terminal SOC constraint
- battery SOC window `20-80%`
- generator startup cost `1000 g/start`
- generator breakpoint powers `[192, 288, 310, 385] kW`
- generator SFOC values `[193, 191, 191, 198] g/kWh`

`config/baseline_model_terminal_soc50_startup700g.toml` is a preserved older thesis/report baseline, not the current main benchmark baseline.
It used:

- synthetic 24 h validation profile at `15 min` resolution
- `70%` initial battery SOC (`658 kWh`)
- `50%` terminal minimum battery SOC (`470 kWh`)
- battery SOC window `20-80%`
- generator startup cost `700 g/start`
- generator breakpoint powers `[192, 288, 310, 385] kW`
- generator SFOC values `[193, 191, 191, 198] g/kWh`

Use `config/baseline_model.toml` as the source of truth for current main benchmark sensitivity runs. Helper-generated configs should inherit unchanged settings from the selected baseline intentionally.

For the older `700 g/start` no-terminal sensitivity package, use `analysis/run_sensitivity_no_terminal_soc.py`.
That package writes to `analysis/output/sensitivity_no_terminal_soc/` and intentionally excludes the terminal-reserve sweep.
For the current baseline package, use `analysis/run_sensitivity_baseline.py`.

Named variants currently kept for sensitivity work:

- `baseline_model_no_terminal_soc.toml`: preserved older no-terminal synthetic case with `700 g/start`; use `baseline_model.toml` for the current main benchmark
- `baseline_model_terminal_soc50_startup700g.toml`: preserved older terminal-SOC synthetic case with `700 g/start`
- `baseline_model_soc50.toml`: lower synthetic initial SOC reference with the same `20-80%` battery window and `350 g/start`
- `baseline_model_soc70_terminal50.toml`: `70%` initial SOC, `50%` terminal minimum SOC, `350 g/start`
- `baseline_model_soc20_cstart_700g.toml`: reduced minimum SOC with `700 g/start`
- `baseline_model_soc70_terminal50_cstart450.toml`, `baseline_model_soc70_terminal50_cstart600.toml`, `baseline_model_soc70_terminal50_cstart700.toml`: startup-cost sensitivity cases
- `baseline_model_soc70_terminal50_socmin30_cstart700.toml` and `baseline_model_soc70_terminal50_socmin30_socmax80_cstart700.toml`: tighter lower-SOC-bound cases
- `operational_model_soc60_terminal50_socmin20_socmax80_cstart700.toml` and `operational_model_soc70_terminal50_socmin20_socmax80_cstart700.toml`: operational-profile variants

For current startup-cost sweeps, use `analysis/startup_cost_sensitivity.py` with `config/baseline_model.toml` unless a different sensitivity baseline is intentional. Older `700 g/start` configs are preserved comparison cases.
