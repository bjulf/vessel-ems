# PLAN: Building a Defensible Telemetry-Based SFOC Approximation

## Purpose

This document defines a step-by-step process for deciding whether this project should:

1. derive generator SFOC curves from operational data,
2. stay with OEM/datasheet SFOC values, or
3. use a hybrid approach where OEM curves are the baseline and telemetry is used only for adjustment or plausibility checks.

The goal is not just to fit a curve. The goal is to produce an SFOC approximation that is technically reliable enough to defend in a thesis and stable enough to use in the dispatch model.

## Immediate Model Priority

Before relying on operational data for validation, the dispatch model should be extended to support optional shore-power import at the vessel bus.

- Treat shore power as an exogenous bus-side source with bounded availability over time.
- Keep the feature disabled by default in synthetic baseline runs until harbor scenarios are defined.
- Revisit operating rules later, especially whether gensets may run in parallel with shore connection.

## Scope Guidance for a Master's Thesis

This plan is intentionally broader than the minimum thesis workflow so that all relevant risks are visible. It should not be interpreted as a requirement to perform a full industrial qualification program.

For a master's thesis, the goal is usually:

- to show a rigorous assessment process,
- to justify the final modeling choice,
- to quantify the most important limitations,
- not to certify the telemetry as a contractual measurement system.

That means the thesis does not need to resolve every possible uncertainty to industrial standards. It does need to show that the main uncertainties were identified and handled honestly.

Use the plan in two layers:

- `Core thesis path`: the minimum work needed for a defensible academic conclusion.
- `Extended path`: additional work that improves confidence if time, access, and data allow.

The thesis is still successful if the conclusion is that OEM data should remain primary.

## Decision Statement

The thesis should make one explicit claim at the start of this workstream:

- `Claim A`: "Operational telemetry is sufficiently trustworthy to derive a vessel-specific SFOC approximation."
- `Claim B`: "Operational telemetry is useful for plausibility checking and limited tuning, but not reliable enough to replace OEM SFOC curves."
- `Claim C`: "Operational telemetry is not sufficiently trustworthy for curve derivation; OEM data remain the defensible source."

Everything below is designed to support one of those three claims.

## Core Thesis Path

This is the recommended minimum path for a master's thesis.

1. Establish the OEM baseline for the installed genset.
2. Identify what the telemetry signals most likely represent and document the remaining unknowns.
3. Build a cleaned dataset with timestamps, fuel signal, speed, and power or justified power proxy.
4. Show whether two speed regimes exist and why one blended curve would be misleading.
5. Extract steady-state windows and fit exploratory regime-specific curves.
6. Compare exploratory telemetry-derived curves against OEM points.
7. State clearly whether telemetry is good enough to replace OEM, only good enough for plausibility checking, or not good enough for either.
8. Run limited dispatch sensitivity tests if different SFOC assumptions materially affect the optimization.

If this core path is completed well, the thesis has enough methodological depth.

For a short, execution-focused version of the telemetry-curve workflow, including Go / No-Go criteria and a time-boxed fitting process, see [GenerateSFOCCurve.md](C:/Users/bulve/OneDrive/master/model/GenerateSFOCCurve.md).

## Extended Path

The following are valuable but optional for thesis scope:

- deeper sensor-calibration audit,
- detailed timestamp-lag correction,
- extensive holdout validation across many date ranges,
- endogenous binary regime selection in the optimizer,
- broad uncertainty propagation studies,
- large-scale automation of the full assessment workflow.

These should only be pursued if they clearly improve the thesis rather than delaying the main result.

## Current Repository Context

The current optimization model in [main.jl](C:/Users/bulve/OneDrive/master/model/main.jl) and [model.jl](C:/Users/bulve/OneDrive/master/model/model.jl) assumes fixed piecewise-linear SFOC breakpoints per generator.

The pilot operational dataset already suggests:

- the gensets operate in at least two speed regimes, around `1400 rpm` and `1800 rpm`,
- those regimes have materially different implied fuel consumption per kWh,
- available data only cover part of the load range,
- the data are promising for exploratory analysis,
- the data are not yet sufficient for a full-range, high-confidence single SFOC curve.

This means the current model assumption of one static curve per generator may eventually need to be revisited.

## Current Status Update

The following has now been established:

- the installed package is the Volvo Penta `D13-MH (VG)` `385 kWe` variable-speed genset,
- OEM SFOC reference points exist for the exact package,
- the operational data show at least two clear speed regimes, roughly `1400 rpm` and `1800 rpm`,
- supplier-provided Modbus information indicates that the genset signal is exposed as `Fuel Rate [L/h]`,
- the Modbus engineering scaling appears consistent with an `L/h` fuel-flow value.

