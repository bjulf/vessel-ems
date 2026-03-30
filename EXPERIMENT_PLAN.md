# Minimal Experiment Loop for Vessel EMS MILP

## Context

The MILP in `main.jl`/`model.jl` is currently run manually. The goal is a minimal,
reproducible experiment loop that:
- Sweeps `E_init` (initial battery SOC) as the first parameter
- Records every run in a persistent `experiments/history.csv`
- Captures enough model metadata that runs with *different formulations* are
  distinguishable in the history — because the model itself will change over the thesis

Two-layer memory design:
- **history.csv** — slim summary index with key decision columns per run
- **params.toml** — authoritative full config per run (extended with `[objective]`
  and `[constraints]` sections)

---

## Files to Create / Modify

| File | Action | Purpose |
|---|---|---|
| `main.jl` | Modify | Add `default_config()`, parameterise `main(config)`, extend params.toml, return `run_dir` |
| `metrics.jl` | Create | Read CSV + params.toml → compute per-run metrics |
| `experiment.jl` | Create | Candidate grid, loop, history.csv logging, ranked summary |
| `model.jl` | No change | Already accepts `battery.E_init` correctly |

No new package dependencies. Uses Julia stdlib (`Statistics`, `TOML`, `Printf`, `Dates`)
plus `JuMP`/`HiGHS` already in Project.toml.

---

## history.csv Schema

```
run_id, timestamp, model_variant, E_init_soc, E_init_kwh,
solver_status, objective_g, fuel_cost_g, startup_cost_g,
battery_throughput_kwh, mean_soc_pct, final_soc_pct, min_soc_pct,
solve_time_s, run_dir
```

- Append-only — never overwrite rows
- `run_id` = `max(existing) + 1`, starting at 1
- Failed/infeasible runs recorded with `solver_status = INFEASIBLE` and `NaN` metrics
- `model_variant` = human label e.g. `"baseline"`, `"soc_penalty"`, `"throughput"`

---

## params.toml Extensions (new sections per run)

```toml
[objective]
terms = ["fuel", "startup"]   # list grows as variants are added

[constraints]
terminal_soc = "gte_init"     # "gte_init" | "eq_init" | "free"
```

These sections are written by `main()` from the config — they describe what model
was actually used, making any run independently reproducible.

---

## Config Structure in main.jl

```julia
function default_config()
    dt = 15 / 60.0
    gensets = [ ... ]   # unchanged from current hardcoded values
    battery = (
        E_max=940.0, SOC_min=0.2, SOC_max=0.9,
        P_ch_max=753.25, P_dis_max=943.2,
        eta_ch=0.95, eta_dis=0.95,
        E_init=0.5*940.0, dt=dt,
    )
    return (
        gensets         = gensets,
        battery         = battery,
        label           = "",
        description     = "",
        show_solver_log = true,
        model_variant   = "baseline",
        objective       = (terms = ["fuel", "startup"],),
        constraints     = (terminal_soc = "gte_init",),
    )
end
```

Callers override only the fields they need:

```julia
cfg = default_config()
cfg = merge(cfg, (
    battery = merge(cfg.battery, (E_init = 0.3 * 940.0,)),
    label   = "einit_30",
    show_solver_log = false,
))
main(cfg)
```

---

## Metrics (metrics.jl)

Reads `dispatch_results.csv` row-by-row (no CSV.jl dependency) and `params.toml`.

Returns per-run NamedTuple:
```
solver_status, objective_g,
fuel_cost_g       = sum(fuel_gph) * dt_h              # grams
startup_cost_g    = total_startups * startup_cost      # grams
battery_throughput_kwh = sum(P_ch + P_dis) * dt_h     # kWh cycled
mean_soc_pct, final_soc_pct, min_soc_pct,
solve_time_s
```

Validity check (`is_valid_run`):
- `solver_status == "OPTIMAL"`
- `objective_g` finite and positive
- `fuel_cost_g > 0`
- `min_soc_pct >= 19.0`  (tolerance on `SOC_min = 20%`)

Spot-check: `fuel_cost_g + startup_cost_g ≈ objective_g` for baseline runs.

---

## Execution Loop (experiment.jl)

```
include("main.jl"), include("metrics.jl")

E_init_soc_values = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
model_variant     = "baseline"

for each soc in E_init_soc_values:
    build config (override E_init, label, show_solver_log=false)
    run_dir = main(config)         # returns path or nothing
    m       = compute_metrics(run_dir)
    append row to experiments/history.csv
    println progress

print ranked summary sorted by objective_g
```

Failed/crashed runs: caught with `try/catch`, logged with `solver_status = "ERROR"`.

---

## Step-by-Step Implementation

1. **Modify `main.jl`**
   - Add `default_config()` above `main()`
   - Change signature to `function main(config=default_config())`
   - Replace all hardcoded refs with `config.gensets`, `config.battery`, `config.label`, etc.
   - Add `[objective]` and `[constraints]` dicts to `params_dict` in params.toml write block
   - Return `run_dir` on OPTIMAL, `nothing` otherwise
   - Replace final `main()` call with guard:
     `if abspath(PROGRAM_FILE) == @__FILE__; main(); end`

2. **Create `metrics.jl`**
   - `compute_metrics(run_dir)` — reads CSV row-by-row, reads params.toml
   - `is_valid_run(metrics)` — sanity checks

3. **Create `experiment.jl`**
   - Grid, loop, history.csv append, ranked summary print

4. **Smoke test**: `julia --project=. main.jl` — must produce identical output to before

5. **Single-candidate test**: call `main(cfg)` with one overridden E_init, verify
   history.csv gets one row and params.toml contains `[objective]` and `[constraints]`

6. **Full sweep**: `julia --project=. experiment.jl`

---

## Verification

- `julia --project=. main.jl` unchanged behaviour (regression test)
- params.toml for a new run contains `[objective]` and `[constraints]` sections
- history.csv row count = number of runs + 1 (header)
- `fuel_cost_g + startup_cost_g ≈ objective_g` for baseline runs
- Ranked summary prints runs sorted by `objective_g` ascending

---

## Adding an LLM Later

After the sweep, feed `history.csv` to Claude as a post-processing step (outside the loop):

```bash
claude -p "Here is my experiment history. Identify trade-offs between
E_init, fuel cost, and battery throughput. Suggest next candidates."
```

Output is advisory — human approves, then adds candidates to the grid in `experiment.jl`.
The `[objective]` / `[constraints]` sections in `params.toml` give the LLM full context
on what model each row used.
