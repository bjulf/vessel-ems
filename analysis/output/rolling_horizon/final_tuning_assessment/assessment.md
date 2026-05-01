# Final Rolling-Horizon Tuning Assessment

Assessment date: 2026-04-30.

## Recommendation

The rolling-horizon tuning process since 2026-04-27 is sufficient for thesis use. It covers the important controller choices: oracle versus implementable forecasted control, horizon length, moving-average forecast window, soft-SOC penalty scaling and magnitude, startup cost, shutdown cost, terminal reserve/SOC behavior, minimum up-time, 6-day operational robustness, and synthetic-profile robustness. I do not see an evidence-based reason to run another broad sweep before freezing the thesis baseline.

If the thesis baseline objective is closest fuel agreement with the full-horizon benchmark, use `config/rolling_horizon_thesis_balanced.toml` as the main practical rolling-horizon controller:

- H16, MA4 forecast, startup cost 500 g/start, shutdown cost 0, soft SOC penalty 10000 g/kWh, `min_up_time_steps = 6`, no terminal reserve.
- On the original 3-day operational profile: 688.44 kg fuel, +2.54% versus full horizon, 5 starts, minimum SOC 20.09%, final SOC 27.44%, zero nonoptimal local solves.
- On the 6-day operational profile without retuning: 1630.05 kg fuel, +2.38% versus full horizon, 16 starts, minimum SOC 20.37%, final SOC 33.71%, zero nonoptimal local solves.

If the thesis baseline objective is operationally cleaner commitment with a still-moderate fuel penalty, the H16/MA4/C500/P10k controller with `min_up_time_steps = 8` is also defensible as the main practical baseline:

- On the original 3-day operational profile: 706.61 kg fuel, +5.25% versus full horizon, 6 starts, minimum SOC 22.11%, final SOC 35.62%, zero nonoptimal local solves.
- Its 3-day commitment blocks are `18;15;10;8;8;15`, so it removes the 6-step minimum block seen in the min-up 6 baseline (`18;13;14;6;19`) and looks more like a deliberate persistence guardrail.
- On the 6-day operational profile it improves both fuel and starts versus min-up 6: +2.29% versus +2.38%, and 13 starts versus 16.
- On the synthetic check it is much stronger than min-up 6: +1.29% versus +6.44%, and 4 starts versus 6.

Therefore, the baseline choice should be stated as an objective choice, not as a purely technical winner:

- Fuel-efficient baseline: H16/MA4/C500/P10k/min-up 6.
- Operational guardrail baseline: H16/MA4/C500/P10k/min-up 8.

Use `config/rolling_horizon_thesis_conservative.toml` only as an optional high-reserve/operator comparison, not as the main baseline:

- H24, MA4, startup cost 500 g/start, shutdown cost 0, soft SOC penalty 20000 g/kWh, `min_up_time_steps = 6`, no terminal reserve.
- It preserves more SOC and gives a visually cautious March 2 online block, but it costs more fuel: +6.90% on the 3-day case and +4.12% on the 6-day case.

## Minimum-Up Decision

Do not reject `min_up_time_steps = 8` just because the 3-day fuel cost is higher. The right interpretation is objective-dependent.

`min_up = 8` is a strong practical guardrail candidate:

- 6-day operational: improves fuel slightly versus min-up 6 (+2.29% vs +2.38%) and reduces starts from 16 to 13, with no SOC slack and zero nonoptimal local solves.
- Synthetic: improves strongly versus min-up 6 (+1.29% vs +6.44%) and matches the full-horizon start count, with no meaningful SOC slack and zero nonoptimal local solves.

Its only important caveat is the original 3-day operational fuel/start metric:

- 3-day operational: fuel rises from +2.54% to +5.25% and starts rise from 5 to 6, but the run lengths become more regular and no longer include a 6-step minimum block.

The defensible thesis framing is:

- Main fuel-efficient baseline: min-up 6, selected on fuel closeness and validated on 6 days.
- Main operational guardrail baseline: min-up 8, selected on cleaner commitment persistence and stronger 6-day/synthetic robustness, while accepting the 3-day fuel premium.
- Optional low-cycling comparison: min-up 12 only if the thesis wants to show a deliberate fuel/cycling tradeoff. It is plausible on 6 days but too fuel-expensive for the main baseline, and it is weak on the 3-day case.
- Reject min-up 16 as a baseline because it causes preferred-band SOC violations on the 6-day case and raises fuel to +8.66%.

## Oracle MILP

Do not present oracle rolling-horizon MILP as the practical controller. The oracle screen uses realized future local load inside each local horizon, so it is not implementable.

