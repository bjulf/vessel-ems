# No-Terminal Sensitivity Rerun Prompt

Use this prompt in a fresh Codex instance working in this repository.

---

You are working in the modeling repo at:
`C:\Users\bulve\OneDrive\master\model`

Read `AGENTS.md` first and follow it.

## Context

The baseline MILP has just been cleaned up:

- The no-terminal baseline entry point is `main_baseline_no_terminal_soc.jl`.
- The no-terminal baseline config is `config/baseline_model_no_terminal_soc.toml`.
- That config now includes:
  - `entry_point = "main_baseline_no_terminal_soc.jl"`
- The shared sensitivity runner helper in `analysis/sensitivity_common.py` now respects `run.entry_point` from the config instead of always calling `main.jl`.
- A dedicated suite runner exists:
  - `analysis/run_sensitivity_no_terminal_soc.py`
- The no-terminal sensitivity package should write to:
  - `analysis/output/sensitivity_no_terminal_soc/`
- This new package intentionally excludes terminal-reserve sensitivity.
- The old terminal-constrained sensitivity package remains in:
  - `analysis/output/sensitivity/`

## Main Goal

Run the full no-terminal-SOC sensitivity package, generate plots and summaries in the new no-terminal sensitivity directory, assess the results against the old sensitivity package, and evaluate whether the current no-terminal baseline parameter choices still look defensible.

## Required Scope

Run the no-terminal sensitivity package for these sweeps:

1. Startup cost
2. Minimum SOC
3. Initial SOC
4. Battery efficiency

Do not include terminal reserve in the new package.

## Expected Runner

Use:

```powershell
python analysis/run_sensitivity_no_terminal_soc.py
```

If needed, inspect and improve the helper scripts, but keep the overall workflow centered on the no-terminal package and its separate output tree.

## Output Location Rules

Keep all new package-level outputs under:

`analysis/output/sensitivity_no_terminal_soc/`

Use clear structure. For example:

- `analysis/output/sensitivity_no_terminal_soc/startup_cost/`
- `analysis/output/sensitivity_no_terminal_soc/soc_min/`
- `analysis/output/sensitivity_no_terminal_soc/initial_soc/`
- `analysis/output/sensitivity_no_terminal_soc/battery_efficiency/`

If you generate package-level comparison outputs, keep them under the same no-terminal root, for example:

- `analysis/output/sensitivity_no_terminal_soc/comparison/`

Do not overwrite or repurpose the old:

`analysis/output/sensitivity/`

## Plotting Requirement

Generate sweep plots in the new no-terminal sensitivity directory.

At minimum, preserve or improve the existing per-sweep outputs:

- `summary.csv`
- `summary.txt`
- overview plots already produced by the sweep scripts

Also add package-level comparison plots if they materially help compare:

- the new no-terminal package,
- the old terminal-constrained package,
- and the current baseline parameter choices.

Prefer high-signal plots over many plots.

## Runtime / Summary Requirement

This is important:

For each sweep and each run, store both:

- solver time from run metadata (`params.toml` / `solver.solve_time_s`)
- full wall-clock runtime of the simulation case as launched by the sensitivity script

Record these in a Markdown summary file, not only in CSV.

Minimum requirement:

- a `summary.md` in each new no-terminal sweep folder

Each `summary.md` should include, per case:

- varied parameter value
- config path
- run directory
- objective value if available
- total fuel
- starts/stops where relevant
- min SOC
- terminal SOC
- battery throughput where relevant
- solver time
- full wall-clock runtime
- any obvious warnings or anomalies

Also create a package-level summary:

- `analysis/output/sensitivity_no_terminal_soc/summary.md`

This package summary should synthesize the full no-terminal package and compare it against the old sensitivity package.

## Comparison Task

Compare the new no-terminal sensitivity package against the old sensitivity package in:

`analysis/output/sensitivity/`

Focus especially on:

1. Whether removing the terminal SOC constraint materially changes the sensitivity story
2. Whether the qualitative conclusions from the old package still hold
3. Whether the relative ranking or significance of the tested parameters changes
4. Whether the new no-terminal baseline parameter choices still look reasonable

## Baseline Parameter Assessment

Assess the current no-terminal baseline choices, especially:

- startup cost = `700 g/start`
- minimum SOC = `20%`
- initial SOC = `70%`
- battery efficiency = `0.95`
- no terminal SOC constraint

I want a clear judgment, not just a description.

For each baseline parameter, assess whether it appears:

- still defensible,
- weakly justified,
- overly influential,
- or in need of revision.

If a parameter looks poorly chosen under the no-terminal baseline, say so directly and explain why.

## Additional Sensitivity Assessment

Assess whether any other parameters should be put through sensitivity analysis.

Do not automatically run extra sweeps unless there is a strong reason.

First, provide a short ranked recommendation list with rationale. Consider things like:

- baseline relevance,
- likely impact on dispatch,
- thesis/report value,
- and whether the parameter is structural or merely cosmetic.

If you conclude that no additional sweep is worth adding, say that explicitly and justify it.

## Validation Expectations

At minimum:

- confirm the no-terminal suite runs successfully
- confirm outputs land in `analysis/output/sensitivity_no_terminal_soc/`
- confirm the old sensitivity tree is left untouched
- sanity-check the generated summaries and plots

If a full rerun is too time-consuming to finish in one session, do as much as possible, leave the repo in a runnable state, and write a precise continuation note in:

`analysis/handoffs/`

## Deliverables

By the end of the task, I want:

1. The no-terminal sensitivity package run
2. New outputs under `analysis/output/sensitivity_no_terminal_soc/`
3. `summary.md` files with solver time and wall-clock runtime per case
4. A package-level `summary.md`
5. A comparison against the old sensitivity package
6. A judgment on whether the current no-terminal baseline parameters are appropriate
7. A recommendation on whether any additional parameter sensitivities should be added

## Relevant Files To Inspect First

- `AGENTS.md`
- `analysis/run_sensitivity_no_terminal_soc.py`
- `analysis/sensitivity_common.py`
- `analysis/startup_cost_sensitivity.py`
- `analysis/soc_min_sensitivity.py`
- `analysis/initial_soc_sensitivity.py`
- `analysis/battery_efficiency_sensitivity.py`
- `config/baseline_model_no_terminal_soc.toml`
- `analysis/output/sensitivity/`

## Important Constraints

- Do not touch the separate thesis/report repo.
- This task is only for the modeling repo.
- Preserve historical outputs and prior sensitivity results.
- Keep the no-terminal package clearly separated from the old package.
- Use the new no-terminal baseline family, not the terminal-constrained one.

When you finish, summarize:

- what was run,
- where outputs were written,
- what changed relative to the old sensitivity package,
- whether the current no-terminal baseline looks well chosen,
- and whether more sensitivity work is warranted.