The following are still unresolved:

- whether `Fuel Rate [L/h]` is directly measured or calculated by the control system,
- whether the value represents net engine consumption or gross fuel supply,
- whether fuel return flow is already accounted for,
- whether the signal is filtered or averaged before export,
- whether trustworthy per-genset electrical `kW` is available,
- whether the telemetry-derived curves would be stable enough to replace OEM data in the optimizer.

Current working conclusion:

- telemetry-based SFOC estimation is justified as an exploratory analysis branch,
- telemetry-based SFOC is not yet justified as the final authoritative model input,
- OEM data remain the baseline until signal provenance and validation are stronger.

## Core Principle

An SFOC curve is only as trustworthy as the weakest part of this chain:

`fuel measurement -> power measurement -> timestamp alignment -> operating-state identification -> filtering -> curve fit -> validation -> uncertainty statement`

If any one of these steps is not defensible, the thesis should not present a telemetry-derived SFOC curve as authoritative.

## Success Criteria

The telemetry-based approach is acceptable only if all of the following are true:

- fuel rate measurement method and units are known,
- per-genset electrical output can be measured or inferred with a justified method,
- timestamps and sampling frequency are known and consistent,
- the data contain enough steady-state operation to estimate generator efficiency,
- major operating regimes are identifiable and modeled separately when needed,
- the fitted curve is physically plausible,
- the fit is stable under reasonable filtering choices,
- uncertainty and limitations can be stated quantitatively or at least systematically,
- the telemetry-derived curve does not create unjustified dispatch behavior in the optimizer.

## Showstoppers

If any of these remain unresolved, the thesis should default to OEM data or a hybrid approach.

- Unknown fuel-rate measurement method.
- Fuel rate is ECU-estimated or virtual, but the algorithm is undocumented.
- Fuel measurement does not account for return flow or bypass flow.
- No trustworthy per-genset power signal exists.
- Power is inferred only from `load %` without proof that `load %` maps linearly to electrical output over the relevant modes.
- Sampling is too sparse to identify steady-state operation or transients.
- Timestamps across signals are not synchronized and cannot be corrected.
- Data coverage is poor across load range or operating regimes.
- Variable-speed operation exists, but speed or mode is not available.
- Sensor drift, clipping, flatlining, or missingness materially distort the usable data.
- Telemetry-derived curves conflict strongly with OEM behavior and the discrepancy cannot be explained.
- Uncertainty is too large for the intended optimization use.

## When OEM Data Are Probably Better

Rely primarily on sparse OEM information if one or more of the following are true:

- the telemetry fuel signal is not a direct measurement,
- telemetry is available only for a narrow operating envelope,
- the gensets are used in multiple regimes but the regime logic is unknown,
- only a short time period is available,
- there is no way to validate telemetry-derived curves against another source,
- the thesis timeline does not allow a proper measurement audit,
- the operational-data curve would require too much undocumented inference.

In that case, the defensible thesis position is:

- use OEM SFOC as the primary model input,
- use telemetry only to show operating envelope, likely regimes, and possible deviations,
- present telemetry analysis as exploratory evidence, not as the source of truth.

## High-Level Work Plan

## Phase 0: Define the Modeling Target

Before collecting more data, define exactly what curve is needed.

Questions to answer:

- Is the target quantity generator `SFOC = mass fuel flow / electrical energy output`?
- Is the curve meant for one generator, pooled identical generators, or generator classes?
- Is one curve enough, or is `SFOC(load, speed regime)` required?
- Is the optimization model allowed to use different curves by mode?
- Does the curve need to represent steady-state efficiency only, or average operational efficiency including transients?

Deliverable:

- one paragraph in the thesis defining the target variable and its intended use in the optimizer.

## Phase 1: Measurement-System Audit

This is the most important phase.

You need a signal register for every relevant tag:

- signal name from the portal,
- engineering description,
- units,
- sample interval,
- source system,
- sensor type,
- whether it is measured or computed,
- calibration procedure if known,
- timestamp origin,
- known failure modes,
- whether the signal is per-genset or system-level.

Minimum signals to audit:

- per-genset fuel rate,
- per-genset electrical power output in `kW`,
- per-genset load percentage,
- per-genset engine speed,
- per-genset running status,
- per-genset breaker status,
- battery power,
- battery SOC,
- bus or microgrid power,
- shore connection power,
- propulsion inverter powers,
- thruster powers.

Critical questions for the fuel signal:

- Is fuel rate measured directly or computed by the engine controller?
- If measured directly, is it mass flow or volumetric flow?
- If volumetric, at what reference temperature and density?
- Is there a supply meter only, or supply and return?
- If there is return flow, is the reported tag already net consumption?
- Is the value filtered in the controller?
- What is the vendor documentation for this signal?

