# Rolling-Horizon Confirmatory Baseline Sweep

Fixed setup: operational 15-minute average load profile, MA4 moving-average forecast, soft SOC band 20-80%, mean-normalized SOC penalty, 6-step minimum up-time, no soft-band terminal reserve, 30 s local solve limit, initial SOC 60% / 564 kWh, initial commitment [0, 0].

Offline full-horizon MILP benchmarks are solved per generated config and have no terminal SOC constraint. Final SOC differences therefore matter when interpreting the rolling fuel penalty.

## Recommendation

Use `h16_startup500_softsoc10000_minup6` for the clean final baseline rerun.

This case uses H=16 (4.0 h), startup cost 500 g/start, soft SOC penalty 10000 g/kWh, and min_up_time_steps=6.

It gives 688.44 kg fuel (2.54% vs full horizon), 5 starts, minimum SOC 20.09%, final SOC 27.44% (+7.44 pp vs full horizon), and no nonoptimal/time-limited/infeasible local solves.

The lowest-fuel clean case is `h12_startup500_softsoc5000_minup6` at 1.33% fuel penalty and 7 starts. It is not the top recommendation under the commitment-cleanliness preference.

## Ranked Clean Contenders

| Rank | Case | Status | H | Startup | SOC penalty | Fuel kg | Delta % | Starts | Min SOC % | Final SOC % | Run lengths | P95 solve s | Nonopt/time/infeas |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| 1 | `h16_startup500_softsoc10000_minup6` | clean | 16 | 500 | 10000 | 688.44 | 2.54 | 5 | 20.09 | 27.44 | 18 13 14 6 19 | 1.305 | 0 |
| 2 | `h16_startup1000_softsoc10000_minup6` | clean | 16 | 1000 | 10000 | 713.14 | 6.22 | 5 | 20.17 | 40.15 | 19 12 14 6 22 | 0.995 | 0 |
| 3 | `h16_startup500_softsoc5000_minup6` | clean | 16 | 500 | 5000 | 701.24 | 4.45 | 6 | 21.41 | 34.22 | 19 13 11 7 6 18 | 1.674 | 0 |
| 4 | `h12_startup1000_softsoc5000_minup6` | clean | 12 | 1000 | 5000 | 718.35 | 6.99 | 6 | 20.56 | 42.13 | 17 16 8 7 6 18 | 0.657 | 0 |
| 5 | `h12_startup500_softsoc10000_minup6` | clean | 12 | 500 | 10000 | 700.97 | 4.40 | 6 | 20.29 | 33.53 | 17 13 10 6 6 19 | 0.833 | 0 |
| 6 | `h16_startup1000_softsoc5000_minup6` | clean | 16 | 1000 | 5000 | 727.53 | 8.36 | 6 | 20.19 | 47.82 | 19 12 14 6 6 19 | 1.313 | 0 |
| 7 | `h12_startup500_softsoc5000_minup6` | clean | 12 | 500 | 5000 | 680.31 | 1.33 | 7 | 20.22 | 21.41 | 17 6 10 8 7 6 16 | 0.875 | 0 |
| 8 | `h12_startup1000_softsoc10000_minup6` | clean | 12 | 1000 | 10000 | 713.48 | 6.27 | 7 | 22.10 | 38.72 | 17 13 6 6 6 6 18 | 0.837 | 0 |
| 9 | `h12_startup250_softsoc5000_minup6` | clean | 12 | 250 | 5000 | 685.54 | 2.16 | 8 | 20.08 | 24.25 | 15 6 9 6 7 7 6 17 | 0.908 | 0 |
| 10 | `h12_startup250_softsoc10000_minup6` | clean | 12 | 250 | 10000 | 698.05 | 4.03 | 8 | 20.88 | 29.83 | 15 6 8 6 8 6 6 16 | 1.016 | 0 |
| 11 | `h16_startup250_softsoc10000_minup6` | clean | 16 | 250 | 10000 | 690.99 | 2.97 | 8 | 20.09 | 27.24 | 16 6 8 6 6 9 6 16 | 1.702 | 0 |
| 12 | `h16_startup250_softsoc5000_minup6` | clean | 16 | 250 | 5000 | 728.26 | 8.53 | 8 | 20.49 | 47.30 | 16 6 8 6 6 8 6 20 | 1.857 | 0 |
| 13 | `h8_startup1000_softsoc10000_minup6` | clean | 8 | 1000 | 10000 | 706.02 | 5.16 | 8 | 20.00 | 33.33 | 17 6 8 6 6 6 6 18 | 0.254 | 0 |
| 14 | `h8_startup1000_softsoc5000_minup6` | clean | 8 | 1000 | 5000 | 706.04 | 5.16 | 8 | 20.11 | 33.33 | 17 6 8 6 6 6 6 18 | 0.283 | 0 |
| 15 | `h8_startup250_softsoc5000_minup6` | clean | 8 | 250 | 5000 | 706.80 | 5.33 | 8 | 20.10 | 33.33 | 17 6 8 6 6 6 6 19 | 0.397 | 0 |
| 16 | `h8_startup500_softsoc10000_minup6` | clean | 8 | 500 | 10000 | 711.21 | 5.93 | 8 | 20.60 | 35.76 | 17 6 8 6 6 6 6 19 | 0.251 | 0 |
| 17 | `h8_startup250_softsoc10000_minup6` | clean | 8 | 250 | 10000 | 711.23 | 5.99 | 8 | 20.00 | 35.76 | 17 6 8 6 6 6 6 19 | 0.346 | 0 |
| 18 | `h8_startup500_softsoc5000_minup6` | clean | 8 | 500 | 5000 | 709.82 | 5.72 | 8 | 20.06 | 35.76 | 17 6 8 6 6 6 6 19 | 0.285 | 0 |

