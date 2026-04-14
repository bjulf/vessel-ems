# Initial SFOC Assessment

Date: 2026-04-13

## Objective

Assess whether the current repository contents are sufficient to start generating a telemetry-informed SFOC curve, following [GenerateSFOCCurve.md](../GenerateSFOCCurve.md).

## Current Branch Evidence

- The optimizer currently uses fixed OEM-style breakpoint curves in [main.jl](../main.jl).
- The active generator definition is two identical `385 kWe` units with breakpoints:
  - `P = [192.5, 288.75, 310, 385] kW`
  - `SFOC = [193, 191, 191, 198] g/kWh`
- The repository contains a synthetic load workflow in [data/generate_synthetic_profile.py](../data/generate_synthetic_profile.py) and [data/load_profile.csv](../data/load_profile.csv).
- The current `master` branch does not contain committed operational telemetry exports.
- The `operational_data` branch does contain:
  - `data/v01.csv`
  - `data/v01_clean.csv`
  - `data/preprocess.py`
- No committed telemetry harmonization, quality-check, or curve-fitting script was found.
- The report pipeline in [report.qmd](../report.qmd) reports optimizer inputs and outputs, not raw telemetry assessment results.

## Preliminary Screening From `operational_data`

The `operational_data` branch contains a first usable operational dataset snapshot.

Quick screening results from `data/v01_clean.csv` on that branch:

- rows: `3959`
- columns: `18`
- time range: `2026-03-01 00:00:00` to `2026-03-03 18:00:00`
- dominant sampling interval: `1 min`
- a few `2 min` gaps exist

Generator 1:

- positive `fuel + load + speed` points: `746`
- provisional regime split:
  - `< 1600 rpm`: `446`
  - `>= 1600 rpm`: `300`
- main observed speeds cluster around `1400 rpm` and `1799-1800 rpm`
- observed load range with valid points: `2.0%` to `76.0%`

Generator 2:

- positive `fuel + load + speed` points: `345`
- provisional regime split:
  - `< 1600 rpm`: `102`
  - `>= 1600 rpm`: `243`
- main observed speeds cluster around `1398-1400 rpm` and `1798-1800 rpm`
- observed load range with valid points: `4.25%` to `78.5%`

Operational implication:

- the branch appears sufficient for a first-pass exploratory curve assessment,
- the data appear to support the claimed two-regime structure,
- coverage still looks partial, especially near rated operation,
- true per-genset active electrical `kW` is still not present in the visible branch files,
- first-pass power attribution would therefore rely on `load % * 385 kW` unless better data exist elsewhere.

## Gate Check Against GenerateSFOCCurve

- OEM baseline exists: `Yes`
- Installed genset package is documented in project notes: `Yes`
- Telemetry fuel unit is documented in project notes: `Partly`
- Telemetry fuel provenance is resolved: `No`
- Per-genset electrical `kW` available in repo: `No`
- Operational speed signal available in repo: `Yes`, on `operational_data`
- Operational dataset available in repo: `Yes`, on `operational_data`
- Sampling resolution can be checked from repo data: `Yes`, on `operational_data`
- Stable windows can be screened from repo data: `Yes`, on `operational_data`
- Two speed regimes can be verified from repo data: `Yes`, provisionally, on `operational_data`

## Current Judgment

The current `master` branch is not yet in a state where a telemetry-derived SFOC curve can be generated from local data alone.

The current position is:

- `Go` for a first-pass exploratory SFOC assessment using the `operational_data` branch dataset.
- `No-Go` for promoting telemetry to the main model input yet.
- OEM breakpoints should remain the active model baseline until the telemetry-derived curve is actually fit, screened, and tested in the optimizer.

## What Is Missing

Minimum data needed to start a real first-pass fit:

- timestamp
- per-genset `Fuel Rate [L/h]`
- per-genset engine speed `rpm`
- per-genset active electrical power `kW`, or a defensible `load %` fallback
- per-genset running status
- per-genset breaker status

Status against that minimum:

- timestamp: `available` on `operational_data`
- `Fuel Rate [L/h]`: `available` as `Fuel Rate`
- engine speed: `available`
- active electrical `kW`: `not yet available`
- `load %`: `available`
- running / breaker status: `not visible in the inspected branch files`

Recommended first evidence package:

- one short raw or `15 s` extract containing starts, stops, and stable operation
- one fitting extract with long single-genset steady windows
- one holdout extract from a different day

## Recommended Next Step

Recommended immediate next step:

1. bring `data/preprocess.py` and the `v01` files into the working branch, either by merge or selective cherry-pick,
2. implement a small screening / fitting script separate from `preprocess.py`,
3. fit provisional `fuel rate vs load-derived power` curves per speed regime,
4. compare them against OEM breakpoints,
5. keep the result as a sensitivity-case candidate unless true per-genset `kW` is found.