Current evidence already available:

- the installed control interface exposes a Modbus signal labeled `Fuel Rate [L/h]`,
- the register-level documentation confirms `L/h` as the engineering unit,
- the full register list may be confidential and therefore may not be reproducible in the thesis.

What this resolves:

- the signal is not unitless,
- the signal is volumetric rather than mass-based,
- a density assumption will be needed to compare against SFOC in `g/kWh`.

What this does not resolve:

- whether the signal is measured or calculated,
- whether it is net or gross fuel flow,
- whether return flow is accounted for,
- whether controller-side filtering is present.

Trust hierarchy for fuel-rate signals:

- `Tier 1`: direct net mass-flow measurement, ideally Coriolis or equivalent.
- `Tier 2`: direct volumetric measurement with known density and temperature correction.
- `Tier 3`: ECU-estimated fuel rate from injection maps.
- `Tier 4`: unknown virtual or aggregated fuel estimate.

Only `Tier 1` and `Tier 2` support a strong thesis claim for absolute SFOC. `Tier 3` may still support an exploratory or relative efficiency analysis. `Tier 4` should not be used as the primary source for a fitted SFOC curve.

Exit criterion:

- a completed measurement audit table with no unresolved critical unknowns about fuel-rate meaning.

## Phase 2: Data Acquisition Plan

Collect data to maximize coverage, not just sample count.

Recommended extraction strategy:

- use the highest raw resolution available, including `15 s` if possible,
- collect multiple dates across different operating contexts,
- include dates with low hotel load,
- include dates with transit load,
- include dates with heavy thruster or DP activity if relevant,
- include dates with charging and discharging battery behavior,
- include periods with one genset online,
- include periods with two gensets online and load sharing,
- include at least some high-load operation if it exists.

Why `15 s` data help:

- better transient detection,
- better synchronization checks,
- better steady-state window detection,
- better visibility into ramps, starts, and stops.

Why `15 s` data are not enough on their own:

- they do not solve missing load-range coverage,
- they do not solve unknown units,
- they do not solve unknown sensor topology,
- they do not solve regime mixing.

Data acquisition target:

- enough data to populate each meaningful operating regime with repeated windows across the useful load range.

Exit criterion:

- a dataset inventory table listing date ranges, resolution, signal completeness, and operating context.

## Phase 3: Build a Reproducible Data Inventory

Create a local inventory of all datasets used for this analysis.

Recommended repository additions:

- `data/raw_portal_exports/` for immutable exports,
- `data/metadata/` for signal dictionary, unit notes, and extraction logs,
- `analysis/` for exploratory and fitting scripts,
- `results/sfoc_assessment/` for figures and tables intended for the thesis.

For each export, record:

- portal source,
- extraction date,
- date range in the data,
- resolution,
- timezone,
- file checksum,
- known filtering done by the portal,
- any missing columns.

Exit criterion:

- every plotted or fitted result can be traced back to a named raw export.

## Phase 4: Timebase, Units, and Signal Harmonization

Standardize:

- timestamp format,
- timezone,
- units,
- missing-value representation,
- sampling interval,
- generator identifiers,
- sign conventions.

Explicitly document:

- whether fuel is `kg/h`, `g/s`, `L/h`, or another unit,
- whether electrical power is instantaneous `kW`, averaged `kW`, or apparent power,
- whether battery power positive means charging or discharging,
- whether `load %` is engine load or generator electrical load.

If the portal provides volumetric fuel flow, convert to mass flow only with a justified density model.

At present, the working assumption is that the telemetry fuel signal is `L/h`. Any conversion to `kg/h` or `g/kWh` must therefore state the assumed density explicitly and distinguish between:

- OEM reference density assumptions,
- actual fuel-property information if available,
- sensitivity of results to the density assumption.

If the portal provides only electrical load percentage, define whether power is approximated as:

`P_el = load_pct / 100 * rated_power`

This approximation is acceptable only if justified with documentation or cross-checks against actual measured `kW`.

Exit criterion:

- one cleaned, harmonized analysis table with fully documented units and sign conventions.

## Phase 5: Basic Signal Quality Assessment

Assess each relevant signal for:

- completeness,
- reporting cadence,
- missing-value bursts,
- flatlining,
- impossible values,
- jumps,
- clipping,
- repeated values,
- suspicious quantization,
- drift across time,
- inconsistent zero behavior.

Plots to produce:

- completeness over time,
- histograms,
- time-series slices,
- value-change histograms,
- cross-correlations between related signals.

Checks to run:

