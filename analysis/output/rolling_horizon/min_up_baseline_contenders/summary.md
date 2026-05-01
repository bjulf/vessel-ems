# Minimum Up-Time Baseline Contenders

Operational 15-minute average profile, moving-average forecast, mean soft-SOC penalty, and 6-step minimum up-time.

| Rank | Case | H | Startup | SOC penalty | Fuel kg | Delta % | Starts | Min SOC % | Final SOC % | Runs | Run lengths | P95 solve s |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| 1 | h12_startup0_softsoc10000_minup6 | 12 | 0 | 10000 | 685.380 | 2.14 | 11 | 20.46 | 22.00 | 11 | `6 8 6 6 6 6 6 6 6 7 7` | 0.555 |
| 2 | h12_startup0_softsoc1000_minup6 | 12 | 0 | 1000 | 687.190 | 2.41 | 12 | 17.03 | 23.78 | 12 | `6 6 6 10 6 6 6 6 6 7 7 1` | 1.875 |
| 3 | h12_startup500_softsoc10000_minup6 | 12 | 500 | 10000 | 700.968 | 4.40 | 6 | 20.29 | 33.53 | 6 | `17 13 10 6 6 19` | 0.623 |
