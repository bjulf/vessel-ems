# Minimum-SOC Sensitivity Summary

Config: `config/operational_model_soc60_no_terminal_startup1000g_sensitivity.toml`
Cases run: 3
Baseline case at 20% minimum SOC: 671.394 kg fuel, 4 starts, terminal SOC 20.00%.

| Minimum SOC [%] | Config | Run Dir | Objective | Fuel [kg] | Starts | Stops | Min SOC [%] | Terminal SOC [%] | Throughput [kWh] | Solve [s] | Wall [s] | Warnings |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20 | `analysis/output/sensitivity_operational_startup1000g/soc_min/generated_configs/soc_min_20pct.toml` | `runs/2026-05-04_140304_operational_model_soc60_no_terminal_cstart_1000g_sensitivity_socmin_20pct` | 675393.6 | 671.4 | 4 | 4 | 20 | 20 | 1962.4 | 3.146 | 28.44 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 30 | `analysis/output/sensitivity_operational_startup1000g/soc_min/generated_configs/soc_min_30pct.toml` | `runs/2026-05-04_140332_operational_model_soc60_no_terminal_cstart_1000g_sensitivity_socmin_30pct` | 693896.8 | 689.9 | 4 | 4 | 30 | 30 | 2061.4 | 2.955 | 28.23 | ends 20.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 40 | `analysis/output/sensitivity_operational_startup1000g/soc_min/generated_configs/soc_min_40pct.toml` | `runs/2026-05-04_140526_operational_model_soc60_no_terminal_cstart_1000g_sensitivity_socmin_40pct` | 714851.3 | 708.9 | 6 | 6 | 40 | 40 | 2117.3 | 90.53 | 113.8 | ends 10.0 pp below the old terminal reserve; hits the configured minimum SOC; longer solve time |