- positive fuel flow when generator is off,
- nonzero power when breaker is open,
- sudden load jumps without corresponding power changes,
- speed changes without state changes,
- impossible battery and generator combinations.

Exit criterion:

- a sensor-quality memo for each core signal stating whether it is usable, usable with filtering, or unusable.

## Phase 6: Physical Consistency Checks

Before fitting anything, verify that the data obey basic power-system physics.

Check:

- per-genset power aligns with load percentage,
- total generator output plus battery net power approximately matches bus demand,
- running status aligns with speed and power,
- fuel is near zero when the generator is stopped,
- fuel increases with power in a physically sensible way,
- speed regimes are real and repeatable.

This phase should identify:

- transients,
- startup/shutdown windows,
- sensor lag,
- sign errors,
- unit errors,
- stale values due to forward-fill behavior in the portal.

Exit criterion:

- the cleaned signals satisfy power-balance and state-consistency checks within a documented tolerance.

## Phase 7: Operating-State Segmentation

Segment the data into meaningful operating states before estimating SFOC.

Likely states:

- off,
- starting,
- stopping,
- synchronization and breaker closing,
- low-load idle or standby,
- steady-state single-genset operation,
- steady-state dual-genset operation,
- high-thruster or DP operation,
- battery charging,
- battery discharging,
- abnormal or faulted operation.

If variable-speed behavior exists, add speed or mode labels such as:

- `~1400 rpm`,
- `~1800 rpm`,
- other clusters if present.

This step matters because one blended curve across multiple modes is usually wrong.

Exit criterion:

- each sample or window is labeled by operating state and, where relevant, speed regime.

## Phase 8: Steady-State Window Detection

SFOC for optimization should usually be derived from steady-state windows, not raw pointwise telemetry.

Recommended first-pass steady-state criteria:

- generator online and breaker closed,
- minimum window length of `5-15 min`,
- load variation within a small band,
- speed variation within a small band,
- no start/stop event near the window,
- no abrupt battery power reversals,
- no portal missing-data imputation in the window.

Use the raw `15 s` data for window detection even if the final fit uses 1-minute or 5-minute aggregates.

The purpose of this step is to remove:

- warm-up and cool-down periods,
- ramps,
- governor settling,
- load-step recovery,
- synchronization artifacts,
- short sensor glitches.

Exit criterion:

- a library of steady-state windows with documented filtering rules.

## Phase 9: Power Attribution Strategy

This phase determines whether per-genset SFOC is actually identifiable.

Best case:

- per-genset fuel rate is available,
- per-genset electrical power `kW` is available,
- each generator can be analyzed directly.

Acceptable fallback:

- per-genset fuel rate is available,
- only `load %` is available,
- `load %` can be validated against electrical `kW` or OEM documentation.

Weak case:

- only total fuel or only total bus power is available,
- multiple gensets operate simultaneously,
- individual SFOC cannot be attributed without additional assumptions.

If attribution is weak, restrict analysis to periods with one genset online or do not fit an individual curve.

Exit criterion:

- a written justification for how power and fuel are attributed to each generator.

## Phase 10: Candidate Model Forms

Fit several candidate representations and compare them.

Recommended candidate forms:

- OEM breakpoints with no change,
- OEM breakpoints with telemetry-adjusted values,
- piecewise-linear curve fitted to telemetry,
- quadratic or cubic polynomial on fuel rate versus power,
- monotone-convex constrained fit if variable-speed modes are important,
- separate curves per speed regime,
- one pooled curve per regime if the two gensets behave similarly.

Recommended current order of work:

1. fit exploratory curves separately for the `~1400 rpm` and `~1800 rpm` regimes,
2. compare both against OEM reference points,
3. assess whether the curves are stable enough for thesis use,
4. only after that consider whether optimizer-side mode switching is warranted.

Prefer fitting `fuel rate vs power` and then converting to SFOC. This is often more stable than fitting SFOC directly.

Hard constraints for any candidate fit:

- nonnegative fuel flow,
- physically reasonable monotonicity in fuel rate,
- no implausible efficiency spike at very low load,
- no extrapolation beyond supported operating range without explicit warning.

Exit criterion:

- a short-listed set of candidate curves with clear assumptions.

## Phase 11: Validation and Uncertainty Assessment

This is where the thesis becomes defensible or not.

Validate the fitted curves against:

- holdout dates not used for fitting,
- chronological splits rather than only random splits,
- alternative filtering thresholds,
- alternative aggregation windows,
- generator 1 versus generator 2,
- different operating regimes,
- OEM reference values.

Useful metrics:

- RMSE on fuel rate,
- MAE on fuel rate,
- bias,
- median absolute percentage error,
- uncertainty bands on SFOC,
- sensitivity of breakpoints to filtering choices.

