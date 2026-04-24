# Battery-Efficiency Sensitivity Summary

Config: `config/baseline_model_no_terminal_soc_startup1000g.toml`
Cases run: 3
Baseline case at eta = 0.95: 807.828 kg fuel, 2 starts, terminal SOC 20.00%.

Recommended benchmark baseline from this package: no terminal SOC constraint, startup cost `1000 g/start`, minimum SOC `20%`, initial SOC `70%`, and battery efficiency `0.95`.

| Efficiency [-] | Config | Run Dir | Objective | Fuel [kg] | Starts | Stops | Min SOC [%] | Terminal SOC [%] | Throughput [kWh] | Solve [s] | Wall [s] | Warnings |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.92 | `analysis/output/sensitivity_new_baseline_startupcost1000g/battery_efficiency/generated_configs/battery_efficiency_92pct.toml` | `runs/2026-04-23_134943_baseline_model_no_terminal_soc_cstart_1000g_eta_92pct` | 817048.3 | 813 | 4 | 3 | 20 | 20 | 1064.1 | 3.076 | 20.31 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 0.95 | `analysis/output/sensitivity_new_baseline_startupcost1000g/battery_efficiency/generated_configs/battery_efficiency_95pct.toml` | `runs/2026-04-23_135000_baseline_model_no_terminal_soc_cstart_1000g_eta_95pct` | 809827.9 | 807.8 | 2 | 1 | 20 | 20 | 1203.9 | 1.2 | 17.85 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 0.98 | `analysis/output/sensitivity_new_baseline_startupcost1000g/battery_efficiency/generated_configs/battery_efficiency_98pct.toml` | `runs/2026-04-23_135020_baseline_model_no_terminal_soc_cstart_1000g_eta_98pct` | 802158.3 | 801.2 | 1 | 0 | 20 | 20 | 1475.6 | 1.475 | 20.17 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