## Fuel Ranking

| Rank | Case | Status | H | Startup | SOC penalty | Fuel kg | Delta % | Starts | Min SOC % | Final SOC % | Run lengths | P95 solve s | Nonopt/time/infeas |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| 1 | `h12_startup500_softsoc5000_minup6` | clean | 12 | 500 | 5000 | 680.31 | 1.33 | 7 | 20.22 | 21.41 | 17 6 10 8 7 6 16 | 0.875 | 0 |
| 2 | `h12_startup250_softsoc5000_minup6` | clean | 12 | 250 | 5000 | 685.54 | 2.16 | 8 | 20.08 | 24.25 | 15 6 9 6 7 7 6 17 | 0.908 | 0 |
| 3 | `h16_startup500_softsoc10000_minup6` | clean | 16 | 500 | 10000 | 688.44 | 2.54 | 5 | 20.09 | 27.44 | 18 13 14 6 19 | 1.305 | 0 |
| 4 | `h16_startup250_softsoc10000_minup6` | clean | 16 | 250 | 10000 | 690.99 | 2.97 | 8 | 20.09 | 27.24 | 16 6 8 6 6 9 6 16 | 1.702 | 0 |
| 5 | `h12_startup250_softsoc10000_minup6` | clean | 12 | 250 | 10000 | 698.05 | 4.03 | 8 | 20.88 | 29.83 | 15 6 8 6 8 6 6 16 | 1.016 | 0 |
| 6 | `h12_startup500_softsoc10000_minup6` | clean | 12 | 500 | 10000 | 700.97 | 4.40 | 6 | 20.29 | 33.53 | 17 13 10 6 6 19 | 0.833 | 0 |
| 7 | `h16_startup500_softsoc5000_minup6` | clean | 16 | 500 | 5000 | 701.24 | 4.45 | 6 | 21.41 | 34.22 | 19 13 11 7 6 18 | 1.674 | 0 |
| 8 | `h8_startup1000_softsoc10000_minup6` | clean | 8 | 1000 | 10000 | 706.02 | 5.16 | 8 | 20.00 | 33.33 | 17 6 8 6 6 6 6 18 | 0.254 | 0 |
| 9 | `h8_startup1000_softsoc5000_minup6` | clean | 8 | 1000 | 5000 | 706.04 | 5.16 | 8 | 20.11 | 33.33 | 17 6 8 6 6 6 6 18 | 0.283 | 0 |
| 10 | `h8_startup250_softsoc5000_minup6` | clean | 8 | 250 | 5000 | 706.80 | 5.33 | 8 | 20.10 | 33.33 | 17 6 8 6 6 6 6 19 | 0.397 | 0 |
| 11 | `h8_startup500_softsoc5000_minup6` | clean | 8 | 500 | 5000 | 709.82 | 5.72 | 8 | 20.06 | 35.76 | 17 6 8 6 6 6 6 19 | 0.285 | 0 |
| 12 | `h8_startup500_softsoc10000_minup6` | clean | 8 | 500 | 10000 | 711.21 | 5.93 | 8 | 20.60 | 35.76 | 17 6 8 6 6 6 6 19 | 0.251 | 0 |
| 13 | `h8_startup250_softsoc10000_minup6` | clean | 8 | 250 | 10000 | 711.23 | 5.99 | 8 | 20.00 | 35.76 | 17 6 8 6 6 6 6 19 | 0.346 | 0 |
| 14 | `h16_startup1000_softsoc10000_minup6` | clean | 16 | 1000 | 10000 | 713.14 | 6.22 | 5 | 20.17 | 40.15 | 19 12 14 6 22 | 0.995 | 0 |
| 15 | `h12_startup1000_softsoc10000_minup6` | clean | 12 | 1000 | 10000 | 713.48 | 6.27 | 7 | 22.10 | 38.72 | 17 13 6 6 6 6 18 | 0.837 | 0 |
| 16 | `h12_startup1000_softsoc5000_minup6` | clean | 12 | 1000 | 5000 | 718.35 | 6.99 | 6 | 20.56 | 42.13 | 17 16 8 7 6 18 | 0.657 | 0 |
| 17 | `h16_startup1000_softsoc5000_minup6` | clean | 16 | 1000 | 5000 | 727.53 | 8.36 | 6 | 20.19 | 47.82 | 19 12 14 6 6 19 | 1.313 | 0 |
| 18 | `h16_startup250_softsoc5000_minup6` | clean | 16 | 250 | 5000 | 728.26 | 8.53 | 8 | 20.49 | 47.30 | 16 6 8 6 6 8 6 20 | 1.857 | 0 |

