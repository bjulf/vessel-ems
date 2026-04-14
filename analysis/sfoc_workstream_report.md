# Telemetry SFOC Workstream Report

Date: 2026-04-13

## Purpose

This report documents the telemetry-based SFOC work completed in this repository.

It is intended to be the single starting point for this part of the thesis work.

It explains:

- what data were collected and kept in the repository,
- how the data pipeline works,
- what was done step by step,
- which intermediate checks were performed,
- what results were achieved,
- and what conclusions are now defensible.

This report does not delete or replace the detailed notes already written during the workstream.
Those files remain as supporting material.

## Recommended Entry Points

If only a few files should be opened first, use these:

- [analysis/sfoc_workstream_report.md](./sfoc_workstream_report.md)
- [analysis/sfoc_cases/case_index.md](./sfoc_cases/case_index.md)
- [analysis/sfoc_cases/full_combined_all_windows/sfoc_regime_clean_compare.png](./sfoc_cases/full_combined_all_windows/sfoc_regime_clean_compare.png)
- [analysis/sfoc_cases/full_combined_all_windows/sfoc_fit_summary.txt](./sfoc_cases/full_combined_all_windows/sfoc_fit_summary.txt)
- [analysis/sfoc_cases/full_combined_all_windows/sfoc_oem_diagnostic.txt](./sfoc_cases/full_combined_all_windows/sfoc_oem_diagnostic.txt)

## Main Files Created or Used

### Core operational files

- [data/v01.csv](../data/v01.csv)
- [data/v01_clean.csv](../data/v01_clean.csv)
- [data/preprocess.py](../data/preprocess.py)

### Additional fetched telemetry windows kept in the repo

- [analysis/sfoc_datasets/march_window_2026-03-04_2026-03-06.csv](./sfoc_datasets/march_window_2026-03-04_2026-03-06.csv)
- [analysis/sfoc_datasets/november_window_2025-11-17_2025-11-20.csv](./sfoc_datasets/november_window_2025-11-17_2025-11-20.csv)
- [analysis/sfoc_datasets/january_window_2026-01-05_2026-01-07.csv](./sfoc_datasets/january_window_2026-01-05_2026-01-07.csv)
- [analysis/sfoc_datasets/january_window_2026-01-14_2026-01-16.csv](./sfoc_datasets/january_window_2026-01-14_2026-01-16.csv)

### Analysis scripts and notes

- [analysis/sfoc_fit.py](./sfoc_fit.py)
- [analysis/sfoc_screen.py](./sfoc_screen.py)
- [analysis/power_proxy_validation.py](./power_proxy_validation.py)
- [analysis/reconstructed_total_load.py](./reconstructed_total_load.py)
- [analysis/sfoc_assessment.md](./sfoc_assessment.md)
- [analysis/power_proxy_validation.md](./power_proxy_validation.md)
- [analysis/data_extraction_process.md](./data_extraction_process.md)
- [analysis/signal_inventory.md](./signal_inventory.md)
- [analysis/sfoc_handoff.md](./sfoc_handoff.md)
- [analysis/sfoc_case_comparison.md](./sfoc_case_comparison.md)

### Preserved case outputs

- [analysis/sfoc_cases/README.md](./sfoc_cases/README.md)
- [analysis/sfoc_cases/case_index.md](./sfoc_cases/case_index.md)
- [analysis/sfoc_cases/case_index.csv](./sfoc_cases/case_index.csv)

## What Data Were Looked At

The work used two groups of telemetry data.

### Group 1: Initial March operational dataset

The initial exploratory work used:

- `data/v01.csv`
- `data/v01_clean.csv`

This dataset spans:

- `2026-03-01 00:00:00` to `2026-03-03 18:00:00`

It has:

- dominant `1 minute` cadence,
- a few `2 minute` gaps,
- fuel rate,
- load percentage,
- speed,
- torque percentage,
- battery power,
- propulsion inverter powers,
- thruster inverter powers.

### Group 2: Follow-up targeted windows

After the first March assessment, a long-horizon hourly export was used only to locate better `1 minute` fetch windows.

That led to repo-owned windows for:

- March mixed-regime follow-up
- November low-speed-heavy follow-up
- January mixed / low-speed follow-up

These were fetched because the initial March dataset did not broaden the low-speed regime enough.

