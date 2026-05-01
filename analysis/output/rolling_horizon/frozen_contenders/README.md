# Frozen Rolling-Horizon Contenders

These are the frozen 3-day operational-profile contenders after the shutdown-penalty diagnostic. Both accepted runs have zero nonoptimal/time-limit/infeasible local solves.

| Role | Case | Fuel kg | Delta vs full | Starts | Min SOC | Final SOC | P95 solve | Run dir |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| main_balanced_baseline | `balanced_h16_ma4_c500_p10k_minup6` | 688.44 | 2.54% | 5 | 20.09% | 27.44% | 1.518 s | `runs/2026-04-29_170441_rolling_horizon_thesis_balanced_h16_ma4_c500_p10k_minup6` |
| conservative_operator_comparison | `conservative_h24_ma4_c500_p20k_minup6` | 717.71 | 6.90% | 5 | 23.23% | 43.60% | 3.535 s | `runs/2026-04-29_172100_rolling_horizon_thesis_conservative_h24_ma4_c500_p20k_minup6` |

## Decision

- Use `balanced_h16_ma4_c500_p10k_minup6` as the main balanced rolling-horizon thesis baseline.
- Use `conservative_h24_ma4_c500_p20k_minup6` as the conservative/operator-style comparison case.
- Keep shutdown cost at `0.0`; the shutdown-penalty diagnostic is rejected as a baseline mechanism.

## Key Plots

- `plots/balanced_h16_ma4_c500_p10k_minup6_dispatch_panel.png`
- `plots/balanced_h16_ma4_c500_p10k_minup6_rolling_vs_full.png`
- `plots/balanced_h16_ma4_c500_p10k_minup6_verification_overview.png`
- `plots/balanced_h16_ma4_c500_p10k_minup6_verification_stress_window.png`
- `plots/conservative_h24_ma4_c500_p20k_minup6_dispatch_panel.png`
- `plots/conservative_h24_ma4_c500_p20k_minup6_rolling_vs_full.png`
- `plots/conservative_h24_ma4_c500_p20k_minup6_verification_overview.png`
- `plots/conservative_h24_ma4_c500_p20k_minup6_verification_stress_window.png`
