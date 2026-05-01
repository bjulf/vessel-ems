# Prompt For Thesis Report Thread: Rolling-Horizon Tuning Methods And Baseline Choice

You are working in the thesis report repository, but the rolling-horizon tuning evidence lives in the model repository:

`C:\Users\bulve\OneDrive\master\model`

Use the model repo evidence to write or revise the methods-chapter description of rolling-horizon MILP tuning. Do not invent new numerical results. If you need exact values, read the files listed below.

## Goal

Write a sufficient thesis-report description of the rolling-horizon MILP tuning process and assess whether the current tuning results are good enough for the thesis.

The report text should explain the tuning process clearly without turning the methods chapter into a long sweep log. The main narrative should distinguish:

- what was tuned,
- why each tuning direction was explored,
- what was rejected,
- what controller settings were retained,
- what results should be shown in the report,
- and what remaining limitations should be acknowledged.

## Core Questions To Answer

1. Are we happy with the rolling-horizon tuning results?
   - Assess whether the current evidence is sufficient for thesis use.
   - Identify whether more tuning or validation is needed before report freeze.
   - Be explicit about the difference between fuel-efficient tuning and operational low-cycling tuning.

2. Which rolling-horizon baseline should be used for further report sensitivity analysis?
   - Compare:
     - `min_up_time_steps = 6`: fuel-efficient baseline.
     - `min_up_time_steps = 8`: more conservative operational guardrail candidate.
   - Decide whether sensitivity analysis in the report should use min-up 6 or min-up 8 as the baseline.
   - If the answer depends on the report objective, state that clearly and recommend the framing.

3. Should the synthetic rolling-horizon MILP result be shown in the report?
   - The tuning was mainly done on operational data.
   - The synthetic case is useful because min-up 8 performs strongly there, but it may confuse the narrative if it looks like tuning evidence after the fact.
   - Decide whether to:
     - include synthetic rolling-horizon MILP in the main results,
     - include it only as validation/appendix,
     - or omit it from the tuning narrative.
   - Make clear whether the synthetic case is a design/tuning case, a robustness check, or a demonstration case.

4. How should the tuning process be presented in the report?
   - Decide whether to show current tuning results explicitly in the report, or describe tuning more generally before the sensitivity analysis.
   - Avoid overloading the report with too many parameter sweeps unless they support a clear modeling decision.
   - Recommend a compact table or figure set if useful.
   - Decide which results belong in methods, results, appendix, or not at all.

5. Should oracle rolling-horizon MILP be included?
   - Oracle uses realized future local load and is not implementable.
   - Assess whether it belongs in an appendix or diagnostic paragraph only.
   - Do not present oracle rolling-horizon MILP as the practical controller.

## Current Interpretation To Challenge Or Confirm

The latest model-repo assessment says the tuning is sufficient for thesis use, but the baseline recommendation is objective-dependent:

- Fuel-efficient practical baseline:
  - H16, MA4 forecast, startup cost 500 g/start, shutdown cost 0, soft SOC penalty 10000 g/kWh, `min_up_time_steps = 6`, no terminal reserve.
  - Good fuel closeness on the 3-day operational profile and 6-day validation.
- Operational guardrail practical baseline:
  - Same settings, but `min_up_time_steps = 8`.
  - Higher fuel cost on the 3-day operational case, but cleaner commitment blocks.
  - Better on the 6-day operational validation and much better on the synthetic validation.

Important: do not blindly accept this. Read the evidence and decide what is best for the thesis report narrative.

## Key Evidence

Start with:

- `C:\Users\bulve\OneDrive\master\model\analysis\output\rolling_horizon\final_tuning_assessment\assessment.md`
- `C:\Users\bulve\OneDrive\master\model\analysis\output\rolling_horizon\final_tuning_assessment\summary.csv`

Then use these supporting packages as needed.

### Baseline selection and tuning

- `C:\Users\bulve\OneDrive\master\model\analysis\output\rolling_horizon\combined_baseline_assessment\assessment.md`
- `C:\Users\bulve\OneDrive\master\model\analysis\output\rolling_horizon\combined_baseline_assessment\combined_summary.csv`
- `C:\Users\bulve\OneDrive\master\model\analysis\output\rolling_horizon\frozen_contenders\README.md`
- `C:\Users\bulve\OneDrive\master\model\analysis\output\rolling_horizon\frozen_contenders\summary.csv`
- `C:\Users\bulve\OneDrive\master\model\analysis\output\rolling_horizon\moving_average_window_sensitivity\assessment.md`
- `C:\Users\bulve\OneDrive\master\model\analysis\output\rolling_horizon\forecast_soft_soc_mean_penalty_tuning_screen\deep_assessment.md`

### Minimum-up evidence

- `C:\Users\bulve\OneDrive\master\model\analysis\output\rolling_horizon\min_up_3day_sensitivity\assessment.md`
- `C:\Users\bulve\OneDrive\master\model\analysis\output\rolling_horizon\min_up_3day_sensitivity\summary.csv`
- `C:\Users\bulve\OneDrive\master\model\analysis\output\rolling_horizon\min_up_6day_sensitivity\assessment.md`
- `C:\Users\bulve\OneDrive\master\model\analysis\output\rolling_horizon\min_up_6day_sensitivity\summary.csv`
- `C:\Users\bulve\OneDrive\master\model\analysis\output\rolling_horizon\min_up_synthetic\assessment.md`
- `C:\Users\bulve\OneDrive\master\model\analysis\output\rolling_horizon\min_up_synthetic\summary.csv`