## Why This Work Was Done

The repository optimizer currently uses fixed OEM-style breakpoint curves in [main.jl](../main.jl).

The telemetry workstream was created to answer four practical questions:

1. Is the operational export good enough to support exploratory SFOC analysis?
2. Is the generator `load %` signal usable as a power proxy?
3. Do real operating speed regimes exist in the telemetry?
4. Can telemetry support a provisional alternative or sensitivity-case SFOC interpretation?

The work was not intended to prove a certified onboard fuel-measurement system.

It was intended to determine whether telemetry could inform the thesis in a defensible way.

## Data Pipeline

Two related but distinct pipelines were used.

### Pipeline A: Dispatch-model load pipeline

This is the path used to build optimizer load input.

1. Export raw telemetry to CSV.
2. Preserve the raw export as `data/v01.csv`.
3. Use [data/preprocess.py](../data/preprocess.py) to:
   - remove always-zero columns,
   - forward-fill sparse generator `Load percentage` tags,
   - create `data/v01_clean.csv`,
   - reconstruct total electrical load,
   - resample to the model timestep.
4. Write [data/load_profile.csv](../data/load_profile.csv) for [main.jl](../main.jl).

Important formula used in this pipeline:

`reconstructed_total_load_kw = gen1_load_pct / 100 * 385 + gen2_load_pct / 100 * 385 + battery_power`

This is a reconstructed load, not a directly measured full-bus load.

### Pipeline B: Telemetry SFOC analysis pipeline

This is the path used to assess operating regimes and SFOC behavior.

1. Start from `v01_clean.csv` or another fetched `1 minute` window.
2. Keep only generator fuel, load, and speed signals per genset.
3. Use the fallback power proxy:

`power_kw = load_pct / 100 * 385`

4. Convert fuel to mass flow using:

`fuel_gph = fuel_lph * 840`

5. Filter for steady points using a centered rolling window:
   - load standard deviation threshold
   - speed standard deviation threshold
   - positive fuel, load, and speed
6. Split steady points into:
   - `speed < 1600 rpm` -> `~1400 rpm`
   - `speed >= 1600 rpm` -> `~1800 rpm`
7. Bin by load percentage.
8. Compute per-bin medians and assess which bins are sufficiently supported.
9. Compare telemetry-derived breakpoints against the OEM breakpoint curve.
10. Store each dataset combination as a preserved analysis case under `analysis/sfoc_cases/`.

## Step-By-Step Work Completed

### Step 1: Initial branch assessment

The first step was to inspect the repository and determine whether telemetry-derived SFOC work was possible at all.

Result:

- OEM breakpoint curves were found in [main.jl](../main.jl).
- The active branch did not yet contain committed operational telemetry.
- The `operational_data` branch did contain a usable first dataset.

This assessment is documented in [analysis/sfoc_assessment.md](./sfoc_assessment.md).

### Step 2: Bring operational telemetry into the working branch

The needed files were brought into the working branch without a full branch merge.

Files:

- `data/v01.csv`
- `data/v01_clean.csv`
- `data/preprocess.py`

Result:

- the repo gained a local operational-data basis for analysis,
- and the preprocessing logic became inspectable in the main working branch.

### Step 3: Document the extraction and preparation workflow

The operational extraction and preprocessing workflow was written down for thesis-method use.

Main file:

- [analysis/data_extraction_process.md](./data_extraction_process.md)

Purpose:

- make the raw-to-cleaned-to-model-input path explicit,
- record forward-fill assumptions,
- document the reconstructed-load approach,
- and state the main limitations clearly.

### Step 4: Inventory available signals

The export schema was inspected to see which signals were genuinely usable and which were zero-only or missing.

Main file:

- [analysis/signal_inventory.md](./signal_inventory.md)

Important outcome:

- useful generator, battery, propulsion, and thruster signals were identified,
- but no trustworthy full-bus measured load and no measured per-genset electrical `kW` were found.

### Step 5: Validate the generator `load %` proxy

Because true per-genset active electrical `kW` was not available, the generator `load %` signal had to be tested before being used as a proxy.

Main files:

- [analysis/power_proxy_validation.md](./power_proxy_validation.md)
- [analysis/output/power_proxy_validation.png](./output/power_proxy_validation.png)
- [analysis/output/power_proxy_validation_summary.txt](./output/power_proxy_validation_summary.txt)

