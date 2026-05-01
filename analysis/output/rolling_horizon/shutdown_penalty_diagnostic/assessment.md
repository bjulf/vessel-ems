# Shutdown-Penalty Diagnostic

Scope: targeted diagnostic only. Fixed setup is the selected H16 MA4 rolling-horizon candidate: operational 15-minute average load profile, moving-average forecast with MA4, startup cost 500 g/start, soft SOC band 20-80%, mean-normalized soft-SOC penalty 10000 g/kWh, min_up_time_steps=6, no terminal reserve, 30 s local solve limit, 564 kWh initial battery energy, and initial commitment [0, 0].

The March 3 indicator uses the closed interval 2026-03-03 13:30 to 17:45. `continuous` means the same generator is online for every dispatch interval in that window; `online@17:45` means at least one generator is online at the endpoint.

## Recommendation

Shutdown penalty did not produce a clearly better clean case under the diagnostic criteria. Keep it as a diagnostic only and do not change the H16 MA4 C500 P10k min_up6 baseline recommendation.

This does not by itself replace the current H16 MA4 C500 P10k min_up6 baseline recommendation. The result should be described as a commitment-hysteresis / shutdown-myopia check, not as a broad thesis sensitivity sweep.

## Case Table

| Shutdown g | Clean | Fuel kg | Delta % | Starts | Shutdowns | Full starts | Full shutdowns | Min SOC % | Final SOC % | Run lengths | March 3 frac | Continuous | Online@17:45 | P95 solve s | Nonopt/time/infeas |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | --- | ---: | ---: |
| 0 | yes | 688.44 | 2.54 | 5 | 5 | 4 | 4 | 20.09 | 27.44 | 18 13 14 6 19 | 0.94 | False | False | 2.001 | 0 |
| 250 | yes | 713.44 | 6.26 | 7 | 6 | 4 | 4 | 21.99 | 39.57 | 18 13 6 7 7 6 18 | 0.94 | False | True | 3.905 | 0 |
| 500 | yes | 720.86 | 7.37 | 7 | 6 | 4 | 4 | 22.85 | 43.29 | 19 12 6 8 6 6 18 | 0.94 | False | True | 1.962 | 0 |
| 1000 | yes | 713.29 | 6.24 | 7 | 6 | 4 | 4 | 23.40 | 39.47 | 19 12 6 7 7 6 18 | 0.94 | False | True | 2.604 | 0 |

## Generated Artifacts

- `summary.csv`
- `plots/fuel_penalty_vs_shutdown_cost.png`
- `plots/starts_shutdowns_vs_shutdown_cost.png`
- `plots/final_soc_vs_shutdown_cost.png`
- `plots/march3_online_fraction_continuity.png`
- `plots/dispatch_panels/shutdown_cost_0000g_dispatch_panel.png`
- `plots/dispatch_panels/shutdown_cost_0250g_dispatch_panel.png`
- `plots/dispatch_panels/shutdown_cost_0500g_dispatch_panel.png`
- `plots/dispatch_panels/shutdown_cost_1000g_dispatch_panel.png`
