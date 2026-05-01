# Frozen 6-Day Rolling-Horizon Contender Validation

This package validates the two frozen 3-day rolling-horizon thesis contenders on the 6-day operational 15-minute average load profile. Controller parameters were not retuned; the only model input change is the load profile path.

## Input

- Derived 6-day profile: `data/operational_profiles/operational_load_profile_6day_15min_avg.csv`
- Source prepared profile: `analysis/operational_load_cases/baseline_load_case/prepared/load_profile_15min_avg.csv`
- Horizon covered: 2026-01-26 01:00:00 to 2026-01-31 14:15:00 (534 steps at 15 minutes)

## Results

| Role | Case | Fuel kg | Delta vs full | Starts | Min SOC | Final SOC | Run count | Short runs | P95 solve | Nonoptimal local solves |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| main_balanced_baseline | `balanced_6day_h16_ma4_c500_p10k_minup6` | 1630.05 | 2.38% | 16 | 20.37% | 33.71% | 16 | 0 | 2.068 s | 0 |
| conservative_operator_comparison | `conservative_6day_h24_ma4_c500_p20k_minup6` | 1657.80 | 4.12% | 16 | 20.45% | 48.90% | 16 | 0 | 4.443 s | 0 |

## Comparison With Frozen 3-Day Counterparts

| Role | 3-day fuel delta | 6-day fuel delta | 3-day starts | 6-day starts | 3-day min SOC | 6-day min SOC | 3-day P95 solve | 6-day P95 solve |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| main_balanced_baseline | 2.54% | 2.38% | 5 | 16 | 20.09% | 20.37% | 1.518 s | 2.068 s |
| conservative_operator_comparison | 6.90% | 4.12% | 5 | 16 | 23.23% | 20.45% | 3.535 s | 4.443 s |

The 6-day profile is a different January operational window, so fuel, starts, and SOC values are not a like-for-like extension of the 3-day March profile. The comparison is interpreted as robustness validation rather than tuning evidence.

## Assessment

- Both 6-day cases solved with `OPTIMAL` full-horizon benchmarks and zero nonoptimal, time-limit, or infeasible rolling local solves.
- Neither case has realized low/high SOC slack; minimum SOC stays above the 20% physical lower bound in both runs.
- Both cases have 16 rolling starts versus 11 starts in the full-horizon benchmark. All rolling generator on-runs satisfy the 6-step minimum up-time; neither case has shorter-than-minimum runs, but many runs stop exactly at the 6-step minimum. This is a watch item for cycling behavior, not a validation failure on this profile.
- Local solve times remain usable for validation: balanced P95 is 2.068 s and max is 4.017 s; conservative P95 is 4.443 s and max is 6.318 s. The full-horizon benchmark solve is much slower, but that is offline validation overhead rather than rolling-controller runtime.
- The balanced case remains closer to the full-horizon fuel benchmark: 2.38% above full horizon versus 4.12% for the conservative case. This is directionally consistent with the frozen 3-day result, where balanced was also closer to full horizon.
- The conservative case keeps a higher terminal SOC, but pays for it with higher fuel while not reducing starts relative to the balanced case on this profile.

Conclusion: the 6-day robustness validation supports the frozen 3-day contender choice. It does not reveal severe issues that would justify changing the baseline recommendation: no physical SOC violation, no nonoptimal or infeasible local solves, no very poor local solve times, no min-up violations, and no obviously broken dispatch. The minimum-length runs should be reported transparently, but they do not reverse the balanced-vs-conservative ordering. The main balanced baseline remains the recommended thesis baseline, with the conservative case retained as the operator-style comparison.

## Key Plots

- `plots/balanced_6day_h16_ma4_c500_p10k_minup6_dispatch_panel.png`
- `plots/balanced_6day_h16_ma4_c500_p10k_minup6_rolling_vs_full.png`
- `plots/balanced_6day_h16_ma4_c500_p10k_minup6_verification_overview.png`
- `plots/balanced_6day_h16_ma4_c500_p10k_minup6_verification_stress_window.png`
- `plots/conservative_6day_h24_ma4_c500_p20k_minup6_dispatch_panel.png`
- `plots/conservative_6day_h24_ma4_c500_p20k_minup6_rolling_vs_full.png`
- `plots/conservative_6day_h24_ma4_c500_p20k_minup6_verification_overview.png`
- `plots/conservative_6day_h24_ma4_c500_p20k_minup6_verification_stress_window.png`

## Comparison Plots

- `plots/controller_metric_comparison_6day.png`: 6-day fuel penalty, starts, minimum SOC, and P95 solve time.
- `plots/fuel_vs_final_soc_tradeoff_6day.png`: fuel-reserve tradeoff between the two frozen controllers.
- `plots/three_day_vs_six_day_robustness.png`: 3-day frozen result versus 6-day validation for fuel penalty and local solve time.
