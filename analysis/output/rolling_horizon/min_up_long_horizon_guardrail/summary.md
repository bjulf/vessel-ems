# Long-Horizon Guardrail Sweep

Four-case extension of the compact baseline confirmation sweep: H20/H24, startup 500 g/start, soft SOC penalty 10000 or 20000 g/kWh, 6-step minimum up-time, no soft-band terminal reserve.

Reference from the 18-case sweep: `h16_startup500_softsoc10000_minup6`.

| Case | H | SOC penalty | Fuel kg | Delta % | Starts | Min SOC % | Final SOC % | Run lengths | P95 solve s | Max solve s | Nonopt/time/infeas |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| `h16_startup500_softsoc10000_minup6` ref | 16 | 10000 | 688.44 | 2.54 | 5 | 20.09 | 27.44 | 18 13 14 6 19 | 1.305 | 2.599 | 0 |
| `h20_startup500_softsoc10000_minup6` | 20 | 10000 | 708.75 | 5.56 | 6 | 20.43 | 38.13 | 19 14 11 7 6 17 | 2.277 | 4.837 | 0 |
| `h20_startup500_softsoc20000_minup6` | 20 | 20000 | 726.12 | 8.15 | 7 | 24.60 | 46.70 | 19 13 6 8 7 6 16 | 2.739 | 6.076 | 0 |
| `h24_startup500_softsoc10000_minup6` | 24 | 10000 | 720.01 | 7.24 | 7 | 21.79 | 43.75 | 19 13 6 8 7 6 17 | 4.534 | 7.749 | 0 |
| `h24_startup500_softsoc20000_minup6` | 24 | 20000 | 717.71 | 6.90 | 5 | 23.23 | 43.60 | 19 13 18 6 17 | 2.729 | 5.054 | 0 |

## Recommendation

Keep `h16_startup500_softsoc10000_minup6` as the rolling-horizon baseline.

The best-fuel long-horizon guardrail case is `h20_startup500_softsoc10000_minup6` at 708.75 kg and 5.56% fuel penalty, but this is worse than the H16 reference at 688.44 kg and 2.54%.

The P20k cases mainly push SOC upward and increase final SOC carryover; they do not improve the fuel/start tradeoff. The long-horizon guardrail therefore supports freezing H16 C500 P10k rather than extending the controller horizon.

## Generated Plots

- `plots/long_horizon_guardrail_fuel_starts.png`: fuel/start guardrail plot with H16 reference.
- `plots/cases/`: dispatch-panel and rolling-vs-full plots for all four guardrail cases.
- `plots/cases/h20_startup500_softsoc10000_minup6_dispatch_panel.png`
- `plots/cases/h20_startup500_softsoc10000_minup6_rolling_vs_full.png`
- `plots/cases/h20_startup500_softsoc20000_minup6_dispatch_panel.png`
- `plots/cases/h20_startup500_softsoc20000_minup6_rolling_vs_full.png`
- `plots/cases/h24_startup500_softsoc10000_minup6_dispatch_panel.png`
- `plots/cases/h24_startup500_softsoc10000_minup6_rolling_vs_full.png`
- `plots/cases/h24_startup500_softsoc20000_minup6_dispatch_panel.png`
- `plots/cases/h24_startup500_softsoc20000_minup6_rolling_vs_full.png`