## Generated Plots

- `plots/confirmatory_sweep_appendix_fuel_starts.png`: simple appendix fuel/start plot.
- `plots/top_contenders/`: copied dispatch-panel and rolling-vs-full plots for the top contenders.
- `plots/top_contenders/rank01_h16_startup500_softsoc10000_minup6_dispatch_panel.png`
- `plots/top_contenders/rank01_h16_startup500_softsoc10000_minup6_rolling_vs_full.png`
- `plots/top_contenders/rank02_h16_startup1000_softsoc10000_minup6_dispatch_panel.png`
- `plots/top_contenders/rank02_h16_startup1000_softsoc10000_minup6_rolling_vs_full.png`
- `plots/top_contenders/rank03_h16_startup500_softsoc5000_minup6_dispatch_panel.png`
- `plots/top_contenders/rank03_h16_startup500_softsoc5000_minup6_rolling_vs_full.png`
- `plots/top_contenders/rank04_h12_startup1000_softsoc5000_minup6_dispatch_panel.png`
- `plots/top_contenders/rank04_h12_startup1000_softsoc5000_minup6_rolling_vs_full.png`
- `plots/top_contenders/rank05_h12_startup500_softsoc10000_minup6_dispatch_panel.png`
- `plots/top_contenders/rank05_h12_startup500_softsoc10000_minup6_rolling_vs_full.png`
