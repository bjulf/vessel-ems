# vessel-ems — Claude Context

## Project purpose

Maritime generator dispatch optimization. Solves a MILP (via JuMP + HiGHS) to minimize fuel consumption across marine diesel generators with battery integration. The broader goal is a **research accelerator**: a system that tracks experiments, grounds analysis in evidence, and proposes next steps — without autonomous execution.

## Domain language

| Term | Meaning |
|---|---|
| **Genset** | Marine diesel generator set |
| **SFOC** | Specific Fuel Oil Consumption (g/kWh) — efficiency curve of a generator at different load points |
| **SOC** | State of Charge — battery energy level as fraction of `E_max` |
| **E_init** | Initial battery energy (kWh) — key swept parameter in experiments |
| **Unit commitment** | On/off scheduling of generators (binary variable `u[g,t]`) |
| **Startup cost** | Fuel-equivalent penalty (grams) for starting a generator from off |
| **Model variant** | Named version of the optimization formulation (e.g. `"baseline"`) |
| **Run** | One solve: a unique `(model_variant, solver_settings, dataset, E_init)` tuple |
| **Proposal** | Formal object describing a planned experiment — requires explicit approval before execution |
| **Reflection** | LLM interpretation attached to a run or paper — never overwrites run facts |

## Model structure (`model.jl`)

**Objective:** minimize total fuel (grams) + startup costs over the planning horizon.

**Key variables:**
- `u[g,t]` — binary on/off status for generator `g` at time `t`
- `y[g,t]` — startup event (1 if `g` starts at `t`, continuous but forced 0/1 by integrality of `u`)
- `Pg[g,t]` — power output (kW)
- `SFOC[g,t]` — specific fuel consumption (g/kWh), modelled via piecewise-linear SOS2 interpolation
- `lambda[g,t,i]` — SOS2 weights for SFOC breakpoints
- `P_ch[t]`, `P_dis[t]` — battery charge/discharge power (kW)
- `E[t]` — stored battery energy (kWh), indexed 1..T+1
- `z_bat[t]` — binary: 1=charging, 0=discharging (prevents simultaneous charge+discharge)

**Key constraints:**
- Power balance: `sum(Pg) + P_dis - P_ch == load[t]`
- Generator min/max tied to on/off: `P_min * u <= Pg <= P_max * u`
- Piecewise-linear SFOC via SOS2 on breakpoints
- Battery energy evolution: `E[t+1] = E[t] + dt * (eta_ch * P_ch - (1/eta_dis) * P_dis)`
- Terminal SOC: `E[T+1] >= E_init` (don't drain below starting level)
- Symmetry-breaking: identical generators ordered by output per timestep

**Default config (in `main.jl`):**
- 2 identical gensets: 385 kW max, 192.5 kW min, 4-point SFOC curve
- Battery: 940 kWh capacity, SOC range 20–90%, charge 753 kW max, discharge 943 kW max, η=0.95 both ways
- Timestep: 15 min (dt = 0.25 h)
- Load profile: `data/load_profile.csv`

## Run identity and reproducibility

Each run is uniquely identified by: `(model_variant, solver_settings, dataset, E_init)`

Every run stores:
- `runs/<timestamp>_<label>/params.toml` — full config + git hash + git_dirty flag
- `runs/<timestamp>_<label>/dispatch_results.csv` — per-timestep dispatch solution
- `.current_run` — path to most recent run directory

Sweep history: `experiments/history.csv` — one row per run with key metrics.

**Never modify `experiments/history.csv` manually.**

## How to run

```bash
# Single run with default config
julia main.jl

# Parameter sweep over E_init SOC values (20%–80%)
julia experiment.jl

# Plot results for a run
python plot.py

# Julia environment setup (first time)
julia --project=. -e "using Pkg; Pkg.instantiate()"
```

## Architecture decisions

| Decision | Rationale |
|---|---|
| Julia for solver, Python for visualization/backend | Existing codebase; Julia called via subprocess from Python layer |
| `params.toml` + `history.csv` as run record | Already implemented; sufficient for current phase |
| Git hash per run | Reproducibility: link result to exact model code |
| Startup cost in grams equivalent | Keeps objective in consistent units (grams fuel) |

## Non-negotiables (from `docs/PLAN.md`)

- **No experiment runs without explicit approval**
- **No code changes applied automatically**
- **LLM reflections never overwrite run facts or metrics**
- **Paper excerpts are evidence; LLM summaries are interpretation — never mix them**
- **Every reflection must point to evidence (a run, a paper, or both)**
- Chat/assistant interface is transport only — never the source of truth

## Development phases (current status)

The project follows a phased plan in `docs/PLAN.md`:
- **Phase 0–1** (partially complete): Run identity, persistence, parameter sweep, basic plotting
- **Phase 2** (next): Formal proposal/approval boundary before any experiment runs
- **Phase 3+**: Reflection memory, CLI assistant, typed command layer, chat interface, paper retrieval

Current branch: `madlab`. Main branch: `master`.
