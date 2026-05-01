# Prompt For Next Thread: Rolling-Horizon Tuning Assessment

We are working in:

`C:\Users\bulve\OneDrive\master\model`

Use `AGENTS.md`. Preserve all existing runs and outputs. Do not delete old run directories or rewrite historical result packages.

## Task

Assess whether the rolling-horizon tuning process since Monday April 27, 2026 has been sufficient for thesis use.

Start from the oracle-screening run:

`C:\Users\bulve\OneDrive\master\model\runs\2026-04-27_171037_oracle_operational_screen_soft_h24_soc20_p1000_c1000`

Then look across the rolling-horizon sweep/result packages and recent run directories created from April 27 onward. The goal is not to run another broad sweep unless you find a clear gap. The goal is to audit the evidence and make a defensible thesis recommendation.

## Questions To Answer

1. Has the current tuning process been sufficient?
   - Check whether the sweep sequence covers the important controller choices: oracle vs non-oracle, horizon length, moving-average forecast, soft SOC penalty, startup cost, shutdown cost, terminal reserve/SOC, minimum up-time, and recent robustness checks.
   - Identify any obvious missing validation before freezing the thesis baseline.

2. What is the best baseline rolling-horizon controller?
   - Decide between the currently frozen baseline and any revised minimum-up-time guardrail candidate.
   - Be explicit about the objective: fuel-efficient baseline vs operational low-cycling baseline.

3. Should the oracle MILP be included in the thesis?
   - Assess whether oracle rolling-horizon MILP is useful as an upper-bound/diagnostic comparison.
   - Decide whether to leave it out of the main method/results to avoid confusing the controller story, or include it only as a benchmark/appendix.
   - Make clear that oracle realized local load is not implementable and should not be presented as the practical controller.

4. What are the important concerns?
   - Look for solver failures, time-limit/nonoptimal local solves, physical SOC violations, soft-SOC violations, excessive starts/chatter, over-tuned parameters, profile-dependence, and any questionable model logic.
   - Specifically review the minimum-up-time results: min-up 8 looks strong on the 6-day and synthetic cases, but weaker on the original 3-day operational profile.

## Key Evidence And Paths

### Oracle screening / early tuning

- Starting point requested by user:
  - `runs/2026-04-27_171037_oracle_operational_screen_soft_h24_soc20_p1000_c1000`
  - This is oracle realized-local-load, H24, soft SOC 20-80, penalty 1000, startup 1000.
  - It is diagnostic only because it uses future realized load inside the local horizon.
- Oracle/tuning package:
  - `analysis/output/rolling_horizon/oracle_operational_tuning_screen/`
- Related early packages:
  - `analysis/output/rolling_horizon/forecast_soft_soc_horizon_sweep/`
  - `analysis/output/rolling_horizon/forecast_soft_soc_horizon_sweep_mean_penalty/`
  - `analysis/output/rolling_horizon/forecast_soft_soc_mean_penalty_tuning_screen/`
  - `analysis/output/rolling_horizon/forecast_soft_soc_high_startup_extension/`
  - `analysis/output/rolling_horizon/moving_average_forecast/`

### Main baseline selection evidence

- Broad/combined baseline assessment:
  - `analysis/output/rolling_horizon/combined_baseline_assessment/assessment.md`
  - `analysis/output/rolling_horizon/combined_baseline_assessment/combined_summary.csv`
- Minimum-up baseline sweep:
  - `analysis/output/rolling_horizon/min_up_baseline_contenders/`
  - `analysis/output/rolling_horizon/min_up_confirmatory_baseline_sweep/`
  - `analysis/output/rolling_horizon/min_up_long_horizon_guardrail/`
- Frozen 3-day contenders:
  - `analysis/output/rolling_horizon/frozen_contenders/README.md`
  - `analysis/output/rolling_horizon/frozen_contenders/summary.csv`
  - Main frozen balanced baseline:
    - `config/rolling_horizon_thesis_balanced.toml`
    - H16, MA4, startup 500 g/start, soft SOC penalty 10000 g/kWh, min_up_time_steps=6, shutdown_cost=0, no terminal reserve.
  - Conservative comparison:
    - `config/rolling_horizon_thesis_conservative.toml`
    - H24, MA4, startup 500 g/start, soft SOC penalty 20000 g/kWh, min_up_time_steps=6, shutdown_cost=0, no terminal reserve.

### Shutdown/terminal reserve evidence

- Shutdown penalty diagnostic:
  - `analysis/output/rolling_horizon/shutdown_penalty_diagnostic/`
  - User’s current interpretation: shutdown cost “did not do shit” and adds model complexity.
- Terminal reserve / terminal SOC evidence:
  - `analysis/output/rolling_horizon/terminal_reserve_soft_soc_weak_sweep/`
  - `analysis/output/rolling_horizon/operational_reserve_tuning/`
  - User’s current interpretation: terminal SOC/reserve behaved like an invisible lower wall that the controller bounced on.

### 6-day robustness validation

- Derived 6-day load profile:
  - `data/operational_profiles/operational_load_profile_6day_15min_avg.csv`
  - Direct copy of `analysis/operational_load_cases/baseline_load_case/prepared/load_profile_15min_avg.csv`
  - 534 steps, 2026-01-26 01:00 to 2026-01-31 14:15.
