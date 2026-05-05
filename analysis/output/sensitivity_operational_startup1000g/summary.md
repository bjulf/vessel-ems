# Operational 3-Day Offline MILP Sensitivity Summary

Generated: 2026-05-04

Config: `config/operational_model_soc60_no_terminal_startup1000g_sensitivity.toml`

Scope:
- Full-horizon offline MILP through `main_baseline.jl`
- 3-day operational 15-minute average load profile: `data/operational_profiles/operational_load_profile_15min_avg.csv`
- 265 timesteps from `2026-03-01 00:00` to `2026-03-03 18:00`
- No enforced terminal SOC constraint; the stored 50% terminal value is a reference only
- Initial battery SOC is 60%, matching the operational comparison baseline
- Minimum SOC is 20%, startup cost is 1000 g/start, and charge/discharge efficiency is 0.95 unless varied

Outputs:
- Startup-cost sweep: `analysis/output/sensitivity_operational_startup1000g/startup_cost/`
- Minimum-SOC sweep: `analysis/output/sensitivity_operational_startup1000g/soc_min/`
- Initial-SOC sweep: `analysis/output/sensitivity_operational_startup1000g/initial_soc/`
- Battery-efficiency sweep: `analysis/output/sensitivity_operational_startup1000g/battery_efficiency/`

Validation:
- Standard sweeps completed successfully.
- Focused startup-cost scan completed successfully.
- 23 unique run directories were produced or reused by the package manifests.
- All 23 runs solved to `OPTIMAL`.
- Standard run-local verification plots were generated for every run:
  - `plots/verification_overview.png`
  - `plots/verification_stress_window.png`

## Baseline Case

The operational baseline case at 60% initial SOC, 20% minimum SOC, eta 0.95, and 1000 g/start produced:

| Metric | Value |
| --- | ---: |
| Fuel | 671.394 kg |
| Starts | 4 |
| Stops | 4 |
| Minimum SOC | 20.00% |
| Terminal SOC | 20.00% |
| Battery throughput | 1962.4 kWh |

## Startup Cost

The operational horizon is almost insensitive to startup cost across the main tested band.

| Startup cost [g/start] | Fuel [kg] | Starts | Notes |
| ---: | ---: | ---: | --- |
| 350 | 671.037 | 5 | Slightly lower fuel, one extra start |
| 500 | 671.394 | 4 | Same dispatch family as baseline |
| 700 | 671.394 | 4 | Same dispatch family as baseline |
| 1000 | 671.394 | 4 | Baseline |
| 1500 | 671.394 | 4 | Same fuel dispatch, larger objective penalty only |

The focused 500-1100 g/start scan found the same 4-start solution throughout 500-1100 g/start. Unlike the synthetic 24-hour case, there is no sharp transition near 850 g/start in the operational 3-day average-load horizon.

## Minimum SOC

Minimum SOC is materially influential on the operational horizon.

| Minimum SOC [%] | Fuel [kg] | Starts | Terminal SOC [%] | Solve time [s] |
| ---: | ---: | ---: | ---: | ---: |
| 20 | 671.394 | 4 | 20.00 | 3.146 |
| 30 | 689.897 | 4 | 30.00 | 2.955 |
| 40 | 708.851 | 6 | 40.00 | 90.525 |

Raising the SOC floor from 20% to 40% increases fuel by about 37.46 kg and adds two starts. The 40% case also has a much longer solve time.

## Initial SOC

Initial SOC has a nearly linear fuel effect on this no-terminal operational horizon, while starts remain unchanged.

| Initial SOC [%] | Fuel [kg] | Starts | Terminal SOC [%] |
| ---: | ---: | ---: | ---: |
| 50 | 689.897 | 4 | 20.00 |
| 60 | 671.394 | 4 | 20.00 |
| 70 | 652.890 | 4 | 20.00 |
| 80 | 634.387 | 4 | 20.00 |

Because the model is not required to restore terminal SOC, higher initial SOC is converted directly into lower fuel consumption. This is expected behavior for an offline lower-bound benchmark, but comparisons should clearly state the assumed initial SOC.

## Battery Efficiency

Battery efficiency has a moderate fuel effect but does not change the start count in this sweep.

| Efficiency | Fuel [kg] | Starts | Terminal SOC [%] |
| ---: | ---: | ---: | ---: |
| 0.92 | 684.272 | 4 | 20.00 |
| 0.95 | 671.394 | 4 | 20.00 |
| 0.98 | 658.985 | 4 | 20.00 |

## Interpretation

For the 3-day operational average-load horizon, the main sensitivity story differs from the synthetic 24-hour package:

- Startup cost is not a major driver once it is at least 500 g/start; the dispatch remains at 4 starts across the focused scan.
- Minimum SOC is a strong modeling choice because it directly raises fuel and can alter starts.
- Initial SOC is highly visible in fuel totals because there is no terminal restoration requirement.
- Battery efficiency affects fuel totals, but not commitment count, over the tested range.

The 20% minimum SOC and no-terminal formulation are defensible for an offline lower-bound comparison, but they should be described as a permissive benchmark. For operational realism or controller comparison, the initial SOC assumption and terminal reserve policy matter more than startup-cost tuning in this 3-day average-load case.
