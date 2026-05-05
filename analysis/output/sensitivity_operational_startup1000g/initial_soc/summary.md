# Initial-SOC Sensitivity Summary

Config: `config/operational_model_soc60_no_terminal_startup1000g_sensitivity.toml`
Cases run: 4
Baseline case at 70% initial SOC: 652.890 kg fuel, 4 starts, terminal SOC 20.00%.

| Initial SOC [%] | Config | Run Dir | Objective | Fuel [kg] | Starts | Stops | Min SOC [%] | Terminal SOC [%] | Throughput [kWh] | Solve [s] | Wall [s] | Warnings |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 50 | `analysis/output/sensitivity_operational_startup1000g/initial_soc/generated_configs/initial_soc_50pct.toml` | `runs/2026-05-04_140559_operational_model_soc60_no_terminal_cstart_1000g_sensitivity_initialsoc_50pct` | 693896.8 | 689.9 | 4 | 4 | 20 | 20 | 2061.4 | 3.046 | 31.85 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 60 | `analysis/output/sensitivity_operational_startup1000g/initial_soc/generated_configs/initial_soc_60pct.toml` | `runs/2026-05-04_140631_operational_model_soc60_no_terminal_cstart_1000g_sensitivity_initialsoc_60pct` | 675393.6 | 671.4 | 4 | 4 | 20 | 20 | 1962.4 | 2.841 | 31.21 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 70 | `analysis/output/sensitivity_operational_startup1000g/initial_soc/generated_configs/initial_soc_70pct.toml` | `runs/2026-05-04_140703_operational_model_soc60_no_terminal_cstart_1000g_sensitivity_initialsoc_70pct` | 656890.4 | 652.9 | 4 | 4 | 20 | 20 | 1863.5 | 5.167 | 31.6 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 80 | `analysis/output/sensitivity_operational_startup1000g/initial_soc/generated_configs/initial_soc_80pct.toml` | `runs/2026-05-04_140732_operational_model_soc60_no_terminal_cstart_1000g_sensitivity_initialsoc_80pct` | 638387.3 | 634.4 | 4 | 4 | 20.7 | 20 | 1764.5 | 3.771 | 28.64 | ends 30.0 pp below the old terminal reserve |
