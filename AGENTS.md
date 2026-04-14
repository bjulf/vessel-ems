# AGENTS.md

Guidance for coding agents working in this repository.

## Repo purpose

This repo models maritime generator dispatch as a mixed-integer optimization problem in Julia, with Python used for data preprocessing, plotting, and Quarto-based reporting.

The main workflow is:

1. Prepare the load profile from raw data in `data/`
2. Solve the dispatch model in Julia
3. Inspect outputs in `runs/`
4. Generate plots or a report from a selected run

## Source map

- `main.jl`: main entry point, run metadata, solver execution, and result export
- `model.jl`: JuMP model formulation and optimization variables/constraints/objective
- `types.jl`: currently unused type definitions and notes
- `data/preprocess.py`: builds `data/load_profile.csv` for the default MILP input and `data/operational_profiles/operational_load_profile_1min.csv` for comparison and timestep-sensitivity work
- `data/operational_profiles/`: reconstructed operational comparison profiles derived from telemetry
- `plot.py`: plotting utilities for a specific run directory
- `report.qmd`: Quarto report driven by `.current_run` or `RUN_DIR`
- `analysis/`: working analysis scripts, notes, and exploratory outputs
- `analysis/output/`: working top-level outputs and intermediate figure exports
- `analysis/sfoc_cases/`: preserved telemetry-SFOC case outputs and case index
- `analysis/sfoc_datasets/`: preserved fetched telemetry windows used in SFOC work
- `analysis/thesis_figures/`: curated thesis-ready or thesis-candidate figures copied from working outputs
- `analysis/handoffs/`: handoff notes for continuing figure/report work in another AI thread
- `data/`: raw and derived input data
- `runs/`: generated run directories with `params.toml`, `dispatch_results.csv`, and plots
- `results/`: archived scenario/report outputs; treat as user-owned historical artifacts unless asked otherwise

## Working assumptions

- The Julia model is the primary source of truth for optimization behavior.
- The Python layer is support tooling for data preparation, inspection, and reporting.
- The repo is experiment-oriented. Preserve run history and avoid deleting generated artifacts unless explicitly asked.
- The worktree may contain user-generated scenario outputs that are intentionally untracked.

## Critical invariants

- Keep `data/preprocess.py:RESAMPLE_MINUTES` aligned with `main.jl:dt_minutes`. These must represent the same timestep length.
- `main.jl` expects `data/load_profile.csv` with columns `timestep,load_kw,datetime`.
- Treat `data/load_profile.csv` as the default model input tied to `main.jl:dt_minutes`, not as the preserved high-resolution operational comparison profile.
- Treat `data/operational_profiles/operational_load_profile_1min.csv` as the preserved 1-minute reconstructed operational profile for final comparison and timestep sensitivity. Do not repurpose it as the default MILP input without an explicit model-timestep change.
- `main.jl` writes the active run path to `.current_run`; `report.qmd` relies on that when `RUN_DIR` is not set.
- `model.jl` contains a symmetry-breaking power-ordering constraint for generators. If generators stop being identical, revisit that logic before keeping the ordering constraint.
- Battery energy dynamics, objective scaling, and reported fuel totals all depend on `battery.dt`; timestep edits need a full end-to-end consistency check.

## Editing guidance

- Prefer small, targeted changes. This repo is compact and tightly coupled.
- When changing optimization behavior, inspect both `model.jl` and `main.jl`; parameters are defined in `main.jl`, not a separate config file.
- Do not hand-edit files inside `runs/` unless the task is explicitly about repairing generated artifacts.
- Do not remove or rewrite files in `results/` just because newer run outputs exist.
- Treat `analysis/sfoc_cases/` and `analysis/sfoc_datasets/` as preserved analysis records. Do not delete or overwrite them casually.
- Treat `analysis/output/` as a working area, not the final curated location for thesis figures.
- When a plot becomes a real thesis candidate, copy it into `analysis/thesis_figures/` rather than relying on `analysis/output/` alone.
- Several files contain mojibake or non-ASCII comment artifacts. Do not perform broad encoding cleanups unless the task specifically requires it.
- Keep report/plot changes aligned with the actual columns exported by `write_results_csv(...)`.

## Plot formatting

When generating plots that are likely to be reused in the thesis or reports:

- Optimize for readability after export, not only for interactive viewing
- Use larger-than-default text for titles, axis labels, tick labels, and in-plot annotations
- Prefer direct labels inside the figure when they are clearer than a separate legend
- Avoid redundant legends when the same categories are already clearly labeled in the plot
- Keep the layout visually simple and prioritize legibility over decorative detail

## Analysis and figure workflow

- Keep exploratory scripts and notes in `analysis/`.
- Keep one-off or intermediate outputs in `analysis/output/`.
- Keep preserved telemetry case outputs in `analysis/sfoc_cases/`.
- Keep thesis-candidate figures in `analysis/thesis_figures/methods/` and `analysis/thesis_figures/results/`.
- Add or update a short note in `analysis/thesis_figures/README.md` when a new figure becomes a serious thesis candidate.
- Keep continuation notes in `analysis/handoffs/` when a thread produces reusable guidance for later report or plotting work.
- For operational telemetry work, separate:
  - general operational data / load reconstruction validation,
  - and telemetry-based SFOC assessment.
- Do not force internal diagnostic plots into the thesis when a clearer explanatory figure can be generated from the same data.

## Validation workflow

Use the smallest relevant validation for the change:

- Data pipeline changes:
  - Run `python data/preprocess.py`
  - Confirm `data/load_profile.csv` shape and datetime range look reasonable
  - If the change affects operational comparison inputs, also confirm `data/operational_profiles/operational_load_profile_1min.csv` shape and datetime range
- Model or parameter changes:
  - Run `julia --project=. main.jl`
  - Check solver status and inspect the newly created directory in `runs/`
  - Verify `params.toml` and `dispatch_results.csv` reflect the intended change
- Plot/report changes:
  - Run `python plot.py <run_dir>`
  - Run `quarto render report.qmd` or render with `RUN_DIR` set to a specific run

## Environment notes

- Julia dependencies are declared in `Project.toml`; `Manifest.toml` is gitignored.
- Quarto is configured in `_quarto.yml` to use `.venv/Scripts/python.exe`.
- Python dependencies are not pinned in a dedicated requirements file; infer them from the scripts and existing environment.

## Collaboration defaults

- Preserve the user's existing run outputs and scenario comparison files.
- Surface model-logic tradeoffs clearly when changing constraints or objective terms.
- If a requested change affects both preprocessing cadence and optimization timestep semantics, treat it as a cross-file change and verify both sides.