- 6-day frozen contender package:
  - `analysis/output/rolling_horizon/frozen_contenders_6day/assessment.md`
  - `analysis/output/rolling_horizon/frozen_contenders_6day/summary.csv`
- 6-day frozen run dirs:
  - Balanced: `runs/2026-04-30_100448_rolling_horizon_thesis_balanced_6day_h16_ma4_c500_p10k_minup6`
  - Conservative: `runs/2026-04-30_105222_rolling_horizon_thesis_conservative_6day_h24_ma4_c500_p20k_minup6`
- 6-day result headline:
  - Balanced min-up 6: 1630.05 kg, +2.38% vs full horizon, 16 starts, min SOC 20.37%, final SOC 33.71%, zero nonoptimal local solves.
  - Conservative min-up 6: 1657.80 kg, +4.12% vs full horizon, 16 starts, min SOC 20.45%, final SOC 48.90%, zero nonoptimal local solves.
  - This supports balanced over conservative, but exposed many exactly-minimum-length runs.

### Minimum-up-time follow-up

- 6-day minimum-up sensitivity:
  - `analysis/output/rolling_horizon/min_up_6day_sensitivity/assessment.md`
  - `analysis/output/rolling_horizon/min_up_6day_sensitivity/summary.csv`
  - Results:
    - min-up 6: +2.38%, 16 starts, min SOC 20.37%, final SOC 33.71%.
    - min-up 8: +2.29%, 13 starts, min SOC 20.02%, final SOC 34.54%.
    - min-up 12: +3.90%, 10 starts, min SOC 20.24%, final SOC 46.72%.
    - min-up 16: +8.66%, 9 starts, min SOC 16.91%, max SOC 86.92%, reject as overconstrained.
  - Initial interpretation: min-up 8 is the best practical guardrail; min-up 12 is a plausible low-cycling comparison if fuel is less important.
- 3-day minimum-up sensitivity:
  - `analysis/output/rolling_horizon/min_up_3day_sensitivity/assessment.md`
  - `analysis/output/rolling_horizon/min_up_3day_sensitivity/summary.csv`
  - Results:
    - min-up 6: +2.54%, 5 starts.
    - min-up 8: +5.25%, 6 starts.
    - min-up 12: +9.19%, 5 starts.
  - Important caveat: min-up 8 and 12 are weaker on the original 3-day March profile.
- Synthetic minimum-up comparison:
  - `analysis/output/rolling_horizon/min_up_synthetic/assessment.md`
  - `analysis/output/rolling_horizon/min_up_synthetic/summary.csv`
  - Results:
    - min-up 6: +6.44%, 6 starts, min SOC 38.55%, final SOC 45.88%.
    - min-up 8: +1.29%, 4 starts, min SOC 20.00%, final SOC 23.09%.
  - Important: min-up 8 is clearly better on synthetic and matches full-horizon start count.

## Likely Current Interpretation To Challenge Or Confirm

The evidence currently suggests:

- The original frozen balanced controller (`H16, MA4, startup 500, soft SOC 10000, min_up=6`) remains the best fuel-efficient operational baseline on the original 3-day profile.
- The 6-day and synthetic checks make `min_up=8` look like a stronger practical guardrail candidate:
  - It reduces starts and improves fuel on 6-day.
  - It strongly improves synthetic.
  - But it is worse on the original 3-day profile.
- `min_up=12` is not weak if framed as an operator-style low-cycling policy, but it is not the fuel-efficient baseline.
- `min_up=16` should not be a baseline due to fuel cost and preferred SOC-band violations.
- Shutdown cost and terminal SOC/reserve likely should not be kept as baseline mechanisms.
- Oracle rolling horizon likely belongs, at most, as a diagnostic/appendix or upper-bound comparison, not as the practical controller.

Do not accept this interpretation blindly. Verify it from the outputs and plots.

## Suggested Work Plan

1. Read the summaries and assessment files listed above.
2. Inspect the referenced oracle run’s `params.toml`, `dispatch_results.csv`, and plots.
3. Build a compact comparison table across:
   - oracle diagnostic result,
   - frozen 3-day balanced/conservative,
   - 6-day balanced/conservative,
   - min-up 8/12 checks on 6-day, 3-day, and synthetic.
4. Decide whether the thesis should:
   - keep min-up 6 as the main baseline and mention min-up 8 as a robustness/guardrail candidate,
   - switch the main practical baseline to min-up 8,
   - or present both as fuel-efficient vs operational guardrail variants.
5. Decide whether oracle MILP should be included:
   - main text as diagnostic benchmark,
   - appendix only,
   - or omitted to avoid confusing the implementable-controller narrative.
6. Write a clear assessment in a new file, for example:
   - `analysis/output/rolling_horizon/final_tuning_assessment/assessment.md`
   - `analysis/output/rolling_horizon/final_tuning_assessment/summary.csv`

## Deliverable

Produce a concise but defensible final assessment with:

- recommended main baseline controller,
- recommended conservative/operator comparison controller, if any,
- whether min-up 8 should replace min-up 6 or remain a robustness note,
- whether oracle MILP should be included and where,
- remaining concerns/limitations,
- exact paths to the evidence and plots used.

If you make or confirm an important thesis/modeling decision, ask whether it should be added to:

`analysis/handoffs/thesis_decision_notes.md`
