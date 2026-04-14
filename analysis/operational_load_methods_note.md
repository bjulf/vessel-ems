# Operational Load Representation Method Note

Date: 2026-04-14

## Purpose

This note consolidates the full workflow used to represent operational electrical load in the thesis study.

It is intended as a direct source for report writing.

The goal is to document:

- what data were available,
- how the operational load signal was reconstructed,
- how the reconstruction was checked,
- how the final model input was produced,
- and whether the process is sufficient for its intended purpose.

## Short Answer

Yes, the repository now contains enough information to write a defensible Methods subsection for operational load representation.

However, the thesis should describe the resulting load as:

- a reconstructed operational electrical load estimate,
- suitable for exploratory dispatch modeling,
- not a directly metered full-vessel electrical load.

That distinction matters.

## Source Files

Main raw export:

- [data/v01.csv](../data/v01.csv)

Cleaned analysis table:

- [data/v01_clean.csv](../data/v01_clean.csv)

Model input profile:

- [data/load_profile.csv](../data/load_profile.csv)

Processing code:

- [data/preprocess.py](../data/preprocess.py)
- [analysis/reconstructed_total_load.py](./reconstructed_total_load.py)

Supporting notes:

- [analysis/data_extraction_process.md](./data_extraction_process.md)
- [analysis/signal_inventory.md](./signal_inventory.md)
- [analysis/power_proxy_validation.md](./power_proxy_validation.md)
- [analysis/operational_data_validation_handoff.md](./operational_data_validation_handoff.md)

Generated figure:

- [analysis/output/operational_load_validation.png](./output/operational_load_validation.png)

## Data Basis

The main operational dataset used for the load-representation workflow is `v01.csv`.

Current checked characteristics of this file:

- time range: `2026-03-01 00:00:00` to `2026-03-03 18:00:00`
- rows: `3959`
- dominant sampling interval: `1 minute`
- minor gaps: a small number of `2 minute` intervals

This dataset is currently the strongest single-window basis for the operational-load Methods figure in this repository because:

- it contains the battery power signal,
- it contains both genset `Load percentage` signals,
- it contains the available measured propulsion and thruster inverter powers,
- and it provides a more complete measured load-side reference than the other currently stored one-minute windows.

## Available Signals Used in the Load Workflow

The operational-load representation uses four signal groups.

### 1. Generator proxy signals

- generator 1 `Load percentage`
- generator 2 `Load percentage`

These are not direct measured electrical powers in `kW`.
They are used as generator-output proxies.

### 2. Battery signal

- battery power

This is used directly in the power balance.

### 3. Explicitly measured load-side signals

- propulsion port inverter power
- propulsion starboard inverter power
- thruster port aft inverter power
- thruster port forward inverter power
- thruster starboard aft inverter power

In the current main March export, the starboard aft thruster tag exists but is zero throughout the inspected period.
It is therefore structurally present but not informative in this window.

### 4. Context signals

- timestamp
- vessel position
- speed over ground

These are useful for interpretation, but not required to construct the load profile itself.

## Signals That Were Not Available

The thesis should state clearly that the export did not contain:

- measured per-generator active electrical power in `kW`,
- a trustworthy total bus or full-vessel electrical load tag,
- explicit hotel-load tags,
- explicit HPU / hydraulic-load tags,
- a full auxiliary-load decomposition.

This is the reason a reconstructed total load had to be created.

## Full Step-By-Step Process

The operational-load representation used in the thesis can be documented as the following workflow.

### Step 1: Export raw operational telemetry

Operational data were exported from the customer data system as a timestamped CSV file.

For the current workflow, the main raw file is:

- [data/v01.csv](../data/v01.csv)

The raw export is preserved unchanged.

### Step 2: Inspect the export schema

The raw export was checked to determine:

- which electrical signals were present,
- which signals were informative,
- which signals were always zero,
- and which important load measurements were missing.

This inspection established that direct full-vessel load measurement was not available.

### Step 3: Create a cleaned analysis table

The script [data/preprocess.py](../data/preprocess.py) removes columns that are always zero and writes:

- [data/v01_clean.csv](../data/v01_clean.csv)

