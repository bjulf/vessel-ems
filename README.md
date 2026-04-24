# Maritime Generator Dispatch Optimisation

Mixed-integer programming model for optimal fuel-economic dispatch of marine diesel generators, using piecewise-linear SFOC curves.

## Overview

The model minimises total fuel consumption across a fleet of generators over a given load profile. Each generator's fuel curve is represented as a piecewise-linear function via SOS2 convex-combination weights, with binary unit commitment.

## Structure

| File | Description |
|---|---|
| `model.jl` | JuMP optimisation model (variables, constraints, objective) |
| `main.jl` | Entry point — reads the active load profile, solves, writes CSV |
| `model_baseline_no_terminal_soc.jl` | Clean baseline variant with the terminal SOC requirement removed |
| `main_baseline_no_terminal_soc.jl` | Entry point for the clean no-terminal-SOC baseline variant |
| `experimental_models/` | Temporary or exploratory model/entry-point variants kept out of the main top-level layout |
| `rule_based.jl` | Separate rule-based supervisory EMS entry point for baseline comparison runs |
| `config/baseline_model.toml` | Baseline run parameters and default model input selection |
| `config/baseline_model_no_terminal_soc.toml` | Clean no-terminal-SOC baseline-variant parameters |
| `types.jl` | Type definitions (reserved for future use) |
| `data/generate_synthetic_profile.py` | Generates synthetic 24 h / 15 min load scenarios and plots |
| `plot.py` | Python plotting script for dispatch results |
| `Project.toml` | Julia package dependencies |

## Usage

### Generate a synthetic load profile

```bash
python data/generate_synthetic_profile.py
```

This writes:

- `data/load_profile.csv` as the active profile for `main.jl`
- `data/synthetic_profiles/validation_profile.csv`
- `data/synthetic_profiles/plots/validation_profile.png`
- `data/synthetic_profiles/plots/validation_profile_bars.png`

### Solve the dispatch problem

```bash
julia --project=. main.jl
```

By default this loads `config/baseline_model.toml`.
You can also provide a different parameter file:

```bash
julia --project=. main.jl config/baseline_model.toml
```

This produces a run directory in `runs/` with `dispatch_results.csv` and `params.toml`.

### Run the rule-based EMS baseline

```bash
julia --project=. rule_based.jl config/baseline_model.toml
```

This reuses the same baseline configuration and load profile, writes a separate run directory in `runs/`, and updates `.current_run` to the new rule-based run.

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
