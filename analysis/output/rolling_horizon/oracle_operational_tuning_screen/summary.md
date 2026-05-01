# Oracle Operational Rolling-Horizon Tuning Screen

Coarse one-factor / small-candidate screen using oracle realized local load on the operational 15-minute average profile.

| Rank | Case | Strategy | H | Fuel kg | Delta % | Starts | Final SOC % | P95 solve s | Non-opt |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | soft_h24_soc20_p350_c1000 | soft_band | 24 | 701.622 | 4.50 | 12 | 34.79 | 1.940 | 0 |
| 2 | soft_h24_soc20_p1000_c1000 | soft_band | 24 | 707.323 | 5.35 | 13 | 34.79 | 2.004 | 0 |
| 3 | term_h24_t20_p1000_c1000 | terminal_reserve | 24 | 709.305 | 5.65 | 9 | 39.74 | 4.587 | 2 |
| 4 | term_h24_t20_p350_c1000 | terminal_reserve | 24 | 709.820 | 5.72 | 10 | 39.74 | 2.615 | 0 |
| 5 | soft_h24_soc20_p1000_c2500 | soft_band | 24 | 712.773 | 6.16 | 14 | 35.24 | 2.657 | 0 |
| 6 | soft_h24_soc20_p1000_c5000 | soft_band | 24 | 715.204 | 6.53 | 14 | 35.17 | 2.482 | 0 |
| 7 | soft_h24_soc20_p1500_c1000 | soft_band | 24 | 716.619 | 6.74 | 12 | 39.74 | 2.035 | 0 |
| 8 | soft_h24_soc30_p1000_c1000 | soft_band | 24 | 721.259 | 7.43 | 11 | 44.09 | 3.575 | 0 |
| 9 | soft_h48_soc20_p1000_c1000 | soft_band | 48 | 732.613 | 9.12 | 8 | 51.70 | 5.683 | 0 |
| 10 | soft_h24_soc40_p1000_c1000 | soft_band | 24 | 738.401 | 9.98 | 14 | 54.79 | 2.767 | 0 |
| 11 | soft_h72_soc20_p1000_c1000 | soft_band | 72 | 762.900 | 13.63 | 4 | 69.31 | 2.702 | 0 |
