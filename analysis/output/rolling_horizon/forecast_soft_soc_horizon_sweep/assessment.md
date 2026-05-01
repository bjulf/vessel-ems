# Forecast Soft-SOC Horizon Sweep Assessment

Operational 15-minute average profile, moving-average forecast, soft 20-80% SOC band. Longest attempted horizons were skipped/stopped after H=48 became slow; this assessment uses completed cases only.

## Completed Cases

| H steps | Horizon [h] | Fuel [kg] | Delta vs offline [%] | Starts | Min SOC [%] | Final SOC [%] | P95 solve [s] |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 1.00 | 703.551 | 4.79 | 17 | 20.38 | 35.32 | 0.073 |
| 8 | 2.00 | 713.436 | 6.26 | 10 | 20.66 | 40.90 | 0.448 |
| 12 | 3.00 | 724.377 | 7.89 | 7 | 21.14 | 47.38 | 0.753 |
| 16 | 4.00 | 727.208 | 8.31 | 8 | 24.91 | 49.36 | 0.878 |
| 24 | 6.00 | 735.110 | 9.49 | 8 | 29.37 | 53.51 | 2.999 |
| 32 | 8.00 | 731.253 | 8.92 | 9 | 32.04 | 51.56 | 3.702 |

## Assessment

- Best fuel result: H=4 (1.0 h), 703.551 kg, 4.79% above offline, with 17 starts.
- Best starts result among completed cases: H=12 (3.0 h), 7 starts, but 7.89% above offline.
- Current H=24 baseline: 9.49% above offline, 8 starts, final SOC 53.51%.
- Shorter horizons reduce fuel because they carry less battery energy at the end, but H=4 causes many starts.
- H=8 and H=12 are the most plausible compromise region in this sweep: materially lower fuel than H=24 with fewer starts than H=4.
- Longer horizons are not automatically better under the current soft-SOC objective; they tend to preserve more SOC and increase fuel.

## Generated Figures

- `forecast_soft_soc_horizon_sweep_overview.png`
- `forecast_soft_soc_horizon_tradeoff.png`
