# Maritime Generator Dispatch Optimisation

Mixed-integer programming model for optimal fuel-economic dispatch of marine diesel generators, using piecewise-linear SFOC curves.

## Overview

The model minimises total fuel consumption across a fleet of generators over a given load profile. Each generator's fuel curve is represented as a piecewise-linear function via SOS2 convex-combination weights, with binary unit commitment.

## Structure

| File | Description |
|---|---|
| `model.jl` | JuMP optimisation model (variables, constraints, objective) |
| `main.jl` | Entry point — defines generator data, solves, writes CSV |
| `types.jl` | Type definitions (reserved for future use) |
| `plot.py` | Python plotting script for dispatch results |
| `Project.toml` | Julia package dependencies |

## Usage

### Solve the dispatch problem

```bash
julia --project=. main.jl
```

This produces `dispatch_results.csv` with per-generator, per-timestep results.

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