This cleaned file is used for exploratory analysis and signal inspection.

This step does not change the row-wise time basis of the export.
It only removes non-informative columns.

### Step 4: Convert the relevant electrical signals to numeric form

The relevant battery, generator, propulsion, and thruster columns are converted to numeric values.

Any non-numeric entries are coerced to missing values before further processing.

This prevents string or mixed-type parsing issues from contaminating the later calculations.

### Step 5: Handle sparse generator controller updates

The generator `Load percentage` registers are sparsely updated in the export rather than repeated on every row.

The workflow therefore:

- forward-fills generator 1 `Load percentage`,
- forward-fills generator 2 `Load percentage`,
- and fills any remaining missing values with zero.

This is a critical assumption.
The interpretation is that a reported controller value remains valid until a new register value is received.

### Step 6: Handle battery and measured load-side missing values

Battery power missing values are filled with zero.

Measured propulsion and thruster power signals are:

- filled with zero where missing,
- and clipped at zero to avoid negative measured load contributions.

This creates a conservative measured load-side reference.

### Step 7: Construct generator power proxies

Because measured per-generator electrical power in `kW` is not available, generator output is approximated from load percentage and rated generator power.

The proxy used is:

`gen_kw_proxy = load_pct / 100 * 385`

for each genset, where `385 kW` is the rated electrical power of each unit.

The combined generator proxy is:

`genset_kw_proxy = gen1_kw_proxy + gen2_kw_proxy`

### Step 8: Reconstruct total electrical load

The reconstructed total load is defined as:

`reconstructed_total_load_kw = genset_kw_proxy + battery_power`

with battery sign convention:

- positive battery power = battery discharge to the bus,
- negative battery power = battery charging from the bus.

This reconstructed signal is intended to represent vessel electrical demand at the bus.

It is not a direct measurement.

### Step 9: Clip small negative reconstructed values

The raw reconstructed load can become slightly negative in a small number of rows because of signal timing mismatch, sparse controller updates, or battery charging exceeding the proxy supply momentarily.

The workflow therefore clips the reconstructed load at zero.

In the current March dataset:

- only `11` rows become negative before clipping,
- and the minimum raw value is `-4.4 kW`

This is small relative to the operating range and does not dominate the reconstructed profile.

### Step 10: Build a measured reference load

The explicitly measured load-side reference is defined as the sum of available propulsion and thruster inverter powers:

`known_measured_load_kw = propulsion inverter powers + thruster inverter powers`

This is not the total vessel electrical demand.

It is the part of the vessel demand that is explicitly visible in the export.

### Step 11: Compute residual onboard load

The residual onboard load is defined as:

`other_onboard_load_kw = reconstructed_total_load_kw - known_measured_load_kw`

This residual is interpreted as load that is physically present on the vessel bus but not explicitly metered in the available telemetry, such as:

- hotel load,
- auxiliaries,
- HPU or hydraulic loads,
- pumps,
- fans,
- controls,
- and other onboard consumers.

### Step 12: Validate the reconstruction against the measured demand pattern

The reconstruction is checked by comparing:

- reconstructed total load,
- known measured propulsion/thruster load,
- generator proxy contribution,
- and battery power contribution.

The validation figure is:

- [analysis/output/operational_load_validation.png](./output/operational_load_validation.png)

The logic of the validation is:

- the reconstructed load should follow the same operating pattern as the measured propulsion and thruster load,
- the remaining positive difference should be physically interpretable as unmetered onboard load,
- and the balance should not produce frequent strongly negative residuals.

### Step 13: Accept the reconstructed load for operational modeling

Once the reconstruction behaves consistently with the available measured demand pattern, it is accepted as the operational-load representation used in this study.

The acceptance criterion is practical rather than metrological.

In other words, the signal is accepted because it is physically plausible and consistent with the export, not because it is a direct calibrated bus-power measurement.

### Step 14: Resample to the model timestep

The operational-load signal is resampled to the timestep used by the dispatch model.

In the current setup:

- [data/preprocess.py](../data/preprocess.py) uses `RESAMPLE_MINUTES = 15`
- [main.jl](../main.jl) uses the matching `dt_minutes`

