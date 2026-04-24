# Initial-SOC Sensitivity Summary

Config: `config/baseline_model_no_terminal_soc_startup1000g.toml`
Cases run: 4
Baseline case at 70% initial SOC: 807.828 kg fuel, 2 starts, terminal SOC 20.00%.

Recommended benchmark baseline from this package: no terminal SOC constraint, startup cost `1000 g/start`, minimum SOC `20%`, initial SOC `70%`, and battery efficiency `0.95`.

| Initial SOC [%] | Config | Run Dir | Objective | Fuel [kg] | Starts | Stops | Min SOC [%] | Terminal SOC [%] | Throughput [kWh] | Solve [s] | Wall [s] | Warnings |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 50 | `analysis/output/sensitivity_new_baseline_startupcost1000g/initial_soc/generated_configs/initial_soc_50pct.toml` | `runs/2026-04-23_134811_baseline_model_no_terminal_soc_cstart_1000g_initialsoc_50pct` | 846819.5 | 843.8 | 3 | 2 | 20 | 20 | 1178.1 | 7.798 | 36.5 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 60 | `analysis/output/sensitivity_new_baseline_startupcost1000g/initial_soc/generated_configs/initial_soc_60pct.toml` | `runs/2026-04-23_134844_baseline_model_no_terminal_soc_cstart_1000g_initialsoc_60pct` | 828431.7 | 825.4 | 3 | 2 | 20 | 20 | 1150.9 | 7.473 | 31.79 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 70 | `analysis/output/sensitivity_new_baseline_startupcost1000g/initial_soc/generated_configs/initial_soc_70pct.toml` | `runs/2026-04-23_134903_baseline_model_no_terminal_soc_cstart_1000g_initialsoc_70pct` | 809827.9 | 807.8 | 2 | 1 | 20 | 20 | 1203.9 | 1.197 | 17.84 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 80 | `analysis/output/sensitivity_new_baseline_startupcost1000g/initial_soc/generated_configs/initial_soc_80pct.toml` | `runs/2026-04-23_134921_baseline_model_no_terminal_soc_cstart_1000g_initialsoc_80pct` | 791708.8 | 789.7 | 2 | 1 | 20 | 20 | 1204.3 | 0.616 | 17.49 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
