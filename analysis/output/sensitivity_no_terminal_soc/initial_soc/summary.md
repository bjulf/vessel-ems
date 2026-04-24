# Initial-SOC Sensitivity Summary

Config: `config/baseline_model_no_terminal_soc.toml`
Cases run: 4
Baseline case at 70% initial SOC: 806.207 kg fuel, 4 starts, terminal SOC 20.00%.

| Initial SOC [%] | Config | Run Dir | Objective | Fuel [kg] | Starts | Stops | Min SOC [%] | Terminal SOC [%] | Throughput [kWh] | Solve [s] | Wall [s] | Warnings |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 50 | `analysis/output/sensitivity_no_terminal_soc/initial_soc/generated_configs/initial_soc_50pct.toml` | `runs/2026-04-23_130103_baseline_model_no_terminal_soc_initialsoc_50pct` | 845646 | 842.1 | 5 | 4 | 20 | 20 | 1027.6 | 9.691 | 39.86 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 60 | `analysis/output/sensitivity_no_terminal_soc/initial_soc/generated_configs/initial_soc_60pct.toml` | `runs/2026-04-23_130159_baseline_model_no_terminal_soc_initialsoc_60pct` | 827519.7 | 824 | 5 | 4 | 20 | 20 | 1028.1 | 13.32 | 55.94 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC; longer solve time |
| 70 | `analysis/output/sensitivity_no_terminal_soc/initial_soc/generated_configs/initial_soc_70pct.toml` | `runs/2026-04-23_130246_baseline_model_no_terminal_soc_initialsoc_70pct` | 809007 | 806.2 | 4 | 3 | 20 | 20 | 1061.3 | 5.634 | 47.64 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 80 | `analysis/output/sensitivity_no_terminal_soc/initial_soc/generated_configs/initial_soc_80pct.toml` | `runs/2026-04-23_130332_baseline_model_no_terminal_soc_initialsoc_80pct` | 790840.3 | 788 | 4 | 3 | 20 | 20 | 1057.6 | 1.601 | 44.36 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
