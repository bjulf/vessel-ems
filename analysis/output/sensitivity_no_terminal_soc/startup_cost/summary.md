# Startup-Cost Sensitivity Summary

Config: `config/baseline_model_no_terminal_soc.toml`
Cases run: 8
Baseline case at 700 g/start: 806.207 kg fuel, 4 starts, terminal SOC 20.00%.

| Startup Cost [g/start] | Config | Run Dir | Objective | Fuel [kg] | Starts | Stops | Min SOC [%] | Terminal SOC [%] | Throughput [kWh] | Solve [s] | Wall [s] | Warnings |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 350 | `analysis/output/sensitivity_no_terminal_soc/startup_cost/generated_configs/startup_cost_350g.toml` | `runs/2026-04-23_125521_baseline_model_no_terminal_soc_cstart_350g` | 807309.1 | 804.5 | 8 | 7 | 20 | 20 | 884.5 | 4.243 | 67.45 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 500 | `analysis/output/sensitivity_no_terminal_soc/startup_cost/generated_configs/startup_cost_500g.toml` | `runs/2026-04-23_125547_baseline_model_no_terminal_soc_cstart_500g` | 808207 | 806.2 | 4 | 3 | 20 | 20 | 1061.3 | 2.598 | 25.37 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 550 | `analysis/output/sensitivity_no_terminal_soc/startup_cost/generated_configs/startup_cost_550g.toml` | `runs/2026-04-23_125613_baseline_model_no_terminal_soc_cstart_550g` | 808407 | 806.2 | 4 | 3 | 20 | 20 | 1061.3 | 2.427 | 26.39 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 600 | `analysis/output/sensitivity_no_terminal_soc/startup_cost/generated_configs/startup_cost_600g.toml` | `runs/2026-04-23_125641_baseline_model_no_terminal_soc_cstart_600g` | 808607 | 806.2 | 4 | 3 | 20 | 20 | 1061.3 | 3.171 | 28.57 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 650 | `analysis/output/sensitivity_no_terminal_soc/startup_cost/generated_configs/startup_cost_650g.toml` | `runs/2026-04-23_125709_baseline_model_no_terminal_soc_cstart_650g` | 808807 | 806.2 | 4 | 3 | 20 | 20 | 1061.3 | 3.012 | 25.85 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 700 | `analysis/output/sensitivity_no_terminal_soc/startup_cost/generated_configs/startup_cost_700g.toml` | `runs/2026-04-23_125806_baseline_model_no_terminal_soc_cstart_700g` | 809007 | 806.2 | 4 | 3 | 20 | 20 | 1061.3 | 1.45 | 55.25 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 1000 | `analysis/output/sensitivity_no_terminal_soc/startup_cost/generated_configs/startup_cost_1000g.toml` | `runs/2026-04-23_125821_baseline_model_no_terminal_soc_cstart_1000g` | 809827.9 | 807.8 | 2 | 1 | 20 | 20 | 1203.9 | 1.925 | 18.81 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
| 1500 | `analysis/output/sensitivity_no_terminal_soc/startup_cost/generated_configs/startup_cost_1500g.toml` | `runs/2026-04-23_125847_baseline_model_no_terminal_soc_cstart_1500g` | 810827.9 | 807.8 | 2 | 1 | 20 | 20 | 1203.9 | 1.942 | 23.89 | ends 30.0 pp below the old terminal reserve; hits the configured minimum SOC |
