# Combined Rolling-Horizon Baseline Assessment

This combines the 18-case confirmatory sweep with the 4-case H20/H24 guardrail sweep. All 22 cases are clean on realized SOC slack, minimum-up violations, and nonoptimal/time-limited/infeasible local solves.

## Main Read

`h24_startup500_softsoc20000_minup6` is visually and operationally attractive because it has only 5 starts, long commitment blocks (`19 13 18 6 17`), and a higher SOC buffer: minimum SOC 23.23% and final SOC 43.60%.

Its strongest operational argument is the March 2 afternoon/evening variable peak: it keeps one genset committed continuously from 15:15 to 19:45, while the H16 P10k baseline splits that part of the day into two shorter blocks with an off-period before the evening spike. That makes H24 P20k look more like a cautious watchstanding policy through uncertain high-load operation.

The cost is material: 717.71 kg fuel and 6.90% penalty versus 688.44 kg and 2.54% for `h16_startup500_softsoc10000_minup6`. It also ends 16.16 percentage points higher in SOC, so part of the impression is a more conservative energy carryover rather than pure dispatch efficiency.

## Recommendation

Keep `h16_startup500_softsoc10000_minup6` as the main thesis baseline if the baseline should be quantitatively efficient while still clean: 5 starts, fuel penalty 2.54%, final SOC 27.44%, and long enough commitment blocks (`18 13 14 6 19`).

Use `h24_startup500_softsoc20000_minup6` as a conservative/visual comparison case rather than replacing the baseline. It is defensible if the narrative is operational reserve and smoothness, but it should be described as a higher-SOC, higher-fuel controller setting.

`h12_startup500_softsoc5000_minup6` remains the fuel-minimum clean case at 1.33% penalty, but it has 7 starts and a low final SOC of 21.41%, so it is less attractive as the final baseline.

## Selected Cases

| Case | H | C | P | Fuel kg | Delta % | Starts | Min SOC % | Final SOC % | Run lengths | P95 s | Max s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| `h16_startup500_softsoc10000_minup6` | 16 | 500 | 10000 | 688.44 | 2.54 | 5 | 20.09 | 27.44 | 18 13 14 6 19 | 1.305 | 2.599 |
| `h24_startup500_softsoc20000_minup6` | 24 | 500 | 20000 | 717.71 | 6.90 | 5 | 23.23 | 43.60 | 19 13 18 6 17 | 2.729 | 5.054 |
| `h12_startup500_softsoc5000_minup6` | 12 | 500 | 5000 | 680.31 | 1.33 | 7 | 20.22 | 21.41 | 17 6 10 8 7 6 16 | 0.875 | 2.059 |
| `h12_startup500_softsoc10000_minup6` | 12 | 500 | 10000 | 700.97 | 4.40 | 6 | 20.29 | 33.53 | 17 13 10 6 6 19 | 0.833 | 1.436 |
| `h20_startup500_softsoc10000_minup6` | 20 | 500 | 10000 | 708.75 | 5.56 | 6 | 20.43 | 38.13 | 19 14 11 7 6 17 | 2.277 | 4.837 |

## Best Fuel Cases

| Case | H | C | P | Fuel kg | Delta % | Starts | Min SOC % | Final SOC % | Run lengths | P95 s | Max s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| `h12_startup500_softsoc5000_minup6` | 12 | 500 | 5000 | 680.31 | 1.33 | 7 | 20.22 | 21.41 | 17 6 10 8 7 6 16 | 0.875 | 2.059 |
| `h12_startup250_softsoc5000_minup6` | 12 | 250 | 5000 | 685.54 | 2.16 | 8 | 20.08 | 24.25 | 15 6 9 6 7 7 6 17 | 0.908 | 1.748 |
| `h16_startup500_softsoc10000_minup6` | 16 | 500 | 10000 | 688.44 | 2.54 | 5 | 20.09 | 27.44 | 18 13 14 6 19 | 1.305 | 2.599 |
| `h16_startup250_softsoc10000_minup6` | 16 | 250 | 10000 | 690.99 | 2.97 | 8 | 20.09 | 27.24 | 16 6 8 6 6 9 6 16 | 1.702 | 3.360 |
| `h12_startup250_softsoc10000_minup6` | 12 | 250 | 10000 | 698.05 | 4.03 | 8 | 20.88 | 29.83 | 15 6 8 6 8 6 6 16 | 1.016 | 2.076 |
| `h12_startup500_softsoc10000_minup6` | 12 | 500 | 10000 | 700.97 | 4.40 | 6 | 20.29 | 33.53 | 17 13 10 6 6 19 | 0.833 | 1.436 |

