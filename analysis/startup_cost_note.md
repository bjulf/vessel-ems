# Startup Cost Note

Date: 2026-04-13

## Purpose

This note explains how startup fuel was estimated from the operational dataset and how that estimate should be interpreted relative to the startup-cost value used in the dispatch model.

The main conclusion is:

- the operational data can support a rough **fuel-only** startup estimate,
- but the optimization startup penalty should still be treated as an **experimental engineering penalty** that can be set higher than the measured fuel-only startup overhead.

This is reasonable if the goal is to:

- represent wear and cycling cost,
- discourage excessive start/stop chattering,
- and reflect that the operational cost of a start is not only the fuel burned in the first few minutes.

## Files

Method script:

- [analysis/startup_fuel_estimate.py](./startup_fuel_estimate.py)

Saved outputs:

- [analysis/output/startup_fuel_events.csv](./output/startup_fuel_events.csv)
- [analysis/output/startup_fuel_summary.txt](./output/startup_fuel_summary.txt)

Current model parameter reference:

- [main.jl](../main.jl)

## What Was Calculated

The current export does not include a direct startup-event fuel counter.

So a simple event-based estimate was constructed from the `1 minute` telemetry.

For each generator:

1. A start event was identified at the first row where the unit becomes `online`.
2. `online` was defined as:

   `speed > 0 OR fuel rate > 0`

3. After the detected start, the signal was scanned forward until the generator first reached a stable operating-speed band.
4. Stable speed was defined as the first row where **three consecutive samples** lie in either:

   - `1350-1450 rpm` -> `~1400 rpm regime`
   - `1750-1850 rpm` -> `~1800 rpm regime`

5. Startup fuel was then defined as:

   **fuel burned from the start row up to, but not including, the first stable-speed row**

6. The fuel-rate unit was integrated using the `1 minute` timestep:

   `fuel_before_stable_l = sum(fuel_lph) / 60`

7. The same fuel amount was also converted to grams using:

   `840 g/L`

This gives a rough estimate of fuel consumed in the startup and acceleration phase before the machine settles into a recognizable operating-speed regime.

## Why This Definition Was Chosen

This definition is intentionally simple.

It avoids the more fragile alternative of trying to compute startup fuel relative to a hypothetical steady-state reference for the later loaded operation.

That more complicated approach performed poorly because:

- load ramps during startup are substantial,
- fuel demand after stabilization depends strongly on the target operating load,
- and the current `1 minute` data do not resolve all startup sub-phases cleanly.

The present method is therefore a conservative and transparent way to estimate the startup-phase fuel quantity that is directly visible in the telemetry.

## Event Results

Per-event results from the current extract:

| Gen | Start time | Stable regime | Minutes before stable | Fuel before stable [L] | Fuel before stable [g] |
|---|---|---|---:|---:|---:|
| 1 | 2026-03-01 11:28 | `~1400 rpm` | 3 | 0.301 | 252.6 |
| 1 | 2026-03-01 21:39 | `~1800 rpm` | 3 | 0.678 | 569.7 |
| 1 | 2026-03-02 02:47 | `~1400 rpm` | 3 | 0.236 | 198.1 |
| 1 | 2026-03-03 08:28 | `~1800 rpm` | 3 | 0.192 | 161.7 |
| 1 | 2026-03-03 13:23 | `~1800 rpm` | 7 | 3.026 | 2541.7 |
| 2 | 2026-03-02 14:54 | `~1800 rpm` | 3 | 0.481 | 403.9 |
| 2 | 2026-03-02 18:05 | `~1400 rpm` | 3 | 0.138 | 115.5 |
| 2 | 2026-03-03 15:17 | `~1800 rpm` | 4 | 0.733 | 616.0 |

## Summary of Results

Grouped by target stable regime:

### `~1400 rpm` starts

- count: `3`
- fuel before stable: mean `0.22 L`, median `0.24 L`
- fuel before stable: mean `188.7 g`, median `198.1 g`

### `~1800 rpm` starts

- count: `5`
- fuel before stable: mean `1.02 L`, median `0.68 L`
- fuel before stable: mean `858.6 g`, median `569.7 g`

### Overall

- overall mean startup fuel: `607.4 g`
- overall median startup fuel: `328.2 g`

## Interpretation

The dataset suggests that the **pure startup fuel overhead** is relatively small.

Typical starts appear to consume:

- a few tenths of a liter of fuel,
- or a few hundred grams of fuel,
- before the genset settles into a stable speed regime.

One event is clearly larger than the others:

- `2026-03-03 13:23`
- about `3.03 L`
- about `2.54 kg`

This event ramped through several intermediate speed and load states before stabilizing and should be treated as a heavier or less clean startup sequence rather than the typical case.

So the operational data support the statement that:

- **fuel-only startup cost is probably on the order of hundreds of grams, not tens of kilograms**

## Why the Model Startup Cost Can Still Be Higher

This is the key modeling point.

The startup penalty used in the dispatch model does **not** have to equal only the startup fuel measured in telemetry.

A startup penalty in a unit-commitment-style model can reasonably represent:

- startup fuel,
- thermal and mechanical wear,
- breaker and synchronization stress,
- maintenance burden from frequent cycling,
- and a general anti-chatter penalty that prevents unrealistic start/stop oscillation.

Therefore, it is completely defensible to set the model startup cost **above** the observed startup fuel amount if the modeling objective is to discourage excessive cycling and better reflect real operational preference.

## Relation to the Current Model Value

The current model in [main.jl](../main.jl) uses:

- `startup_cost = 15000 g` equivalent per start

This is much larger than the startup fuel estimated directly from the current telemetry.

That does **not** mean the value is wrong.

It means the current startup cost should be interpreted as:

- an experimental equivalent-fuel penalty,
- intended to include wear and anti-chatter behavior,
- not as a literal measurement of startup diesel burned in the first few minutes.

## Recommended Interpretation for the Thesis

The startup fuel estimate can be used in the thesis to justify the following distinction:

- **measured or estimated startup fuel** is small,
- but **the optimization startup penalty** is intentionally larger because it also stands in for wear and cycling aversion.

That distinction is stronger and more defensible than pretending that the optimization startup penalty is a direct fuel measurement.

## Recommended Thesis Wording

"A rough startup-fuel estimate was derived from the operational data by integrating the reported fuel-rate signal from the first detected start until the generator reached a stable operating-speed regime. This analysis suggested that the direct fuel consumed during startup was typically on the order of a few hundred grams. However, the startup penalty used in the optimization model was set higher than this fuel-only estimate, because the model penalty was intended to represent not only startup fuel but also wear, operational preference against frequent cycling, and the need to avoid unrealistic start-stop chattering in the dispatch solution."

## Practical Recommendation

For the current model work:

- keep the startup cost as an experimental engineering parameter,
- do not claim it is equal to the measured startup fuel,
- and it is reasonable to increase it further if needed to suppress unrealistic chattering.

If the value is changed, the clean interpretation is:

- **this is a modeling penalty chosen for dispatch behavior, informed by but not equal to startup fuel**

rather than:

- **this is the exact startup fuel cost**
