# Minimum-SOC Sensitivity Summary

Config: `config/baseline_model_no_terminal_soc.toml`
Cases run: 3
Baseline case at 20% minimum SOC: 806.207 kg fuel, 4 starts, terminal SOC 20.00%.

| Minimum SOC [%] | Config | Run Dir | Objective | Fuel [kg] | Starts | Stops | Min SOC [%] | Terminal SOC [%] | Throughput [kWh] | Solve [s] | Wall [s] | Warnings |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20 | `analysis/output/sensitivity_no_terminal_soc/soc_min/generated_configs/soc_min_20pct.toml` | `runs/2026-04-23_125917_baseline_model_no_terminal_soc_socmin_20pct` | 809007 | 806.2 | 4 | 3 | 20 | 20 | 1061.3 | 3.108 | 26 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 30 | `analysis/output/sensitivity_no_terminal_soc/soc_min/generated_configs/soc_min_30pct.toml` | `runs/2026-04-23_125948_baseline_model_no_terminal_soc_socmin_30pct` | 827481.5 | 824 | 5 | 4 | 30 | 30 | 1024.1 | 7.839 | 29.87 | ends 20.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 40 | `analysis/output/sensitivity_no_terminal_soc/soc_min/generated_configs/soc_min_40pct.toml` | `runs/2026-04-23_130023_baseline_model_no_terminal_soc_socmin_40pct` | 845646 | 842.1 | 5 | 4 | 40 | 40 | 1027.6 | 8.865 | 37.4 | ends 10.0 pp below the old terminal reserve; hits the configured minimum SOC |