Also perform stress tests:

- fit with and without questionable windows,
- fit using only one-genset periods,
- fit using only high-confidence fuel windows,
- fit using one month versus another month,
- fit with and without low-load data.

Telemetry-derived curves are trustworthy only if the results are stable under these checks.

Exit criterion:

- a validation table and an uncertainty statement suitable for the thesis.

## Phase 12: Compare Telemetry-Derived Curves Against OEM

Do not treat telemetry and OEM as mutually exclusive until this comparison is complete.

Compare:

- breakpoint values,
- minimum-SFOC region,
- shape at low load,
- shape near rated load,
- regime-specific behavior,
- implied fuel use over representative duty cycles.

Possible outcomes:

- telemetry agrees with OEM within reasonable tolerance,
- telemetry suggests small, explainable deviations,
- telemetry suggests major deviations that are plausible and supported,
- telemetry suggests major deviations that cannot be justified.

If the last case occurs, default back toward OEM.

Exit criterion:

- a comparison plot and a written explanation of agreement or disagreement.

## Phase 13: Dispatch-Model Integration Decision

After validation, choose one of three implementation paths.

Path 1: Keep OEM curves.

- Use existing `main.jl` structure.
- Add a report discussion explaining why telemetry was not used as the source of truth.

Path 2: Use telemetry-adjusted static curves.

- Replace current breakpoints in [main.jl](C:/Users/bulve/OneDrive/master/model/main.jl).
- Keep one curve per generator if regimes can be safely collapsed.

Path 3: Extend the optimizer to handle multiple modes.

- separate curve sets by speed regime,
- regime-selection logic in preprocessing or optimization,
- possibly add binary mode variables if mode switching matters.

Only choose Path 3 if the extra complexity is justified by data quality and thesis scope.

Practical note:

- do not introduce an endogenous binary speed-mode switch in the optimizer yet,
- first establish whether two telemetry-derived regime curves are stable and defensible,
- if regime can be assigned exogenously from measured speed or operating context, prefer that before adding new integer decisions.

Exit criterion:

- a written model-integration decision with rationale.

## Phase 14: Sensitivity Analysis in the Optimizer

Regardless of the chosen curve source, run optimization sensitivity tests.

Test:

- OEM curve,
- telemetry-derived curve,
- upper and lower uncertainty curve,
- hybrid curve.

Check whether dispatch conclusions change materially:

- generator commitment pattern,
- starts and stops,
- battery use,
- total fuel consumption,
- marginal value of the battery,
- preferred operating region.

If optimization conclusions are highly sensitive to uncertain SFOC assumptions, that must be stated explicitly in the thesis.

Exit criterion:

- a sensitivity table and a short discussion of result robustness.

## What the Thesis Report Must Contain

The report should justify the SFOC source, not just present the final curve.

## Minimum Report Sections

1. Objective of the SFOC work.
2. Why SFOC is needed in the dispatch model.
3. Description of available operational data.
4. Sensor and signal audit.
5. Data cleaning and harmonization process.
6. Operating-state segmentation and steady-state selection.
7. Curve-fitting methodology.
8. Validation and uncertainty assessment.
9. Comparison against OEM information.
10. Final decision on curve source.
11. Limitations and implications for optimization results.

## Tables the Report Should Include

- signal dictionary,
- sensor/source audit,
- data availability by date and resolution,
- operating-regime coverage table,
- load-range coverage table,
- filtering rules,
- validation metrics,
- telemetry versus OEM comparison,
- dispatch sensitivity results.

If confidential supplier material is used, the report should also include:

- a short note stating that signal definitions were checked against supplier-provided documentation,
- a note that the full register map cannot be reproduced due to confidentiality restrictions,
- a concise restatement in prose of the specific signal facts that are needed for the method.

## Figures the Report Should Include

- raw and cleaned time-series examples,
- completeness plots,
- speed-regime clustering plot,
- fuel rate versus power scatter,
- steady-state window examples,
- fitted curves with uncertainty bands,
- telemetry versus OEM overlay,
- optimizer sensitivity comparison.

## Explicit Limitations the Report Should State

- whether fuel rate is measured or computed,
- that the currently known signal unit is volumetric `L/h`,
- whether low-load behavior is well observed,
- whether high-load behavior is observed,
- whether the curve is regime-specific,
- whether the curve is valid only for a subset of vessel operation,
- whether extrapolation was required,
- whether the final curve is absolute or only relative.

## Recommended Thesis Narrative if Telemetry Succeeds

"Operational data were subjected to a measurement audit, physical consistency checks, steady-state filtering, and out-of-sample validation. Because the fuel and power signals were sufficiently well understood and the resulting curves were stable across repeated operating windows, telemetry was considered an acceptable source for a vessel-specific SFOC approximation."

