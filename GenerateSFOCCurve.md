# Generate SFOC Curve

## Purpose

This document is a short, execution-focused guide for generating a telemetry-informed SFOC approximation under thesis time pressure.

It is not a replacement for [PLAN.md](C:/Users/bulve/OneDrive/master/model/PLAN.md). It is the practical workflow to use when the goal is to quickly determine whether operational data are good enough to produce a usable alternative to the OEM breakpoint curve.

## Recommended Use

Use this workflow only after the following are at least partially established:

- the installed genset package is known,
- an OEM SFOC baseline exists,
- the telemetry fuel signal has a known unit,
- the telemetry fuel signal is at least partly understood,
- the data show identifiable operating regimes.

For the present case, the working assumptions are:

- genset: Volvo Penta `D13-MH (VG)` `385 kWe`,
- OEM baseline points exist,
- `Fuel Rate [L/h]` is supplier-confirmed as a calculated consumed-fuel value excluding return flow,
- the operational data show two speed regimes around `1400 rpm` and `1800 rpm`.

This workflow should also be used to answer two practical screening questions before doing serious fitting:

- Is the currently available timestep resolution high enough for this purpose?
- Is the currently available operational dataset good enough for this purpose?

## Scope

This workflow is intended for a master's thesis analysis.

The objective is:

- to generate a defensible telemetry-informed curve candidate,
- to compare it against the OEM curve,
- to decide whether it is strong enough to be used in the model,
- or whether it should remain only a sensitivity case.

It is not intended to certify the telemetry as an industrial-grade fuel measurement system.

## Go / No-Go Criteria

## Go: Make Telemetry the Main Case Only If All of These Are True

- separate curves can be fit for `~1400 rpm` and `~1800 rpm`,
- the fitted curves are smooth and physically plausible,
- the fitted curves broadly align with the OEM shape and level,
- the fitted curves are supported by more than a handful of points,
- the fitted curves remain similar under small filtering changes,
- the optimizer behaves sensibly when using the telemetry-derived breakpoints.

## No-Go: Keep OEM as the Main Case If Any of These Occur

- one regime is too sparse to fit credibly,
- the fitted curve is jagged or nonphysical,
- low-load points dominate the fit,
- the fitted curve changes a lot when filtering is adjusted slightly,
- the telemetry-derived curve produces obviously strange dispatch behavior,
- telemetry disagrees strongly with OEM for no explainable reason.

## Decision Logic

- If telemetry is strong: use telemetry as main case and OEM as comparison/reference.
- If telemetry is mixed: keep OEM as main case and use telemetry as sensitivity case.
- If telemetry is weak: keep OEM as main case and discuss telemetry only qualitatively.

## Working Assumptions for Fast Curve Generation

If better information is not available in time, use these assumptions explicitly:

- `Fuel Rate [L/h]` is converted to mass flow using `840 g/L`,
- the density assumption is taken from the Volvo reference material and must be stated in the report,
- if true per-genset electrical `kW` is unavailable, power is approximated from `load %` as:

`P_el = load_pct / 100 * 385`

- the approximation above must be clearly labeled as an assumption.

## Pre-Check 1: Is the Current Timestep Resolution Good Enough?

Before fitting anything, assess whether the available sampling rate is adequate.

General guidance:

- `15 s` or raw data are preferred for identifying transients and steady-state windows,
- `1 min` data can still be good enough for fitting if stable operating periods are long and clearly visible,
- `5 min` or coarser data are usually weak for separating transients from steady-state behavior,
- already averaged or portal-smoothed data must be treated cautiously.

The current data are good enough on timestep resolution only if:

- speed regime changes can still be identified,
- startup and shutdown periods can be excluded with reasonable confidence,
- steady-state windows remain visible,
- adjacent samples are frequent enough to detect obvious ramps or disturbances.

If these conditions are not met, do not try to build the final curve from the current export alone. Use the current dataset only for exploratory screening and request higher-resolution data if possible.

## Pre-Check 2: Is the Current Dataset Good Enough?

Before fitting, assess whether the available dataset has enough quality and coverage.

The current dataset is good enough only if most of the following are true:

- there are enough positive fuel-flow points,
- there are enough stable windows in each speed regime,
- the load range is not concentrated in only one narrow band,
- the fitted curve will not depend on just a few isolated points,
- the data quality is good enough to remove obvious outliers and transients without losing almost everything,
- the resulting curve can be compared meaningfully against OEM points.

The current dataset is not good enough as a main source if any of the following happen:

- one regime has very sparse coverage,
- almost all usable points sit in one narrow load region,
- only low-load or mid-load data exist with no support near rated operation,
- small filtering changes produce very different fitted curves,
- the dataset can only support a few points but not a stable trend.

Practical thesis decision:

- if the current dataset is only moderately good, it can still support an exploratory or sensitivity-case curve,
- if the current dataset is clearly strong, it may support replacing the OEM curve in the main case,
- if the current dataset is weak, keep OEM as the main case and use the telemetry result only in discussion.

## Recommended Workflow

## Step 1: Prepare Fitting Data