## Lowest-Start Cases

| Case | H | C | P | Fuel kg | Delta % | Starts | Min SOC % | Final SOC % | Run lengths | P95 s | Max s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| `h16_startup500_softsoc10000_minup6` | 16 | 500 | 10000 | 688.44 | 2.54 | 5 | 20.09 | 27.44 | 18 13 14 6 19 | 1.305 | 2.599 |
| `h16_startup1000_softsoc10000_minup6` | 16 | 1000 | 10000 | 713.14 | 6.22 | 5 | 20.17 | 40.15 | 19 12 14 6 22 | 0.995 | 2.521 |
| `h24_startup500_softsoc20000_minup6` | 24 | 500 | 20000 | 717.71 | 6.90 | 5 | 23.23 | 43.60 | 19 13 18 6 17 | 2.729 | 5.054 |
| `h12_startup500_softsoc10000_minup6` | 12 | 500 | 10000 | 700.97 | 4.40 | 6 | 20.29 | 33.53 | 17 13 10 6 6 19 | 0.833 | 1.436 |
| `h16_startup500_softsoc5000_minup6` | 16 | 500 | 5000 | 701.24 | 4.45 | 6 | 21.41 | 34.22 | 19 13 11 7 6 18 | 1.674 | 3.177 |
| `h20_startup500_softsoc10000_minup6` | 20 | 500 | 10000 | 708.75 | 5.56 | 6 | 20.43 | 38.13 | 19 14 11 7 6 17 | 2.277 | 4.837 |
| `h12_startup1000_softsoc5000_minup6` | 12 | 1000 | 5000 | 718.35 | 6.99 | 6 | 20.56 | 42.13 | 17 16 8 7 6 18 | 0.657 | 1.705 |
| `h16_startup1000_softsoc5000_minup6` | 16 | 1000 | 5000 | 727.53 | 8.36 | 6 | 20.19 | 47.82 | 19 12 14 6 6 19 | 1.313 | 2.898 |

## Plots

- `plots/combined_fuel_start_tradeoff.png`
- `plots/combined_fuel_final_soc_tradeoff.png`
- `plots/combined_case_bars.png`
- `plots/selected_commitment_soc_timeline.png`
- `plots/third_peak_focused_comparison.png`
- `plots/selected_case_panels/`: copied dispatch and rolling-vs-full panels for selected cases.
- `plots/selected_case_panels/h12_startup500_softsoc10000_minup6_rolling_horizon_dispatch_panel.png`
- `plots/selected_case_panels/h12_startup500_softsoc10000_minup6_rolling_vs_full_horizon_comparison.png`
- `plots/selected_case_panels/h16_startup500_softsoc10000_minup6_rolling_horizon_dispatch_panel.png`
- `plots/selected_case_panels/h16_startup500_softsoc10000_minup6_rolling_vs_full_horizon_comparison.png`
- `plots/selected_case_panels/h20_startup500_softsoc10000_minup6_rolling_horizon_dispatch_panel.png`
- `plots/selected_case_panels/h20_startup500_softsoc10000_minup6_rolling_vs_full_horizon_comparison.png`
- `plots/selected_case_panels/h24_startup500_softsoc20000_minup6_rolling_horizon_dispatch_panel.png`
- `plots/selected_case_panels/h24_startup500_softsoc20000_minup6_rolling_vs_full_horizon_comparison.png`