## Recommended Thesis Narrative if OEM Remains Primary

"Operational telemetry was analyzed to assess whether a vessel-specific SFOC curve could be derived. However, unresolved uncertainty in signal provenance, operating-regime coverage, and/or sensor accuracy meant that a telemetry-derived curve could not be defended as a primary source. OEM SFOC data were therefore retained as the main model input, while telemetry was used only for plausibility checks and qualitative discussion."

## Recommended Thesis Narrative if a Hybrid Approach Is Best

"OEM SFOC data were used as the baseline because they remain the only fully documented source across the full operating envelope. Operational telemetry was then used to identify relevant operating regimes, assess plausibility, and quantify likely vessel-specific deviations within the observed operating range."

## Repository Implementation Plan

This repository should eventually add a separate SFOC-analysis workflow instead of mixing it into the current load-preprocessing script.

Recommended additions:

- `analysis/sfoc_signal_audit.md`
- `analysis/sfoc_extract_inventory.csv`
- `analysis/sfoc_assessment.py`
- `analysis/sfoc_fit.py`
- `analysis/sfoc_validation.py`
- `data/metadata/signal_dictionary.csv`
- `data/metadata/extraction_log.csv`
- `results/sfoc_assessment/`

Recommended processing stages:

- `00_inventory`
- `01_harmonize`
- `02_quality_checks`
- `03_segment_states`
- `04_extract_steady_windows`
- `05_fit_curves`
- `06_validate`
- `07_export_breakpoints`

## Immediate Next Steps

These are the next concrete actions to take.

1. Treat the Modbus `Fuel Rate [L/h]` information as a partial resolution of signal units, not as full proof of signal provenance.
2. Confirm whether `Fuel Rate` is measured, estimated, filtered, and netted for return flow.
3. Confirm whether true per-genset electrical `kW` is available from the portal or control system.
4. Export additional date ranges at raw resolution, ideally `15 s`.
5. Prioritize periods with one generator online and stable load.
6. Build the signal dictionary and extraction log, including the known `Fuel Rate [L/h]` fact and confidentiality note.
7. Run a first formal sensor-quality audit.
8. Fit exploratory two-regime curves only after the above checks are in place.
9. Keep OEM curves as the active model baseline until the telemetry branch passes validation.
10. In parallel, continue with other simulation work that does not depend on final telemetry-based SFOC adoption.

## Customer Portal Extraction Checklist

Use this checklist when pulling additional data from the customer portal.

## Objective of Each Extract

Every extract should have a stated purpose before download:

- `signal audit extract`: used to identify signal meaning, units, cadence, and missingness,
- `steady-state extract`: used to fit candidate SFOC curves,
- `validation extract`: used only for holdout testing,
- `event extract`: used to inspect start, stop, synchronization, and ramp behavior.

Do not download large date ranges without knowing which of these purposes they serve.

## What to Export First

Priority 1 signals:

- timestamp,
- per-genset fuel rate,
- per-genset electrical power `kW`,
- per-genset load percentage,
- per-genset engine speed,
- per-genset running status,
- per-genset breaker status.

Priority 2 signals:

- battery power,
- battery SOC,
- microgrid or main bus power,
- shore power,
- propulsion inverter powers,
- thruster inverter powers.

Priority 3 signals:

- alarms and event logs,
- governor or mode status,
- generator frequency,
- voltage,
- current,
- power factor,
- maintenance flags or engine health indicators.

## Resolution Strategy

If the portal allows multiple resolutions:

- export raw or highest available resolution first, ideally `15 s`,
- avoid portal-side averaging unless necessary,
- if file-size limits are strict, split exports by date range rather than using coarser resolution,
- only downsample locally after inspecting the raw data.

Recommended default:

- `15 s` or raw for short representative windows,
- `1 min` for medium-length coverage checks,
- longer windows only after verifying that the higher-resolution data are consistent.

## Date-Range Strategy

Choose dates to cover distinct operating patterns, not just consecutive days.

Try to include:

- one low-load hoteling day,
- one transit day,
- one day with significant thruster use if relevant,
- one day with battery charging and discharging,
- one day with mostly single-genset operation,
- one day with multi-genset load sharing,
- one day with the highest loads you can find.

For each candidate date, quickly check:

- which gensets were online,
- whether speed regimes changed,
- whether battery activity was present,
- whether enough steady-state windows exist.

## Export Naming Convention

Use a consistent naming pattern:

`YYYYMMDD_YYYYMMDD_resolution_context_source.csv`

Examples:

- `20260301_20260303_15s_signal-audit_portal.csv`
- `20260315_20260315_15s_single-genset_portal.csv`
- `20260402_20260405_1min_validation_portal.csv`

## Metadata to Record for Every Export

Create a log entry with:

- file name,
- export date,
- portal name,
- vessel name or anonymized ID,
- timezone shown by the portal,
- requested date range,
- delivered date range,
- requested resolution,
- delivered resolution,
- list of exported tags,
- any missing tags,
- any portal filters or aggregations applied,
- who performed the export,
- reason for the export.

## First Three Extracts to Request

If time is limited, start with these:

1. `Signal audit extract`
   Include `15 s` data for one short window with starts, stops, and normal operation.

2. `Steady-state fitting extract`
   Include `15 s` or raw data for a day with long stable single-genset periods and a wide load range.

3. `Holdout validation extract`
   Include a different day not used for fitting, ideally in a similar operating context.

## Practical Rules While Exporting

- Prefer raw tags over portal-derived KPIs.
- Export both `Fuel Rate` and any similarly named alternative fuel tags if they exist.
- Export both `load %` and `kW` if both exist.
- Export status signals even if they seem redundant.
- Keep one untouched raw copy of every export.
- Do not merge files manually before logging them.
- If the portal truncates or aggregates silently, note that immediately.

## Red Flags During Portal Extraction

Stop and investigate if:

- the same tag appears with multiple units,
- values are identical across long periods,
- a per-genset tag changes only every 5 minutes while others update every 15 seconds,
- fuel remains positive while speed is zero,
- a signal disappears when the genset is off,
- a portal dashboard value cannot be mapped to an exportable raw tag.

## Questions to Ask Colleagues

These questions are intended for colleagues who know the installed generators, the automation system, the customer portal, or the electrical integration.

## Fuel Measurement Questions

- What exactly is the `Fuel Rate` signal on each genset?
- Is it measured directly by a sensor, or calculated by the engine control system?
- If measured directly, what hardware produces it?
- Is it mass flow or volumetric flow?
- If volumetric, what density or temperature correction is used?
- Does the measurement account for fuel return flow?
- Is the signal net engine consumption, gross supply flow, or something else?
- Is the signal filtered or averaged before it reaches the portal?
- What is the expected accuracy of this signal?
- Has this signal ever been used internally for fuel accounting or only for monitoring?

## Power Measurement Questions

- Do we have true per-genset electrical active power in `kW`?
- If yes, where is that measured?
- Is it measured at the generator terminals, breaker, switchboard, PMS, or another level?
- Is the exported `load %` based on electrical power, torque, engine load, or another internal quantity?
- Is the mapping from `load %` to `kW` linear and documented?
- Are there situations where `load %` is misleading compared with actual electrical output?

## Operating Mode and Control Questions

- Are these generators fixed-speed or variable-speed in normal service?
- If variable-speed, what modes are used and why?
- What determines switching between roughly `1400 rpm` and `1800 rpm`?
- Is speed controlled by PMS logic, local governor logic, or another supervisory controller?
- Are there warm-up, cool-down, or standby modes that affect fuel consumption without meaningful electrical output?
- Are there known operating modes where efficiency is intentionally sacrificed for stability or response?

## System Integration Questions

- How are the generators integrated with the battery and power management system?
- During battery charging, how is generator loading controlled?
- Does the PMS deliberately bias one generator over the other?
- During multi-genset operation, do the units share load equally?
- Are there periods where one genset carries spinning reserve with low electrical load but nontrivial fuel burn?
- Is shore power ever active in the same periods as generator operation?

## Data Provenance Questions

- Which system is the source of truth for the portal tags?
- Are the timestamps generated onboard or in the cloud platform?
- Are all exported signals time-synchronized?
- Are there known offsets or delays between engine, electrical, and battery signals?
- Are missing values real missing data, or does the portal suppress unchanged values?
- Has anyone already validated these signals for another project?

## Sensor Accuracy and Maintenance Questions

- What are the installed sensor types and model numbers for fuel and power measurement?
- When were they last calibrated?
- Is there a calibration certificate or maintenance record?
- Are there known biases, drifts, or common failure modes?
- Have any sensors been replaced during the time period of interest?
- Are there periods where the measurements are known to be unreliable due to maintenance, faults, or configuration changes?

## OEM and Commissioning Questions

- Do we have OEM SFOC sheets for these exact engines and ratings?
- Do we have sea-trial, FAT, SAT, or commissioning performance data?
- Were the installed engines derated or configured differently from the standard datasheet case?
- Do we have documentation for expected fuel use at different loads and speeds?
- Has the company already compared measured fuel use against OEM data?

## Questions About Thesis Defensibility