### Rejected or diagnostic mechanisms

- `C:\Users\bulve\OneDrive\master\model\analysis\output\rolling_horizon\shutdown_penalty_diagnostic\assessment.md`
- `C:\Users\bulve\OneDrive\master\model\analysis\output\rolling_horizon\terminal_reserve_soft_soc_weak_sweep\assessment.md`
- `C:\Users\bulve\OneDrive\master\model\analysis\output\rolling_horizon\operational_reserve_tuning\summary.md`
- `C:\Users\bulve\OneDrive\master\model\analysis\output\rolling_horizon\oracle_operational_tuning_screen\assessment.md`

### Important run directories

- 3-day min-up 6 baseline:
  - `C:\Users\bulve\OneDrive\master\model\runs\2026-04-29_170441_rolling_horizon_thesis_balanced_h16_ma4_c500_p10k_minup6`
- 3-day min-up 8 candidate:
  - `C:\Users\bulve\OneDrive\master\model\runs\2026-04-30_133906_rolling_horizon_balanced_3day_h16_ma4_c500_p10k_minup8`
- 6-day min-up 6:
  - `C:\Users\bulve\OneDrive\master\model\runs\2026-04-30_100448_rolling_horizon_thesis_balanced_6day_h16_ma4_c500_p10k_minup6`
- 6-day min-up 8:
  - `C:\Users\bulve\OneDrive\master\model\runs\2026-04-30_115840_rolling_horizon_balanced_6day_h16_ma4_c500_p10k_minup8`
- Synthetic min-up 6:
  - `C:\Users\bulve\OneDrive\master\model\runs\2026-04-30_135109_rolling_horizon_balanced_synthetic_h16_ma4_c500_p10k_minup6`
- Synthetic min-up 8:
  - `C:\Users\bulve\OneDrive\master\model\runs\2026-04-30_140817_rolling_horizon_balanced_synthetic_h16_ma4_c500_p10k_minup8`

## Numerical Anchors

Use exact values from the CSV files when writing final report text, but these anchors summarize the current evidence:

- 3-day min-up 6:
  - +2.54% fuel versus full horizon, 5 starts, min SOC 20.09%, final SOC 27.44%.
  - Run lengths: `18;13;14;6;19`.
- 3-day min-up 8:
  - +5.25% fuel versus full horizon, 6 starts, min SOC 22.11%, final SOC 35.62%.
  - Run lengths: `18;15;10;8;8;15`.
  - Operationally cleaner persistence, despite higher fuel and one more start.
- 6-day min-up 6:
  - +2.38%, 16 starts, many exactly-minimum-length 6-step runs.
- 6-day min-up 8:
  - +2.29%, 13 starts, no physical SOC violation.
- Synthetic min-up 6:
  - +6.44%, 6 starts.
- Synthetic min-up 8:
  - +1.29%, 4 starts, matching full-horizon start count.
- H12/startup 500/P10k/min-up 6:
  - +4.40%, 6 starts. Viable, but not obviously better than H16/min-up 8 for the operational guardrail story.
- H16/startup 1000/P10k/min-up 6:
  - +6.22%, 5 starts. Tested, but higher startup cost mainly raises carried SOC/fuel rather than producing a clearly superior baseline.

## Suggested Report Framing

Consider this structure, but revise it if the report repo already has a better chapter organization:

1. Methods chapter:
   - Define rolling-horizon MILP control.
   - Explain implementable moving-average forecast.
   - Explain local soft SOC band.
   - Explain minimum up-time as the retained anti-chatter/commitment-regularity mechanism.
   - State that shutdown cost and terminal reserve were tested but not retained.
   - State that oracle local-load MILP is diagnostic only.

2. Tuning subsection:
   - Give a compact description of the tuning sequence, not a full dump of all sweeps.
   - Include one concise table of retained/rejected tuning mechanisms:
     - horizon and MA window,
     - soft SOC penalty,
     - startup cost,
     - shutdown penalty,
     - terminal reserve,
     - minimum up-time.
   - Include a second compact table comparing min-up 6 and min-up 8 across 3-day, 6-day, and synthetic cases if this helps justify the baseline.

3. Results or appendix:
   - Main report should focus on the chosen practical baseline and the sensitivity analysis.
   - Put detailed tuning sweeps in appendix if needed.
   - Use synthetic rolling-horizon MILP as validation/robustness only if it supports the narrative without implying the controller was tuned on synthetic data.

## Deliverable

Produce a report-thread assessment with:

- recommended baseline for report sensitivity analysis,
- whether min-up 8 should replace min-up 6 for the report baseline,
- whether synthetic rolling-horizon MILP should be shown and where,
- whether oracle rolling-horizon MILP should be shown and where,
- recommended tuning text for the methods chapter,
- recommended report table/figure list,
- and any remaining limitations to disclose.

If you update report files, keep edits focused and cite the model-repo evidence paths in comments or notes where appropriate.
