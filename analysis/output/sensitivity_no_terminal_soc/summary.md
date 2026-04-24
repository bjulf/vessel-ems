# No-Terminal SOC Sensitivity Package Summary

This package reran the frozen baseline from `config/baseline_model_no_terminal_soc.toml` and compared it
against the older terminal-constrained package in `analysis/output/sensitivity/`.

No-terminal cases completed: 18
Total no-terminal wall-clock runtime: 707.8 s
Comparison outputs: `comparison/comparison_metrics.csv`, `comparison/fuel_response_comparison.png`,
`comparison/starts_response_comparison.png`, and `comparison/terminal_soc_response_comparison.png`.

## Sweep Comparison

| Sweep | Old fuel span [kg] | New fuel span [kg] | Old starts span | New starts span | Baseline fuel delta [kg] | Baseline starts delta | Baseline terminal delta [pp] | New avg solve [s] | New wall total [s] |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| startup cost | 2.26 | 3.32 | 4 | 6 | -55.64 | 2 | -30 | 2.6 | 271.6 |
| soc min | 1.21 | 35.94 | 2 | 1 | -55.64 | 2 | -30 | 6.6 | 93.3 |
| initial soc | 53.58 | 54.11 | 1 | 1 | -55.64 | 2 | -30 | 7.56 | 187.8 |
| battery efficiency | 9.26 | 9.87 | 7 | 6 | -55.64 | 2 | -30 | 9.07 | 155.2 |

## Findings

- Removing the terminal reserve cuts baseline fuel by 55.64 kg across the package, drops terminal SOC from 50% to 20%, and increases starts from 2 to 4.
- Old fuel-sensitivity ranking: initial soc (53.58), battery efficiency (9.26), startup cost (2.26), soc min (1.21).
- New fuel-sensitivity ranking: initial soc (54.11), soc min (35.94), battery efficiency (9.87), startup cost (3.32).
- The qualitative story changes mainly through `soc_min`: in the old package it was nearly inactive, while in the no-terminal package it becomes the second-strongest driver because the optimizer now uses the battery down to the configured floor.
- `startup_cost` remains a low-leverage calibration parameter. `battery_efficiency` still matters, but it does not dominate the result the way available battery energy does.

## Baseline Assessment

| Parameter | Judgment | Evidence |
| --- | --- | --- |
| Startup cost = 700 g/start | still defensible | The 500-700 g/start band is flat at 806.21 kg fuel and 4 starts. Moving to 1000 g/start only saves 2 starts at +1.62 kg fuel. |
| Minimum SOC = 20% | overly influential | Every no-terminal case finishes on the floor. Raising the floor to 30% and 40% increases fuel by 17.77 and 35.94 kg and lifts terminal SOC one-for-one. |
| Initial SOC = 70% | weakly justified | Moving from 70% to 80% cuts fuel by 18.17 kg with the same 4 starts. Dropping to 60% and 50% adds 17.81 and 35.94 kg and adds one start. |
| Battery efficiency = 0.95 | still defensible | The 0.92 to 0.98 range shifts fuel from 811.03 to 801.16 kg and starts from 7 to 1. The baseline sits near the middle of a plausible range. |
| No terminal SOC constraint | weakly justified | Removing the reserve lowers baseline fuel by 55.64 kg, lowers terminal SOC by 30 pp, and changes starts by +2. It works as a lower-bound scenario, not as a silent replacement for the terminal-constrained baseline. |

## Additional Sensitivity Recommendations

1. Add `battery.E_max` or an explicit usable-energy-window sweep if one more analysis is worth doing. The no-terminal package is clearly energy-budget limited, so this is the highest-value structural check.
2. Consider a generator-minimum-load or SFOC-shape sweep only if the thesis needs robustness on engine-model assumptions. That is secondary to battery-energy assumptions.
3. Do not add finer startup-cost sweeps. The current results already show a broad 500-700 g/start plateau, so extra resolution there is low value.

If no more sweep time is available, the current four-sweep no-terminal package is already enough to support a clear report claim: removing the terminal reserve materially lowers fuel use, keeps startup-cost conclusions mostly intact, and makes `soc_min` plus available battery energy the dominant assumptions.
