# Startup-Cost Sensitivity Summary

Config: `config/baseline_model_no_terminal_soc_startup1000g.toml`
Cases run: 8
Baseline case at 1000 g/start: 807.828 kg fuel, 2 starts, terminal SOC 20.00%.

Recommended benchmark baseline from this package: no terminal SOC constraint, startup cost `1000 g/start`, minimum SOC `20%`, initial SOC `70%`, and battery efficiency `0.95`.

| Startup Cost [g/start] | Config | Run Dir | Objective | Fuel [kg] | Starts | Stops | Min SOC [%] | Terminal SOC [%] | Throughput [kWh] | Solve [s] | Wall [s] | Warnings |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 350 | `analysis/output/sensitivity_new_baseline_startupcost1000g/startup_cost/generated_configs/startup_cost_350g.toml` | `runs/2026-04-23_134432_baseline_model_no_terminal_soc_cstart_1000g_cstart_350g` | 807309.1 | 804.5 | 8 | 7 | 20 | 20 | 884.5 | 2.115 | 45.65 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 500 | `analysis/output/sensitivity_new_baseline_startupcost1000g/startup_cost/generated_configs/startup_cost_500g.toml` | `runs/2026-04-23_134449_baseline_model_no_terminal_soc_cstart_1000g_cstart_500g` | 808207 | 806.2 | 4 | 3 | 20 | 20 | 1061.3 | 1.426 | 16.15 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 550 | `analysis/output/sensitivity_new_baseline_startupcost1000g/startup_cost/generated_configs/startup_cost_550g.toml` | `runs/2026-04-23_134504_baseline_model_no_terminal_soc_cstart_1000g_cstart_550g` | 808407 | 806.2 | 4 | 3 | 20 | 20 | 1061.3 | 1.388 | 15.68 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 600 | `analysis/output/sensitivity_new_baseline_startupcost1000g/startup_cost/generated_configs/startup_cost_600g.toml` | `runs/2026-04-23_134520_baseline_model_no_terminal_soc_cstart_1000g_cstart_600g` | 808607 | 806.2 | 4 | 3 | 20 | 20 | 1061.3 | 1.56 | 16.26 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 650 | `analysis/output/sensitivity_new_baseline_startupcost1000g/startup_cost/generated_configs/startup_cost_650g.toml` | `runs/2026-04-23_134537_baseline_model_no_terminal_soc_cstart_1000g_cstart_650g` | 808807 | 806.2 | 4 | 3 | 20 | 20 | 1061.3 | 1.519 | 16.71 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 700 | `analysis/output/sensitivity_new_baseline_startupcost1000g/startup_cost/generated_configs/startup_cost_700g.toml` | `runs/2026-04-23_134553_baseline_model_no_terminal_soc_cstart_1000g_cstart_700g` | 809007 | 806.2 | 4 | 3 | 20 | 20 | 1061.3 | 1.65 | 16.43 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 1000 | `analysis/output/sensitivity_new_baseline_startupcost1000g/startup_cost/generated_configs/startup_cost_1000g.toml` | `runs/2026-04-23_134609_baseline_model_no_terminal_soc_cstart_1000g_cstart_1000g` | 809827.9 | 807.8 | 2 | 1 | 20 | 20 | 1203.9 | 1.094 | 15.76 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 1500 | `analysis/output/sensitivity_new_baseline_startupcost1000g/startup_cost/generated_configs/startup_cost_1500g.toml` | `runs/2026-04-23_134625_baseline_model_no_terminal_soc_cstart_1000g_cstart_1500g` | 810827.9 | 807.8 | 2 | 1 | 20 | 20 | 1203.9 | 1.169 | 16.04 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
