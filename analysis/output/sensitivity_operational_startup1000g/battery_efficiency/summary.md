# Battery-Efficiency Sensitivity Summary

Config: `config/operational_model_soc60_no_terminal_startup1000g_sensitivity.toml`
Cases run: 3
Baseline case at eta = 0.95: 671.394 kg fuel, 4 starts, terminal SOC 20.00%.

| Efficiency [-] | Config | Run Dir | Objective | Fuel [kg] | Starts | Stops | Min SOC [%] | Terminal SOC [%] | Throughput [kWh] | Solve [s] | Wall [s] | Warnings |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.92 | `analysis/output/sensitivity_operational_startup1000g/battery_efficiency/generated_configs/battery_efficiency_92pct.toml` | `runs/2026-05-04_140813_operational_model_soc60_no_terminal_cstart_1000g_sensitivity_eta_92pct` | 688272 | 684.3 | 4 | 4 | 20 | 20 | 2008.6 | 5.366 | 40.1 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 0.95 | `analysis/output/sensitivity_operational_startup1000g/battery_efficiency/generated_configs/battery_efficiency_95pct.toml` | `runs/2026-05-04_140845_operational_model_soc60_no_terminal_cstart_1000g_sensitivity_eta_95pct` | 675393.6 | 671.4 | 4 | 4 | 20 | 20 | 1962.4 | 3.596 | 31.01 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 0.98 | `analysis/output/sensitivity_operational_startup1000g/battery_efficiency/generated_configs/battery_efficiency_98pct.toml` | `runs/2026-05-04_140923_operational_model_soc60_no_terminal_cstart_1000g_sensitivity_eta_98pct` | 662985.2 | 659 | 4 | 4 | 20 | 20 | 2400.7 | 7.261 | 37.68 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
