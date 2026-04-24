# Battery-Efficiency Sensitivity Summary

Config: `config/baseline_model_no_terminal_soc.toml`
Cases run: 3
Baseline case at eta = 0.95: 806.207 kg fuel, 4 starts, terminal SOC 20.00%.

| Efficiency [-] | Config | Run Dir | Objective | Fuel [kg] | Starts | Stops | Min SOC [%] | Terminal SOC [%] | Throughput [kWh] | Solve [s] | Wall [s] | Warnings |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.92 | `analysis/output/sensitivity_no_terminal_soc/battery_efficiency/generated_configs/battery_efficiency_92pct.toml` | `runs/2026-04-23_130417_baseline_model_no_terminal_soc_eta_92pct` | 815926.3 | 811 | 7 | 6 | 20 | 20 | 936.9 | 11.52 | 41.81 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC; longer solve time |
| 0.95 | `analysis/output/sensitivity_no_terminal_soc/battery_efficiency/generated_configs/battery_efficiency_95pct.toml` | `runs/2026-04-23_130505_baseline_model_no_terminal_soc_eta_95pct` | 809007 | 806.2 | 4 | 3 | 20 | 20 | 1061.3 | 4.524 | 47.38 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 0.98 | `analysis/output/sensitivity_no_terminal_soc/battery_efficiency/generated_configs/battery_efficiency_98pct.toml` | `runs/2026-04-23_130600_baseline_model_no_terminal_soc_eta_98pct` | 801858.3 | 801.2 | 1 | 0 | 20 | 20 | 1475.6 | 11.18 | 66.02 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC; longer solve time |
