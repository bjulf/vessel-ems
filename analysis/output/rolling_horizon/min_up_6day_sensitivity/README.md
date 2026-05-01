# 6-Day Minimum Up-Time Sensitivity

Focused guardrail sensitivity from the frozen balanced 6-day controller. H16, MA4, startup cost 500 g/start, soft SOC penalty 10000 g/kWh, shutdown cost 0, no terminal reserve, and the 6-day 15-minute average operational profile are held fixed. Only `min_up_time_steps` changes.

## Results

| Min-up | Hours | Fuel kg | Delta vs full | Starts | Full starts | Min SOC | Max SOC | Final SOC | Realized low slack | Realized high slack | Run count | Min-length runs | P95 solve | Nonoptimal local solves |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 | 1.5 | 1630.05 | 2.38% | 16 | 11 | 20.37% | 66.35% | 33.71% | 0.00 | 0.00 | 16 | 13 | 2.068 s | 0 |
| 8 | 2.0 | 1628.62 | 2.29% | 13 | 11 | 20.02% | 60.00% | 34.54% | 0.00 | 0.00 | 13 | 10 | 1.407 s | 0 |
| 12 | 3.0 | 1654.35 | 3.90% | 10 | 11 | 20.24% | 70.01% | 46.72% | 0.00 | 0.00 | 10 | 7 | 0.720 s | 0 |
| 16 | 4.0 | 1730.17 | 8.66% | 9 | 11 | 16.91% | 86.92% | 81.95% | 160.71 | 502.16 | 9 | 7 | 0.634 s | 0 |

## Assessment

- Extending minimum up-time does exactly what we suspected: it reduces starts between peak clusters.
- `min_up=8` is the best first guardrail. It reduces starts from 16 to 13 and slightly improves fuel relative to the min-up-6 reference, while keeping minimum SOC above 20%, maximum SOC below 80%, and zero nonoptimal local solves.
- `min_up=12` is the strongest plausible anti-cycling option in this sweep. It reduces starts to 10, but fuel penalty rises to 3.90% and final SOC rises to 46.72%. This is usable only if start reduction is prioritized over fuel efficiency.
- `min_up=16` should be rejected for the thesis baseline. It reduces starts to 9, but fuel penalty jumps to 8.66% and the realized SOC trajectory leaves the preferred 20-80% operating band, with minimum SOC 16.91% and maximum SOC 81.95%.
- No case had nonoptimal/time-limit/infeasible local solves, so the issue is operational tradeoff rather than solver reliability.

Recommendation: use `min_up=8` as the next balanced-controller guardrail candidate. It is a cleaner and more physical fix than shutdown cost, and it avoids the terminal-SOC wall behavior. Keep `min_up=12` as an operator-style low-cycling comparison if the thesis wants to show the fuel/cycling tradeoff explicitly.

## Plots

- `plots/min_up_sensitivity_metrics.png`
- `plots/fuel_start_tradeoff_min_up.png`
- `plots/run_lengths_by_min_up.png`
- `plots/soc_and_start_timing_by_min_up.png`
- `plots/cases/`: copied run-local dispatch, rolling-vs-full, and verification plots for each case.