Key result:

- correlation between proxy supply and known measured propulsion/thruster load was `0.986`,
- the residual other onboard load was mostly positive and plausible,
- strongly negative residuals were effectively absent.

Interpretation:

- `load % * 385 kW` was accepted as a defensible exploratory power proxy,
- but explicitly kept as a proxy rather than a measured power signal.

### Step 6: Reconstruct total electrical load

A reconstructed total load figure was created to support the load and balance interpretation.

Main files:

- [analysis/output/reconstructed_total_load.png](./output/reconstructed_total_load.png)
- [analysis/output/reconstructed_total_load.md](./output/reconstructed_total_load.md)

Purpose:

- visualize the inferred total electrical demand,
- make the supply-side reconstruction transparent,
- support the thesis discussion of missing explicit onboard-load measurements.

### Step 7: Confirm that two speed regimes exist

The initial March dataset was screened to test whether low-speed and high-speed operation were real operating modes or just transients.

Main files:

- [analysis/sfoc_screen.py](./sfoc_screen.py)
- [analysis/sfoc_handoff.md](./sfoc_handoff.md)

Result:

- two real clusters appeared around `~1400 rpm` and `~1800 rpm`,
- sustained operation existed in both,
- and the low-speed mode was therefore treated as a real operational regime.

### Step 8: Fit the first March telemetry SFOC case

The first full telemetry fit was run on the initial March dataset.

Legacy one-off outputs:

- [analysis/output/sfoc_regime_overlay.png](./output/sfoc_regime_overlay.png)
- [analysis/output/sfoc_regime_clean_compare.png](./output/sfoc_regime_clean_compare.png)
- [analysis/output/sfoc_fit_summary.txt](./output/sfoc_fit_summary.txt)
- [analysis/output/sfoc_regime_breakpoints.csv](./output/sfoc_regime_breakpoints.csv)
- [analysis/output/sfoc_oem_diagnostic.txt](./output/sfoc_oem_diagnostic.txt)

Initial result:

- `~1800 rpm` had enough span and density for a provisional telemetry sensitivity curve,
- `~1400 rpm` remained too narrowly concentrated around roughly `48-50%` load.

At that stage, the defensible conclusion was:

- keep OEM as the optimizer baseline,
- use telemetry only as a sensitivity or discussion case,
- especially for `~1800 rpm`.

### Step 9: Add a preserved case system

As more windows were fetched, the workstream shifted from one-off outputs to preserved case folders.

This led to:

- [analysis/sfoc_cases/README.md](./sfoc_cases/README.md)
- [analysis/build_sfoc_case_index.py](./build_sfoc_case_index.py)
- [analysis/sfoc_cases/case_index.md](./sfoc_cases/case_index.md)

Reason:

- multiple datasets and combinations needed to be compared,
- the older plots and outputs had to be preserved,
- and new runs should not overwrite prior work.

Each case now stores:

- `sfoc_fit_summary.txt`
- `sfoc_regime_breakpoints.csv`
- `sfoc_regime_overlay.png`
- `sfoc_regime_clean_compare.png`
- `sfoc_oem_diagnostic.csv`
- `sfoc_oem_diagnostic.txt`
- `case_manifest.json`

### Step 10: Fetch additional March window

A longer March `1 minute` window was fetched after screening a longer, coarser hourly export.

Repo-owned file:

- [analysis/sfoc_datasets/march_window_2026-03-04_2026-03-06.csv](./sfoc_datasets/march_window_2026-03-04_2026-03-06.csv)

Reason:

- strengthen the March dataset,
- look for more low-speed support,
- and preserve a better mixed-regime operational sample.

March case comparison outputs:

- [analysis/sfoc_case_comparison.md](./sfoc_case_comparison.md)

Result:

- the new March window strengthened the `~1800 rpm` regime,
- but by itself still did not solve the low-speed coverage problem.

### Step 11: Screen the long-horizon hourly export and target low-speed windows

A much longer hourly export was used only as a scouting tool.

Reason:

- identify which `1 minute` windows were worth fetching next,
- specifically targeting the weak low-speed regime rather than collecting more generic `~1800 rpm` behavior.

