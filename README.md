# Maritime Generator Dispatch Optimisation

Mixed-integer programming model for optimal fuel-economic dispatch of marine diesel generators, using piecewise-linear SFOC curves.

## Overview

The model minimises total fuel consumption across a fleet of generators over a given load profile. Each generator's fuel curve is represented as a piecewise-linear function via SOS2 convex-combination weights, with binary unit commitment.

## Structure

| File | Description |
|---|---|
| `model.jl` | JuMP optimisation model (variables, constraints, objective) |
| `main.jl` | Entry point — defines generator data, solves, writes CSV |
| `metrics.jl` | Computes per-run metrics from `dispatch_results.csv` and `params.toml` |
| `experiment.jl` | Parameter sweep loop — runs the model across a candidate grid and logs results |
| `types.jl` | Type definitions (reserved for future use) |
| `plot.py` | Python plotting script for dispatch results |
| `Project.toml` | Julia package dependencies |

## Usage

### Solve the dispatch problem

```bash
julia --project=. main.jl
```

This produces `dispatch_results.csv` with per-generator, per-timestep results.

### Run a parameter sweep

```bash
julia --project=. experiment.jl
```

Sweeps `E_init` (initial battery SOC) across `[20%, 30%, ..., 80%]`, runs the MILP for each candidate, and appends results to `experiments/history.csv`. Prints a ranked summary sorted by total objective (fuel + startup cost) at the end.

Each run is saved to a timestamped subdirectory under `experiments/` containing `dispatch_results.csv` and `params.toml`. The `params.toml` includes `[objective]` and `[constraints]` sections that record which model formulation was used, making runs independently reproducible and comparable across model variants.

### Plot results

```bash
python plot.py
```

Generates a multi-panel figure saved to `plots/dispatch_results.png`.

## Dependencies

**Julia** (≥ 1.9): `JuMP`, `HiGHS`

**Python** (≥ 3.9): `pandas`, `matplotlib`, `seaborn`

## License

TBD
