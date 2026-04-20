# Sensitivity Sweep Parameters

This note records the parameter values used in the existing sensitivity sweeps that feed the thesis presentation figures in this folder.

These figures were derived from existing sweep summaries. They are not based on new model runs.

## Source and interpretation

- Baseline configuration: `config/baseline_model.toml`
- Sweep summaries:
  - `analysis/output/sensitivity/startup_cost/summary.csv`
  - `analysis/output/sensitivity/terminal_reserve/summary.csv`
  - `analysis/output/sensitivity/soc_min/summary.csv`
  - `analysis/output/sensitivity/initial_soc/summary.csv`
- Supporting sweep summaries:
  - `analysis/output/sensitivity/startup_cost/summary.txt`
  - `analysis/output/sensitivity/terminal_reserve/summary.txt`
  - `analysis/output/sensitivity/soc_min/summary.txt`
  - `analysis/output/sensitivity/initial_soc/summary.txt`

Each sweep varies one parameter relative to the frozen thesis baseline and leaves the other baseline settings unchanged.

## Live baseline values used for the thesis figures

- Startup cost: `700 g/start`
- Terminal reserve: `50%`
- Minimum SOC constraint: `20%`
- Initial SOC: `70%`

These baseline values come directly from `config/baseline_model.toml`.

## Sweep values used

### Startup-cost sweep

- Varied parameter: generator startup cost
- Cases used: `350, 500, 550, 600, 650, 700, 1000, 1500 g/start`
- Baseline case within sweep: `700 g/start`
- Source documentation:
  - `analysis/output/sensitivity/startup_cost/summary.txt`
  - `analysis/startup_cost_sensitivity.py`

### Terminal-SOC-requirement sweep

- Varied parameter: terminal SOC requirement
- Cases used: `30, 40, 50, 60%`
- Baseline case within sweep: `50%`
- Source documentation:
  - `analysis/output/sensitivity/terminal_reserve/summary.txt`
  - `analysis/terminal_reserve_sensitivity.py`

### Minimum-SOC sweep

- Varied parameter: minimum battery SOC constraint
- Cases used: `20, 30, 40%`
- Baseline case within sweep: `20%`
- Source documentation:
  - `analysis/output/sensitivity/soc_min/summary.txt`
  - `analysis/soc_min_sensitivity.py`

### Initial-SOC sweep

- Varied parameter: initial battery SOC
- Cases used: `50, 60, 70, 80%`
- Baseline case within sweep: `70%`
- Source documentation:
  - `analysis/output/sensitivity/initial_soc/summary.txt`
  - `analysis/initial_soc_sensitivity.py`

### Battery-efficiency sweep

- Varied parameter: symmetric battery charge and discharge efficiency
- Cases used: `0.92, 0.95, 0.98`
- Baseline case within sweep: `0.95`
- Current status: completed as an additional secondary check after the first thesis sensitivity package
- Source documentation:
  - `analysis/output/sensitivity/battery_efficiency/summary.txt`
  - `analysis/battery_efficiency_sensitivity.py`

## Figure mapping

- `startup_cost_main.*`
  - Uses the startup-cost sweep
- `other_main_sensitivities.*`
  - Uses the terminal-SOC-requirement sweep and the battery-efficiency sweep
- `startup_cost_appendix.*`
  - Uses the startup-cost sweep
- `terminal_soc_requirement_appendix.*`
  - Uses the terminal-SOC-requirement sweep
- `battery_efficiency_appendix.*`
  - Uses the battery-efficiency sweep
- `soc_min_appendix.*`
  - Uses the minimum-SOC sweep
- `initial_soc_appendix.*`
  - Uses the initial-SOC sweep
- `analysis/output/sensitivity/battery_efficiency/overview.png`
  - Working overview figure for the battery-efficiency sweep