This led to three follow-up targeted windows:

- [analysis/sfoc_datasets/november_window_2025-11-17_2025-11-20.csv](./sfoc_datasets/november_window_2025-11-17_2025-11-20.csv)
- [analysis/sfoc_datasets/january_window_2026-01-05_2026-01-07.csv](./sfoc_datasets/january_window_2026-01-05_2026-01-07.csv)
- [analysis/sfoc_datasets/january_window_2026-01-14_2026-01-16.csv](./sfoc_datasets/january_window_2026-01-14_2026-01-16.csv)

Reason for each:

- November window:
  - strongest low-speed-focused candidate,
  - broad low-speed load range,
  - especially valuable below the March operating cluster.
- January 05-07:
  - mixed-regime candidate,
  - useful bridge window with both low-speed and high-speed points.
- January 14-16:
  - low-speed-heavy candidate,
  - intended to add more low-load low-speed coverage.

### Step 12: Run preserved per-window and combined cases

The new windows were run both individually and in combined cases.

Important cases:

- [analysis/sfoc_cases/november_window_2025_11_17_to_11_20](./sfoc_cases/november_window_2025_11_17_to_11_20)
- [analysis/sfoc_cases/january_window_2026_01_05_to_01_07](./sfoc_cases/january_window_2026_01_05_to_01_07)
- [analysis/sfoc_cases/january_window_2026_01_14_to_01_16](./sfoc_cases/january_window_2026_01_14_to_01_16)
- [analysis/sfoc_cases/low_speed_followup_combined](./sfoc_cases/low_speed_followup_combined)
- [analysis/sfoc_cases/full_combined_all_windows](./sfoc_cases/full_combined_all_windows)

This was the key turning point in the workstream.

## Results Achieved

### Result 1: The telemetry shows two real speed regimes

Across the operational windows, the generators clearly operate in two speed bands:

- `~1400 rpm`
- `~1800 rpm`

This is not only startup or shutdown behavior.

This result remained stable through the later windows.

### Result 2: The load-percentage proxy is good enough for exploratory work

The `load % * 385 kW` fallback was never promoted to a measured-power claim.

However, the validation work showed it was good enough to support:

- regime screening,
- provisional fuel-versus-power fitting,
- and comparative SFOC interpretation.

### Result 3: The initial March-only conclusion was incomplete

March-only analysis supported:

- a strong `~1800 rpm` telemetry curve candidate,
- but not a regime-wide low-speed curve.

That conclusion was valid for March-only data.

It changed only after the targeted November and January follow-up windows were added.

### Result 4: The targeted low-speed follow-up windows materially improved the low-speed regime

The combined low-speed follow-up case is:

- [analysis/sfoc_cases/low_speed_followup_combined](./sfoc_cases/low_speed_followup_combined)

Its summary is:

- [analysis/sfoc_cases/low_speed_followup_combined/sfoc_fit_summary.txt](./sfoc_cases/low_speed_followup_combined/sfoc_fit_summary.txt)

Key result from that case:

- `~1400 rpm` supported bins:
  - `10-20%`
  - `20-30%`
  - `40-50%`
- supported low-speed span: `32.6` percentage points
- low-speed linear fuel fit:
  - `fuel_gph = -721.7 + 184.894 * power_kw`

Interpretation:

- the low-speed regime is no longer only a narrow `48-50%` cluster,
- and a provisional low-speed telemetry curve is now supportable.

### Result 5: The full combined telemetry case now supports provisional curves for both regimes

The most important current case is:

- [analysis/sfoc_cases/full_combined_all_windows](./sfoc_cases/full_combined_all_windows)

Main files for the latest full combined result:

- [sfoc_regime_clean_compare.png](./sfoc_cases/full_combined_all_windows/sfoc_regime_clean_compare.png)
- [sfoc_fit_summary.txt](./sfoc_cases/full_combined_all_windows/sfoc_fit_summary.txt)
- [sfoc_oem_diagnostic.txt](./sfoc_cases/full_combined_all_windows/sfoc_oem_diagnostic.txt)
- [sfoc_regime_breakpoints.csv](./sfoc_cases/full_combined_all_windows/sfoc_regime_breakpoints.csv)

Key combined-case numbers:

