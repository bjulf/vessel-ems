# Config Reference

`config/baseline_model.toml` is the active thesis baseline for this repository.

It matches the latest report-side synthetic baseline that produced the current validation result:

- synthetic 24 h validation profile at `15 min` resolution
- `70%` initial battery SOC (`658 kWh`)
- `50%` terminal minimum battery SOC (`470 kWh`)
- battery SOC window `20-80%`
- generator startup cost `700 g/start`
- generator breakpoint powers `[192, 288, 310, 385] kW`
- generator SFOC values `[193, 191, 191, 198] g/kWh`

Use the baseline file as the source of truth for sensitivity runs. Helper-generated configs should inherit all unchanged settings from it, especially `[terminal_conditions]`.

Named variants currently kept for sensitivity work:

- `baseline_model_soc50.toml`: lower synthetic initial SOC reference with the same `20-80%` battery window and `350 g/start`
- `baseline_model_soc70_terminal50.toml`: `70%` initial SOC, `50%` terminal minimum SOC, `350 g/start`
- `baseline_model_soc20_cstart_700g.toml`: reduced minimum SOC with `700 g/start`
- `baseline_model_soc70_terminal50_cstart450.toml`, `baseline_model_soc70_terminal50_cstart600.toml`, `baseline_model_soc70_terminal50_cstart700.toml`: startup-cost sensitivity cases
- `baseline_model_soc70_terminal50_socmin30_cstart700.toml` and `baseline_model_soc70_terminal50_socmin30_socmax80_cstart700.toml`: tighter lower-SOC-bound cases
- `operational_model_soc60_terminal50_socmin20_socmax80_cstart700.toml` and `operational_model_soc70_terminal50_socmin20_socmax80_cstart700.toml`: operational-profile variants

For startup-cost sweeps, use `analysis/startup_cost_sensitivity.py` with `config/baseline_model.toml` unless a different sensitivity baseline is intentional.