- Would the company consider the portal `Fuel Rate` trustworthy enough for contractual or reporting use?
- If not, why not?
- If yes, under what conditions?
- What would internal technical staff consider an acceptable validation of a telemetry-derived fuel curve?
- Are there operational constraints or confidentiality issues that limit what can be stated in the thesis?

## Recommended First Conversation

For the first colleague discussion, focus on getting answers to these five questions:

1. What exactly is the per-genset `Fuel Rate` signal, and how is it generated?
2. Do we have true per-genset electrical `kW`, and where is it measured?
3. Why do the gensets appear to operate at both about `1400 rpm` and `1800 rpm`?
4. Are the portal timestamps and sample intervals trustworthy and synchronized?
5. Do we have OEM or commissioning fuel-performance documents for these exact installed units?

If those five remain unresolved, do not start serious curve fitting yet.

Update:

- the `Fuel Rate [L/h]` unit question is now partially resolved,
- the remaining highest-value questions are whether the signal is measured or calculated, whether it is net fuel consumption, and whether true per-genset `kW` exists.

## Decision Gate Checklist

Use this checklist before committing to telemetry-derived SFOC.

- `Yes/No`: Fuel-rate measurement principle is known.
- `Yes/No`: Fuel-rate units are known.
- `Yes/No`: Return-flow handling is known.
- `Yes/No`: Per-genset electrical output is trustworthy.
- `Yes/No`: Timestamps are synchronized.
- `Yes/No`: Variable-speed regimes are identified.
- `Yes/No`: Enough steady-state windows exist.
- `Yes/No`: Useful load-range coverage exists.
- `Yes/No`: Fit is stable under filtering changes.
- `Yes/No`: Telemetry and OEM comparison is explainable.
- `Yes/No`: Optimization conclusions remain robust.

If more than two of these remain `No`, do not treat telemetry-derived SFOC as authoritative.

## Literature and Standards to Use in the Report

These sources are relevant to the thesis rationale and method design.

- ISO 3046-1:2002, official ISO page. This is the standard reference for declarations of power, fuel consumption, and test methods for reciprocating engines. Useful for explaining what OEM SFOC values represent.  
  Link: https://www.iso.org/standard/28330.html

- ISO 8178-1:2017, official ISO page. Useful for discussing formal engine measurement systems and why fuel-flow measurement details matter.  
  Link: https://www.iso.org/standard/64710.html

- Dageförde et al., "Metrology for reliable fuel consumption measurements in the maritime sector," *Measurement*, 2024. Useful for discussing flow-meter uncertainty, dynamic fuel-consumption measurement, and why metrology matters.  
  Link: https://www.sciencedirect.com/science/article/pii/S0263224124000459

- Einang, Styve, and Valkealahti, "Estimation and Optimization of Vessel Fuel Consumption," *IFAC-PapersOnLine*, 2016. Useful because it explicitly discusses online estimation of specific fuel consumption for individual generators in diesel-electric vessels using measured operational profiles.  
  Link: https://doi.org/10.1016/j.ifacol.2016.10.436

- Zhu, Zuo, and Li, "Modeling of Ship Fuel Consumption Based on Multisource and Heterogeneous Data," *JMSE*, 2021. Useful for motivating sensor fusion, mixed frequencies, and structured data processing.  
  Link: https://doi.org/10.3390/jmse9030273

- Vorkapić et al., "Toward Realistic Ship Fuel Consumption Prediction Under Chronological Validation," *JMSE*, 2025. Useful for supporting chronological rather than purely random validation of models built from operational data.  
  Link: https://www.mdpi.com/2077-1312/14/6/538

- Kim et al., "Ship operational data driven fuel efficiency assessment for shaft generator using input convex neural network," *Energy Reports*, 2025. Useful for justifying physically constrained data-driven models and regime-aware operational fuel-efficiency analysis.  
  Link: https://doi.org/10.1016/j.egyr.2025.108993

## Final Recommendation

At this stage, the correct strategy is:

- do not fit the final authoritative SFOC curve yet,
- first complete the measurement audit,
- gather more raw high-resolution data across more dates and operating contexts,
- decide whether the thesis can support a telemetry-derived curve, an OEM curve, or a hybrid approach.

Near-term implementation recommendation:

- continue using OEM curves as the active model baseline,
- allow telemetry-based SFOC work to proceed as an exploratory side branch,
- fit two provisional telemetry curves by speed regime if the remaining signal questions are resolved enough,
- postpone optimizer-side binary regime switching until the exploratory curves are validated.

That decision should be framed as a methodological result, not as a failure. If telemetry cannot be defended, concluding that OEM data are the only trustworthy source is still a valid and useful thesis outcome.