- rows: `19741`
- steady filtered points: `2939`
- `~1800 rpm` filtered points: `1737`
- `~1400 rpm` filtered points: `1202`

Supported bins in the latest full combined case:

- `~1800 rpm`:
  - `40-50%`
  - `50-60%`
  - `60-70%`
  - `70-80%`
- `~1400 rpm`:
  - `10-20%`
  - `20-30%`
  - `40-50%`
  - `50-60%`

Supported spans:

- `~1800 rpm`: `26.0` percentage points
- `~1400 rpm`: `35.5` percentage points

Linear fuel fits from the full combined case:

- `~1800 rpm`:
  - `fuel_gph = -4371.0 + 233.075 * power_kw`
- `~1400 rpm`:
  - `fuel_gph = -718.0 + 184.788 * power_kw`

At this point, the telemetry supports a provisional curve interpretation for both regimes.

### Result 6: Telemetry and OEM still disagree materially by regime

The OEM diagnostic for the latest full combined case is:

- [analysis/sfoc_cases/full_combined_all_windows/sfoc_oem_diagnostic.txt](./sfoc_cases/full_combined_all_windows/sfoc_oem_diagnostic.txt)

Main pattern:

- `~1800 rpm` telemetry sits above OEM by about `+7.7%` to `+14.3%`
- `~1400 rpm` telemetry sits below OEM in the supported bins

Important caution:

- the low-load `10-20%` and `20-30%` low-speed comparisons are not clean apples-to-apples OEM comparisons,
- because the active OEM breakpoint set begins at roughly `50%` load.

So the strongest OEM-versus-telemetry comparison remains:

- mid-load and high-load high-speed telemetry,
- and the mid-load low-speed telemetry band around `40-60%`.

## Current Interpretation

The workstream now supports the following statements.

### What is defensible

- The vessel telemetry supports a two-regime operating interpretation.
- The generator `load %` signal is a defensible exploratory power proxy.
- A provisional telemetry-derived `~1800 rpm` curve is well supported.
- After the November and January follow-up windows, a provisional telemetry-derived `~1400 rpm` curve is also supportable.
- Real operation appears to differ from the OEM fuel-optimal picture, especially in the high-speed regime.

### What remains uncertain

- There is still no measured per-genset active electrical `kW`.
- The power axis is still based on a proxy.
- The telemetry does not strongly cover the exact high-load low-speed OEM-efficient region that would matter most for a fuel-optimal dispatch model.
- The telemetry cannot prove that the present operating strategy is simply “wrong” or unconstrained.

### Practical thesis implication

Even after the successful low-speed follow-up windows, the safest modeling choice remains:

- keep OEM as the optimizer baseline curve source,
- use telemetry as empirical evidence and, if desired, as a bounded sensitivity case,
- and discuss the telemetry mainly as evidence that practical operation is shaped by objectives or constraints not represented in a fuel-only optimization.

## Why This Work Can Stop Here

This part of the thesis now has enough material to close cleanly.

The workstream achieved:

- a documented telemetry extraction and preparation pipeline,
- a validated power-proxy justification,
- evidence for two real operating regimes,
- preserved case tracking across all fetched windows,
- and a latest full combined telemetry case with provisional support for both regimes.

Further data-fetching is no longer necessary for the thesis to make a clear and defensible point.

The incremental value of more windows is now lower than the value of writing up the results and moving back to the main thesis deliverable.

## Recommended Final Position for the Thesis

Use the telemetry results in the thesis as follows:

1. Keep OEM curves as the main dispatch-model baseline.
2. Use telemetry to show that real operation occurs in two regimes.
3. Use telemetry to show that observed regime behavior differs from the OEM-efficient picture.
4. Discuss that gap as evidence that practical dispatch is influenced by additional onboard constraints or objectives.
5. If time permits, mention telemetry as a sensitivity or comparison case, but do not make the thesis depend on replacing the OEM curves with telemetry.

## Supporting Files Kept Intentionally

The following groups of files were intentionally preserved and not overwritten:

- legacy one-off outputs in `analysis/output/`
- case-specific outputs in `analysis/sfoc_cases/`
- fetched repo-owned telemetry windows in `analysis/sfoc_datasets/`
- method and interpretation notes in `analysis/`

This means the workstream remains fully auditable inside the repository.
