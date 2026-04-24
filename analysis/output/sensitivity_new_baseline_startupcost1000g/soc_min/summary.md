# Minimum-SOC Sensitivity Summary

Config: `config/baseline_model_no_terminal_soc_startup1000g.toml`
Cases run: 3
Baseline case at 20% minimum SOC: 807.828 kg fuel, 2 starts, terminal SOC 20.00%.

Recommended benchmark baseline from this package: no terminal SOC constraint, startup cost `1000 g/start`, minimum SOC `20%`, initial SOC `70%`, and battery efficiency `0.95`.

| Minimum SOC [%] | Config | Run Dir | Objective | Fuel [kg] | Starts | Stops | Min SOC [%] | Terminal SOC [%] | Throughput [kWh] | Solve [s] | Wall [s] | Warnings |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20 | `analysis/output/sensitivity_new_baseline_startupcost1000g/soc_min/generated_configs/soc_min_20pct.toml` | `runs/2026-04-23_134645_baseline_model_no_terminal_soc_cstart_1000g_socmin_20pct` | 809827.9 | 807.8 | 2 | 1 | 20 | 20 | 1203.9 | 1.122 | 18.75 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 30 | `analysis/output/sensitivity_new_baseline_startupcost1000g/soc_min/generated_configs/soc_min_30pct.toml` | `runs/2026-04-23_134709_baseline_model_no_terminal_soc_cstart_1000g_socmin_30pct` | 828431.7 | 825.4 | 3 | 2 | 30 | 30 | 1150.9 | 5.926 | 24.98 | ends 20.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 40 | `analysis/output/sensitivity_new_baseline_startupcost1000g/soc_min/generated_configs/soc_min_40pct.toml` | `runs/2026-04-23_134735_baseline_model_no_terminal_soc_cstart_1000g_socmin_40pct` | 846819.5 | 843.8 | 3 | 2 | 40 | 40 | 1178.1 | 5.462 | 23.49 | ends 10.0 pp below the old terminal reserve; hits the configured minimum SOC |
