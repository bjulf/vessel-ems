# Forecast Soft-SOC Horizon Sweep

Operational 15-minute average profile, moving-average forecast, soft 20-80% SOC band.
Soft SOC penalty scaling: `mean`.

## By Horizon

| H steps | Horizon h | Fuel kg | Delta % | Starts | Short runs | Min SOC % | Final SOC % | P95 solve s | Non-opt |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 | 2.00 | 704.680 | 4.96 | 12 | 7 | 20.26 | 36.68 | 0.227 | 0 |
| 12 | 3.00 | 709.212 | 5.63 | 9 | 4 | 22.10 | 39.77 | 0.290 | 0 |
| 16 | 4.00 | 710.484 | 5.82 | 8 | 3 | 25.49 | 40.21 | 0.446 | 0 |
| 24 | 6.00 | 724.055 | 7.84 | 7 | 2 | 28.44 | 47.40 | 0.768 | 0 |

## Ranked By Fuel Delta

| Rank | H steps | Horizon h | Fuel kg | Delta % | Starts | Final SOC % |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 8 | 2.00 | 704.680 | 4.96 | 12 | 36.68 |
| 2 | 12 | 3.00 | 709.212 | 5.63 | 9 | 39.77 |
| 3 | 16 | 4.00 | 710.484 | 5.82 | 8 | 40.21 |
| 4 | 24 | 6.00 | 724.055 | 7.84 | 7 | 47.40 |