It is useful as a diagnostic or appendix benchmark because it shows that perfect local-horizon load knowledge does not remove the rolling-controller gap. The requested oracle screen run, `runs/2026-04-27_171037_oracle_operational_screen_soft_h24_soc20_p1000_c1000`, used H24 with realized local load, soft 20-80% SOC, penalty 1000 g/kWh, startup 1000 g/start, and no terminal reserve. It achieved 707.32 kg fuel, +5.35% versus the full-horizon benchmark, 13 starts, minimum SOC essentially 20%, final SOC 34.79%, and zero nonoptimal local solves.

Recommended placement:

- Main method/results: keep focused on implementable forecasted rolling MILP.
- Appendix or short diagnostic paragraph: include oracle results only to explain the upper-bound/diagnostic role and why oracle local foresight is not the thesis controller.

## Concerns And Limitations

No evidence package reviewed shows solver reliability as the blocking issue for the recommended baseline. The accepted baseline and robustness cases have zero nonoptimal/time-limit/infeasible local solves, and no physical SOC violations.

The main concerns to report are:

- Profile dependence: min-up 8 is strong on the 6-day and synthetic checks but worse on the original 3-day profile.
- Cycling: the 6-day min-up 6 baseline has many exactly-minimum-length runs. This is not a feasibility failure, but it motivates the min-up 8 guardrail discussion.
- Over-tuning risk: the baseline was selected on the original 3-day operational profile, so the 6-day and synthetic validations should be described as robustness checks rather than new tuning targets.
- Terminal reserve/SOC: terminal reserve behaved mainly as a carried-SOC wall and increased final SOC/fuel. It is not competitive with minimum up-time as an anti-chatter mechanism.
- Shutdown cost: the shutdown diagnostic increased fuel and starts without producing a clearly cleaner case, so it should remain excluded from the baseline.
- Oracle interpretation: oracle realized local load must be clearly labeled non-implementable.
- Model logic: the generator symmetry-breaking constraint remains acceptable only while the two generators are identical; revisit it if generator data diverges.

## Evidence Used

Compact metrics are in `summary.csv` in this directory.

Primary evidence paths:

- `analysis/output/rolling_horizon/oracle_operational_tuning_screen/assessment.md`
- `runs/2026-04-27_171037_oracle_operational_screen_soft_h24_soc20_p1000_c1000/params.toml`
- `runs/2026-04-27_171037_oracle_operational_screen_soft_h24_soc20_p1000_c1000/dispatch_results.csv`
- `runs/2026-04-27_171037_oracle_operational_screen_soft_h24_soc20_p1000_c1000/plots/verification_overview.png`
- `runs/2026-04-27_171037_oracle_operational_screen_soft_h24_soc20_p1000_c1000/plots/verification_stress_window.png`
- `analysis/output/rolling_horizon/forecast_soft_soc_horizon_sweep/assessment.md`
- `analysis/output/rolling_horizon/forecast_soft_soc_horizon_sweep_mean_penalty/assessment.md`
- `analysis/output/rolling_horizon/forecast_soft_soc_mean_penalty_tuning_screen/deep_assessment.md`
- `analysis/output/rolling_horizon/forecast_soft_soc_high_startup_extension/assessment.md`
- `analysis/output/rolling_horizon/moving_average_forecast/forecast_method_comparison_soft_soc20.md`
- `analysis/output/rolling_horizon/moving_average_window_sensitivity/assessment.md`
- `analysis/output/rolling_horizon/min_up_baseline_contenders/summary.md`
- `analysis/output/rolling_horizon/min_up_confirmatory_baseline_sweep/summary.md`
- `analysis/output/rolling_horizon/min_up_long_horizon_guardrail/summary.md`
- `analysis/output/rolling_horizon/combined_baseline_assessment/assessment.md`
- `analysis/output/rolling_horizon/frozen_contenders/README.md`
- `analysis/output/rolling_horizon/shutdown_penalty_diagnostic/assessment.md`
- `analysis/output/rolling_horizon/terminal_reserve_soft_soc_weak_sweep/assessment.md`
- `analysis/output/rolling_horizon/operational_reserve_tuning/summary.md`
- `analysis/output/rolling_horizon/frozen_contenders_6day/assessment.md`
- `analysis/output/rolling_horizon/min_up_6day_sensitivity/assessment.md`
- `analysis/output/rolling_horizon/min_up_3day_sensitivity/assessment.md`
- `analysis/output/rolling_horizon/min_up_synthetic/assessment.md`

Key plot directories:

- `analysis/output/rolling_horizon/frozen_contenders/plots/`
- `analysis/output/rolling_horizon/frozen_contenders_6day/plots/`
- `analysis/output/rolling_horizon/min_up_6day_sensitivity/plots/`
- `analysis/output/rolling_horizon/min_up_3day_sensitivity/plots/`
- `analysis/output/rolling_horizon/min_up_synthetic/plots/`
- `analysis/output/rolling_horizon/moving_average_window_sensitivity/plots/`
- `analysis/output/rolling_horizon/shutdown_penalty_diagnostic/plots/`
- `analysis/output/rolling_horizon/terminal_reserve_soft_soc_weak_sweep/`
