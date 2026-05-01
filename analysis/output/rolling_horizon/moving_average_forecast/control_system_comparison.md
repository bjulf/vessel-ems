# Control System Comparison

Fuel delta is relative to the matching full-horizon MILP for the same load profile.

The oracle rows below are preserved terminal-reserve runs from the earlier comparison set. They are not the current soft-SOC oracle baseline configs; regenerate this table before using it as the final oracle-vs-prediction soft-SOC comparison.

| Case | Control system | Fuel [kg] | Delta vs full [%] | Starts | Min SOC [%] | Final SOC [%] | Power balance |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Synthetic | Full-horizon MILP | 807.828 | +0.00 | 2 | 20.00 | 20.00 | yes |
| Synthetic | Rule-based supervisory logic | 828.940 | +2.61 | 5 | 14.03 | 17.42 | yes |
| Synthetic | Oracle terminal-reserve rolling MILP | 855.359 | +5.88 | 3 | 33.02 | 46.70 | yes |
| Synthetic | Moving-average soft-SOC rolling MILP | 858.309 | +6.25 | 7 | 43.48 | 46.56 | yes |
| Operational | Full-horizon MILP | 671.394 | +0.00 | 4 | 20.00 | 20.00 | yes |
| Operational | Rule-based supervisory logic | 784.533 | +16.85 | 4 | 18.29 | 71.19 | yes |
| Operational | Oracle terminal-reserve rolling MILP | 763.805 | +13.76 | 6 | 29.88 | 69.74 | yes |
| Operational | Moving-average soft-SOC rolling MILP | 735.110 | +9.49 | 8 | 29.37 | 53.51 | yes |

## Notes

- Synthetic / Full-horizon MILP: Offline lower-bound benchmark; no terminal SOC constraint.
- Synthetic / Rule-based supervisory logic: Rule-based verification output; controller uses soft SOC thresholds with 0-100% physical battery bounds.
- Synthetic / Oracle terminal-reserve rolling MILP: Preserved oracle rolling MILP with realized future load over the local horizon and a terminal reserve soft target.
- Synthetic / Moving-average soft-SOC rolling MILP: Soft-SOC20 controller; forecast[1] is realized load, look-ahead uses 4-step trailing moving average; no terminal reserve.
- Operational / Full-horizon MILP: Offline lower-bound benchmark; no terminal SOC constraint.
- Operational / Rule-based supervisory logic: Rule-based verification output; controller uses soft SOC thresholds with 0-100% physical battery bounds.
- Operational / Oracle terminal-reserve rolling MILP: Preserved oracle rolling MILP with realized future load over the local horizon and a terminal reserve soft target.
- Operational / Moving-average soft-SOC rolling MILP: Soft-SOC20 controller; forecast[1] is realized load, look-ahead uses 4-step trailing moving average; no terminal reserve.