Use only data points that satisfy all of the following:

- positive `Fuel Rate`,
- positive power or positive `load %`,
- valid speed,
- no obvious missing-value artifacts,
- no startup or shutdown event,
- no rapid transient if steady-state fitting is the goal.

Preferred additional restriction:

- one genset online at a time where possible.

This reduces attribution error and makes the resulting curve easier to defend.

Before continuing past this step, explicitly record:

- whether the current timestep resolution was judged sufficient,
- whether the current dataset was judged sufficient for a main-case curve or only for a sensitivity-case curve.

## Step 2: Split by Regime

Split the data into two provisional regimes:

- `speed < 1600 rpm` -> `~1400 rpm regime`
- `speed >= 1600 rpm` -> `~1800 rpm regime`

Do not blend the two regimes into one curve.

## Step 3: Convert Fuel Signal

Convert volumetric fuel flow to mass flow:

`fuel_gph = fuel_lph * 840`

This is a working assumption, not a fully verified fuel-property measurement. State that clearly.

## Step 4: Estimate Electrical Power

Preferred:

- use true per-genset active electrical power in `kW`.

Fallback:

- infer power from `load %`:

`power_kw = load_pct / 100 * 385`

Only use the fallback if true `kW` is unavailable and the assumption is documented.

## Step 5: Fit Fuel Rate Versus Power

Fit `fuel rate vs power`, not SFOC directly.

Reason:

- this is usually more stable,
- raw fuel flow tends to be less numerically noisy than direct `g/kWh`,
- SFOC can be derived afterward.

Recommended fit types:

- piecewise-linear,
- low-order polynomial,
- or breakpoint averages based on stable load clusters.

Avoid:

- high-order polynomials,
- aggressive extrapolation,
- fits dominated by low-load points.

## Step 6: Convert to SFOC

Convert fitted fuel flow to SFOC:

`SFOC = fuel_gph / power_kw`

Inspect the result for:

- unrealistic low-load efficiency spikes,
- negative or nonphysical behavior,
- unreasonable jumps between nearby operating points.

## Step 7: Select Breakpoints

Pick `3-4` breakpoints per regime from dense, stable operating regions.

Good breakpoint candidates are:

- around `50%` load,
- around `75%` load,
- near minimum-SFOC region,
- near rated load if coverage exists.

Do not force breakpoints into regions without meaningful data support.

## Step 8: Compare Against OEM

Plot or tabulate:

- OEM breakpoint curve,
- telemetry-derived `~1400 rpm` curve,
- telemetry-derived `~1800 rpm` curve,
- raw or filtered telemetry points.

Look for:

- similar overall shape,
- plausible magnitude,
- explainable differences,
- whether telemetry supports two regimes more strongly than one blended curve.

## Step 9: Decide Main Case vs Sensitivity Case

Use the Go / No-Go criteria above.

Recommended default under time pressure:

- keep OEM as the active baseline,
- treat telemetry as an alternative curve set,
- promote telemetry to the main case only if it is clearly stable and credible.

## Step 10: Run Sensitivity Analysis

At minimum, run:

- one case with OEM breakpoints,
- one case with telemetry-derived breakpoints.

Compare:

- total fuel consumption,
- genset starts and stops,
- battery usage,
- dispatch pattern,
- any clearly visible qualitative differences.

If results are highly sensitive to the curve source, state that explicitly in the report.

## What Not To Do Under Time Pressure

- do not add an endogenous binary speed-mode switch in the optimizer,
- do not redesign the model architecture around speed regimes,
- do not attempt a full uncertainty propagation study,
- do not replace the OEM curve without keeping an OEM comparison case.

## Recommended 4-Hour Execution Plan

## Hour 1: Prepare Clean Data

- filter valid points,
- exclude obvious transients,
- split by speed regime,
- convert `L/h` to `g/h`,
- compute or assign power.

## Hour 2: Fit Provisional Curves

- fit `fuel rate vs power`,
- convert to SFOC,
- build provisional regime-specific breakpoints,
- overlay against OEM.

## Hour 3: Decide Curve Status

- apply Go / No-Go criteria,
- choose whether telemetry becomes main case or sensitivity case,
- prepare breakpoint values for model input.

## Hour 4: Run Comparison Cases and Write

- run OEM case,
- run telemetry case,
- compare outputs,
- write the method, assumptions, and limitations clearly.

## Suggested Thesis Wording

"Supplier clarification indicated that the reported `Fuel Rate [L/h]` signal is a calculated consumed-fuel value excluding return flow. Based on this, an approximate telemetry-derived fuel curve was fitted from operational data and compared against OEM reference points. Due to remaining assumptions on density and power attribution, the telemetry-derived curve was treated as an approximate operational model and evaluated alongside the OEM curve in sensitivity analysis."

## Deliverables

At the end of this workflow, the minimum useful outputs are:

- a telemetry-derived curve or breakpoint table,
- an OEM vs telemetry comparison figure,
- a written decision on whether telemetry is main case or sensitivity case,
- a short limitations statement suitable for the thesis.
