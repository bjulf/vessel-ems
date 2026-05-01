# 3-Day Minimum Up-Time Sensitivity

Focused check on the original 3-day frozen balanced controller. I interpreted "3 hour dataset" as the 3-day operational profile used for the frozen thesis contenders. H16, MA4, startup cost 500 g/start, soft SOC penalty 10000 g/kWh, shutdown cost 0, no terminal reserve, and the 3-day 15-minute average operational profile are held fixed. Only `min_up_time_steps` changes.

## Results

| Min-up | Hours | Fuel kg | Delta vs full | Starts | Full starts | Min SOC | Final SOC | Run count | Min-length runs | P95 solve | Nonoptimal local solves |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 | 1.5 | 688.44 | 2.54% | 5 | 4 | 20.09% | 27.44% | 5 | 1 | 1.518 s | 0 |
| 8 | 2.0 | 706.61 | 5.25% | 6 | 4 | 22.11% | 35.62% | 6 | 2 | 1.832 s | 0 |
| 12 | 3.0 | 733.12 | 9.19% | 5 | 4 | 20.80% | 47.41% | 5 | 2 | 1.171 s | 0 |

## Assessment

- On the 3-day profile, extending minimum up-time is not beneficial for the balanced baseline.
- `min_up=8` increases starts from 5 to 6 and raises fuel penalty from 2.54% to 5.25%. That is a weak result on this profile.
- `min_up=12` returns starts to 5, but fuel penalty rises sharply to 9.19% and final SOC rises to 47.41%. It does not improve the 3-day frozen baseline.
- Neither case has SOC slack or nonoptimal local solves, so the issue is not feasibility. It is that the longer persistence rule does not match this shorter March profile as well as it matched the 6-day January profile.

Conclusion: the minimum-up extension is profile-dependent. The 6-day profile supported `min_up=8` and made `min_up=12` plausible as a low-cycling policy, but the 3-day profile supports keeping `min_up=6` as the original balanced frozen contender. I would not promote `min_up=12` to the main baseline unless the thesis explicitly prioritizes low cycling over fuel closeness across profiles.

## Plots

- `plots/min_up_sensitivity_metrics_3day.png`
- `plots/fuel_start_tradeoff_min_up_3day.png`
- `plots/three_day_vs_six_day_min_up_response.png`
- `plots/cases/`: copied run-local dispatch, rolling-vs-full, and verification plots for each case.
