# Synthetic Minimum Up-Time Comparison

Balanced rolling-horizon controller on the synthetic validation profile. H16, MA4, startup 500 g/start, soft SOC penalty 10000 g/kWh, shutdown cost 0, no terminal reserve, and synthetic initial SOC 658 kWh are fixed. Only `min_up_time_steps` changes.

## Results

| Min-up | Fuel kg | Delta vs full | Starts | Full starts | Min SOC | Max SOC | Final SOC | Run lengths | Short runs before end | P95 solve | Nonoptimal local solves |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| 6 | 858.13 | 6.44% | 6 | 4 | 38.55% | 70.00% | 45.88% | `6;40;22;3;6;2` | 0 | 1.106 s | 0 |
| 8 | 816.62 | 1.29% | 4 | 4 | 20.00% | 70.00% | 23.09% | `62;5;10;3` | 0 | 1.083 s | 0 |

## Assessment

- `min_up=8` is clearly better than `min_up=6` on the synthetic profile.
- Fuel penalty drops from 6.44% to 1.29%, and starts drop from 6 to 4, matching the full-horizon benchmark start count.
- The run remains clean: zero nonoptimal local solves and zero realized SOC slack.
- `min_up=8` ends at 23.09% SOC and touches the 20% lower bound, so it uses the battery more aggressively than `min_up=6`, but still stays inside the preferred 20-80% band.
- This strengthens `min_up=8` as a practical guardrail candidate: it helped on the 6-day operational profile and the synthetic profile. The caveat remains that it was weaker on the original 3-day operational profile.

## Plots

- `plots/synthetic_minup6_vs_minup8_metrics.png`
- `plots/synthetic_fuel_start_tradeoff_minup6_vs_8.png`
- Run-local copied plots are also stored in `plots/` with `balanced_synthetic_h16_ma4_c500_p10k_minup*` prefixes.
