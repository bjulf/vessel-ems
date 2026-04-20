# Sensitivity Figure Manifest

These figures are presentation figures derived from the existing sweep summary CSV files. They are not new model runs.

Related notes:

- `sweep_parameters.md`
  - Consolidated record of the baseline values and sweep case values used for these figures
- `full_sensitivity_sweep_table.md`
  - One-table summary of all completed sensitivity sweeps and tested values

## Generated figures

- `startup_cost_main.pdf` and `startup_cost_main.png`
  - Source: `analysis/output/sensitivity/startup_cost/summary.csv`
  - Intended use: main text
  - Panels: A startup-cost trade-off in fuel versus starts, B minimum-SOC response to startup cost

- `other_main_sensitivities.pdf` and `other_main_sensitivities.png`
  - Sources: `analysis/output/sensitivity/terminal_reserve/summary.csv`, `analysis/output/sensitivity/battery_efficiency/summary.csv`
  - Intended use: main text
  - Panels: A fuel versus terminal SOC requirement, B minimum SOC versus terminal SOC requirement, C fuel versus battery efficiency, D starts versus battery efficiency

- `startup_cost_appendix.pdf` and `startup_cost_appendix.png`
  - Source: `analysis/output/sensitivity/startup_cost/summary.csv`
  - Intended use: appendix only
  - Panels: total fuel, total starts, minimum SOC reached, battery throughput versus startup cost

- `terminal_soc_requirement_appendix.pdf` and `terminal_soc_requirement_appendix.png`
  - Source: `analysis/output/sensitivity/terminal_reserve/summary.csv`
  - Intended use: appendix only
  - Panels: total fuel, total starts, minimum SOC reached, battery throughput versus terminal SOC requirement

- `battery_efficiency_appendix.pdf` and `battery_efficiency_appendix.png`
  - Source: `analysis/output/sensitivity/battery_efficiency/summary.csv`
  - Intended use: appendix only
  - Panels: total fuel, total starts, minimum SOC reached, battery throughput versus battery efficiency

- `soc_min_appendix.pdf` and `soc_min_appendix.png`
  - Source: `analysis/output/sensitivity/soc_min/summary.csv`
  - Intended use: appendix only
  - Panels: total fuel and total starts versus minimum SOC

- `initial_soc_appendix.pdf` and `initial_soc_appendix.png`
  - Source: `analysis/output/sensitivity/initial_soc/summary.csv`
  - Intended use: appendix only
  - Panels: total fuel and total starts versus initial SOC
