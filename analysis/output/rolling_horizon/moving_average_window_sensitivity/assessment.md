# Moving-Average Window Sensitivity

Scope: compact rolling-horizon forecast-window sweep only. Fixed setup uses the operational 15-minute average load profile, moving-average forecast, soft SOC band 20-80%, mean soft-SOC penalty scaling, startup cost 500 g/start, min_up_time_steps=6, no terminal reserve, 30 s local solve limit, 564 kWh initial battery energy, and initial commitment [0, 0].

The March 2 indicator is true when the same generator is online at every 15-minute dispatch interval from 2026-03-02 15:15 up to 19:45. The fraction is the best single-generator online fraction over that half-open interval.

## Reference Cases

- H16 MA4 P10k baseline reference: `balanced_h16_p10k_ma04`: fuel 688.44 kg (+2.54%), 5 starts, final SOC 27.44%, March 2 fraction 0.67, continuous=False.
- H24 MA4 P20k conservative reference: `conservative_h24_p20k_ma04`: fuel 717.71 kg (+6.90%), 5 starts, final SOC 43.60%, March 2 fraction 1.00, continuous=True.

## Main Readout

- Best balanced-family case by the cleanliness-first ranking: `balanced_h16_p10k_ma04`: fuel 688.44 kg (+2.54%), 5 starts, final SOC 27.44%, March 2 fraction 0.67, continuous=False.
- Best conservative-family case by the cleanliness-first ranking: `conservative_h24_p20k_ma02`: fuel 720.78 kg (+7.36%), 5 starts, final SOC 45.94%, March 2 fraction 0.78, continuous=False.

## Cautious-Operator Behavior

- Cases reproducing continuous same-genset online behavior through the March 2 variable peak: `conservative_h24_p20k_ma04`.
- No clean case reproduced the March 2 continuous-online behavior with lower fuel than the H24 MA4 P20k conservative reference.

## Family Tables

### balanced_h16_p10k

| MA window | Clean | Fuel kg | Delta % | Starts | Min SOC % | Final SOC % | Run lengths | March 2 frac | March 2 continuous | P95 solve s | Nonopt/time/infeas |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: |
| 1 | yes | 704.36 | 4.91 | 7 | 21.53 | 34.35 | 17 12 6 6 6 6 19 | 0.50 | False | 2.707 | 0 |
| 2 | yes | 718.89 | 7.07 | 6 | 21.03 | 43.87 | 17 14 13 6 6 18 | 0.67 | False | 1.737 | 0 |
| 4 | yes | 688.44 | 2.54 | 5 | 20.09 | 27.44 | 18 13 14 6 19 | 0.67 | False | 1.814 | 0 |
| 8 | yes | 680.85 | 1.41 | 6 | 20.56 | 21.02 | 16 6 8 6 18 16 | 0.83 | False | 2.008 | 0 |
| 12 | yes | 706.14 | 5.18 | 6 | 21.86 | 35.54 | 15 6 9 6 18 19 | 0.83 | False | 1.788 | 0 |
| 16 | yes | 682.36 | 1.63 | 6 | 20.43 | 22.39 | 15 6 9 6 18 17 | 0.83 | False | 1.417 | 0 |

### conservative_h24_p20k

| MA window | Clean | Fuel kg | Delta % | Starts | Min SOC % | Final SOC % | Run lengths | March 2 frac | March 2 continuous | P95 solve s | Nonopt/time/infeas |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: |
| 1 | yes | 711.73 | 6.01 | 8 | 20.00 | 36.20 | 17 6 9 6 6 6 6 19 | 0.44 | False | 5.935 | 0 |
| 2 | yes | 720.78 | 7.36 | 5 | 22.43 | 45.94 | 18 13 13 7 22 | 0.78 | False | 5.011 | 0 |
| 4 | yes | 717.71 | 6.90 | 5 | 23.23 | 43.60 | 19 13 18 6 17 | 1.00 | True | 6.106 | 0 |
| 8 | yes | 740.47 | 10.29 | 6 | 26.00 | 54.53 | 17 6 9 6 16 23 | 0.89 | False | 5.637 | 0 |
| 12 | yes | 697.20 | 3.84 | 6 | 21.88 | 30.53 | 15 6 9 6 21 16 | 0.89 | False | 5.383 | 0 |
| 16 | yes | 704.29 | 4.90 | 6 | 21.11 | 34.12 | 15 6 9 6 19 16 | 0.89 | False | 4.758 | 0 |

## Recommendation

- Keep MA4 for the current H16 C500 P10k balanced baseline. Within this compact sweep, another moving-average window did not produce a cleaner balanced baseline under the starts/run-block/fuel tradeoff.
- For the H24 P20k conservative comparison, keep MA4 if the purpose is to represent the cautious March 2 operator behavior. `conservative_h24_p20k_ma02` has a cleaner generic run-block ranking, but it does not reproduce the continuous March 2 online block and does not reduce fuel relative to H24 MA4.
- Lower-fuel H24 alternatives exist (`conservative_h24_p20k_ma12` (6 starts, March 2 continuous=False), `conservative_h24_p20k_ma16` (6 starts, March 2 continuous=False), `conservative_h24_p20k_ma01` (8 starts, March 2 continuous=False)), but they add a start and lose the continuous March 2 block, so they are not better conservative-comparison cases.
- Longer moving-average windows should be described as smoother but more lagged; shorter windows are more responsive and can change start timing rather than representing a universally better forecast.

## Generated Artifacts

- `summary.csv`
- `plots/fuel_penalty_vs_ma_window.png`
- `plots/starts_vs_ma_window.png`
- `plots/final_soc_vs_ma_window.png`
- `plots/march2_online_fraction_continuity.png`
- `plots/dispatch_panels/rank01_balanced_h16_p10k_ma04_dispatch_panel.png`
- `plots/dispatch_panels/rank02_conservative_h24_p20k_ma04_dispatch_panel.png`
- `plots/dispatch_panels/rank03_conservative_h24_p20k_ma02_dispatch_panel.png`
- `plots/dispatch_panels/rank04_balanced_h16_p10k_ma08_dispatch_panel.png`
- `plots/dispatch_panels/rank05_balanced_h16_p10k_ma16_dispatch_panel.png`
