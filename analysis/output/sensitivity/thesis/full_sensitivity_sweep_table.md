# Full Sensitivity Sweep Table

This note consolidates every parameter sweep that was tested during the current synthetic-case sensitivity-analysis workflow in the model repository.

These sweeps were run on the frozen synthetic validation baseline and summarized under `analysis/output/sensitivity/`.

## Baseline used for the sweeps

Source: `config/baseline_model.toml`

| Parameter | Baseline value | Unit |
|---|---:|---|
| Start-up cost | 700 | g/start |
| Terminal SOC requirement | 50 | % |
| Minimum SOC constraint | 20 | % |
| Initial SOC | 70 | % |
| Battery charge efficiency | 0.95 | - |
| Battery discharge efficiency | 0.95 | - |

## Completed retained sweeps

These are the sweep sets currently retained in the working summary CSV files and thesis-facing figure workflow.

| Sweep parameter | Baseline | Values tested | Retained source summary |
|---|---:|---|---|
| Start-up cost | 700 g/start | 350, 500, 550, 600, 650, 700, 1000, 1500 g/start | `analysis/output/sensitivity/startup_cost/summary.csv` |
| Terminal SOC requirement | 50 % | 30, 40, 50, 60 % | `analysis/output/sensitivity/terminal_reserve/summary.csv` |
| Minimum SOC constraint | 20 % | 20, 30, 40 % | `analysis/output/sensitivity/soc_min/summary.csv` |
| Initial SOC | 70 % | 50, 60, 70, 80 % | `analysis/output/sensitivity/initial_soc/summary.csv` |
| Battery charge/discharge efficiency | 0.95 | 0.92, 0.95, 0.98 | `analysis/output/sensitivity/battery_efficiency/summary.csv` |

## Battery-efficiency sweep note

The battery-efficiency sweep was first explored with:

- `0.90, 0.95, 0.98`

That first test showed a strong response, but the lower bound was then tightened to keep the sweep centered more cleanly around the thesis baseline.

The retained battery-efficiency sweep for documentation and figures is therefore:

- `0.92, 0.95, 0.98`

The currently active summary file is:

- `analysis/output/sensitivity/battery_efficiency/summary.csv`

## Parameter count summary

| Sweep parameter | Number of tested cases |
|---|---:|
| Start-up cost | 8 |
| Terminal SOC requirement | 4 |
| Minimum SOC constraint | 3 |
| Initial SOC | 4 |
| Battery charge/discharge efficiency | 3 retained cases |

Total retained tested cases across all completed sweeps: `22`

If the initial exploratory `0.90` battery-efficiency point is also counted as part of the broader process history, the total tested cases becomes `23`.