The resampled series is averaged to fixed 15-minute intervals.

### Step 15: Write the model input file

The final reduced model input is written as:

- [data/load_profile.csv](../data/load_profile.csv)

with columns:

- `timestep`
- `load_kw`
- `datetime`

This is the file consumed by the dispatch model in [main.jl](../main.jl).

## Current Validation Evidence

For the current March operational dataset, the reconstruction check gives:

- correlation between reconstructed load and known measured load: `0.986`
- reconstructed load mean / median: `56.9 / 23.0 kW`
- reconstructed load max: `237.4 kW`
- residual onboard load mean / median: `27.6 / 22.8 kW`
- share of residual values below `-5 kW`: `0.00%`

Interpretation:

- the reconstructed signal follows the measured propulsion and thruster activity pattern closely,
- the residual is mostly positive,
- and the unexplained component looks more like missing onboard demand than like a broken proxy.

## What Can Be Claimed Safely

The thesis can safely claim that:

- a direct total-load measurement was not available in the export,
- operational electrical load was therefore reconstructed from generator `Load percentage` and battery power,
- the reconstruction was checked against the available propulsion and thruster load signals,
- the reconstructed signal followed the measured demand pattern consistently,
- and the resulting profile was accepted as a practical operational-load representation for the dispatch study.

## What Should Not Be Claimed

The thesis should not claim that:

- the reconstructed signal is a directly measured full-vessel electrical load,
- the generator `Load percentage` proxy is identical to true generator terminal active power,
- the workflow provides a full decomposition of all onboard load categories,
- or the validation proves exact electrical accuracy in a metrological sense.

## Sufficiency Assessment

### Sufficient for the thesis purpose?

Yes, with explicit scope limits.

The process is sufficient for its intended purpose if that purpose is:

- to obtain a representative operational electrical-load profile for an exploratory dispatch optimization study,
- to preserve the overall vessel demand pattern seen in the telemetry,
- and to anchor the model in a realistic operational time series rather than a synthetic demand trace.

### Why it is sufficient

It is sufficient because:

- the required signals for a practical reconstruction are available,
- the missing total-load tag is replaced by a physically interpretable reconstruction,
- the proxy is checked against the measured load-side powers that do exist,
- the resulting residual behaves plausibly,
- and the final profile is aligned with the model timestep and format requirements.

### Why it is not stronger than that

It is not sufficient for:

- exact vessel-wide electrical auditing,
- exact auxiliary-load decomposition,
- exact per-generator electrical efficiency estimation,
- exact controller-threshold inference in `kW`,
- or broad claims about all operating seasons and duty modes.

Those stronger purposes would require better measurements, especially:

- direct per-generator active electrical power in `kW`,
- a trustworthy total bus-load signal,
- more explicit auxiliary-load tagging,
- and broader multi-window validation if stronger generalization claims are needed.

## Recommended Thesis Position

The safest and strongest thesis wording is:

"Because the available operational export did not include a trustworthy measured total electrical load or per-generator active power in `kW`, vessel electrical demand was reconstructed from the generator-controller `Load percentage` signals and measured battery power. The resulting load estimate was checked against the explicitly available propulsion and thruster inverter powers. As the reconstructed load followed the measured demand pattern closely and the remaining positive residual was consistent with unmetered onboard consumers, the reconstructed series was accepted as a practical operational-load representation for the dispatch study. The signal was then resampled to the model timestep and used as the optimization input profile."

## Remaining Gaps Worth Acknowledging

The Methods section can be written now, but these small gaps should still be acknowledged explicitly:

- the source system and export settings should be described at the level the thesis permits,
- the `385 kW` genset rating should be cited to the same source used elsewhere in the thesis,
- the operational-load representation should be described as reconstructed or inferred, not measured,
- and the validation should be presented as a consistency check, not a formal calibration.

## Bottom Line

Yes, the repository now contains enough material to write a complete and defensible Methods subsection for operational-load representation.

The process is sufficient for representing operational load in this thesis study, provided that the report frames it as:

- a practical reconstructed load profile,
- validated against the available measured load-side signals,
- and used for exploratory dispatch modeling within clearly stated limitations.
