# Forecast Soft-SOC Horizon Sweep Assessment

Operational 15-minute average profile, moving-average forecast, soft 20-80% SOC band, `mean` soft-SOC penalty scaling.

## Completed Cases

| H steps | Horizon [h] | Fuel [kg] | Delta vs offline [%] | Starts | Short runs | Min SOC [%] | Final SOC [%] | P95 solve [s] |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 | 2.00 | 704.680 | 4.96 | 12 | 7 | 20.26 | 36.68 | 0.227 |
| 12 | 3.00 | 709.212 | 5.63 | 9 | 4 | 22.10 | 39.77 | 0.290 |
| 16 | 4.00 | 710.484 | 5.82 | 8 | 3 | 25.49 | 40.21 | 0.446 |
| 24 | 6.00 | 724.055 | 7.84 | 7 | 2 | 28.44 | 47.40 | 0.768 |

## Assessment

- Best fuel result: H=8 (2.0 h), 704.680 kg, 4.96% above offline, with 12 starts.
- Best starts result among completed cases: H=24 (6.0 h), 7 starts, but 7.84% above offline.
- Current H=24 baseline: 7.84% above offline, 7 starts, final SOC 47.40%.
- Short 1-2 timestep generator runs are counted from realized commitment blocks in `dispatch_results.csv`.

## Generated Figures

- `forecast_soft_soc_horizon_sweep_overview.png`
- `forecast_soft_soc_horizon_tradeoff.png`
