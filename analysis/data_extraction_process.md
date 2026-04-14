# Operational Data Extraction Process

Date: 2026-04-13

## Purpose

This note documents the practical extraction and preparation workflow used for the operational dataset in this repository.

It is written to support thesis-method writing.

The goal is to describe:

- where the data came from,
- which signals were exported,
- how the raw export was cleaned,
- how the active analysis tables were constructed,
- and which assumptions and limitations were introduced along the way.

This note is not a claim that the export is a fully validated measurement system. It is a transparent record of how the available operational data were turned into analysis-ready inputs.

## Files Used in the Current Workflow

Raw export:

- [data/v01.csv](../data/v01.csv)

Cleaned export:

- [data/v01_clean.csv](../data/v01_clean.csv)

Operational preprocessing script:

- [data/preprocess.py](../data/preprocess.py)

Related analysis notes:

- [analysis/signal_inventory.md](./signal_inventory.md)
- [analysis/power_proxy_validation.md](./power_proxy_validation.md)
- [analysis/sfoc_assessment.md](./sfoc_assessment.md)

## Source of the Data

The operational data were exported from the customer data system as timestamped CSV files.

In the current repository state, the main operational extract is:

- `v01.csv`

This file contains a time series of vessel position, battery signals, generator-controller signals, and selected propulsion and thruster power signals.

The export used in the current analysis spans:

- `2026-03-01 00:00:00` to `2026-03-03 18:00:00`

The dominant sample interval in the current extract is:

- `1 minute`

with a small number of `2 minute` gaps.

## Step 1: Export Raw Operational Data

The first step is to export raw operational data to CSV without modifying the original export file afterward.

Recommended rule:

- keep the raw export immutable,
- save it under `data/`,
- and perform all cleaning and derived calculations in separate files or scripts.

For the current workflow, the raw export file is:

- [data/v01.csv](../data/v01.csv)

The thesis should describe this as the original operational export used for analysis.

## Step 2: Identify the Signals Present in the Export

Before any cleaning or modeling, the export must be inspected to determine which signals are actually available.

For the current dataset, the useful signals fall into four groups:

### Generator Signals

- generator 1 fuel rate
- generator 1 load percentage
- generator 1 speed
- generator 1 torque percentage
- generator 2 fuel rate
- generator 2 load percentage
- generator 2 speed
- generator 2 torque percentage

### Battery Signals

- battery power
- battery state of charge

### Explicitly Measured Load-Side Signals

- propulsion port inverter power
- propulsion starboard inverter power
- thruster port aft inverter power
- thruster port forward inverter power

### Context Signals

- latitude
- longitude
- speed over ground

Some signals are present in the raw export schema but are zero throughout the current dataset, for example:

- microgrid power
- shore connection power
- shore-connection inverter power
- some thruster-related aggregate tags

These are therefore not usable in this specific extract.

For the detailed signal grouping, see [analysis/signal_inventory.md](./signal_inventory.md).

## Step 3: Preserve the Raw Export and Create a Cleaned Copy

The raw file is not edited directly.

Instead, the cleaning script [data/preprocess.py](../data/preprocess.py) reads `v01.csv`, removes columns that are always zero, and writes:

- [data/v01_clean.csv](../data/v01_clean.csv)

This cleaned file keeps the same row-level time series but removes signals that do not contribute information in the current export.

This step improves readability and reduces the risk of using empty signals by mistake.

## Step 4: Handle Sparse Generator Register Updates

The generator `Load percentage` tags are not updated on every row in the raw export.

That means the values appear sparsely in the CSV, even though they are intended to describe the ongoing generator operating state.

To make the signal usable as a time series, the preprocessing script applies:

- forward-fill on generator 1 load percentage,
- forward-fill on generator 2 load percentage,
- and fills remaining missing values with zero.

This is implemented in [data/preprocess.py](../data/preprocess.py).

The rationale is:

- the generator controller updates the register intermittently,
- but the reported value is intended to remain valid until the next update,
- so forward-filling is more appropriate than treating intermediate missing rows as true zero output.

This assumption should be stated clearly in the thesis.

## Step 5: Construct a Reconstructed Total Electrical Load

The current export does not contain a useful nonzero total-bus-load tag.

Therefore, a reconstructed total load is built from the supply-side signals.

The reconstruction used in this project is:

`reconstructed_total_load_kw = gen1_load_pct / 100 * 385 + gen2_load_pct / 100 * 385 + battery_power`

where:

- `385 kW` is the rated power of each genset,
- positive battery power means battery discharge to the bus,
- negative battery power means battery charging from the bus.

This reconstructed total load is used because:

- the generator `load %` signal is available for both units,
- battery power is available,
- and the explicit load-side export is incomplete.

This quantity is a reconstructed estimate, not a directly measured total load.

## Step 6: Validate the Generator Load-Percentage Proxy

Because measured per-genset active electrical power in `kW` is not available in the current export, the `load % * rated power` calculation must be checked before it is used in analysis.

The validation performed in this repository compares:

- proxy generator supply plus battery power,

against:

- the explicitly measured propulsion and thruster powers in the export.

The remaining difference is interpreted as:

- other onboard load,
- such as hotel load, auxiliary services, or unmetered electrical consumers.

This validation is documented in:

- [analysis/power_proxy_validation.md](./power_proxy_validation.md)

The current result is that the proxy behaves consistently with the rest of the export and is reasonable for exploratory analysis, while still remaining an approximation rather than a direct `kW` measurement.

## Step 7: Build an Active Load Profile for the Dispatch Model

The optimization model expects a compact time-series file with:

- timestep
- load in `kW`
- datetime

The preprocessing script therefore resamples the reconstructed total load to a fixed timestep and writes:

- [data/load_profile.csv](../data/load_profile.csv)

In the current setup:

- the resampling interval is `15 minutes`

This is controlled in [data/preprocess.py](../data/preprocess.py) through:

- `RESAMPLE_MINUTES = 15`

This value must stay aligned with:

- `dt_minutes` in [main.jl](../main.jl)

as noted in [AGENTS.md](../AGENTS.md).

The resampled `load_profile.csv` is the file used directly by the dispatch optimization model.

## Step 8: Use the Cleaned Export for Exploratory Analysis

The cleaned file `v01_clean.csv` is then used for exploratory analyses such as:

- checking available signals,
- identifying operating regimes,
- validating the generator load-percentage proxy,
- screening the fuel-rate data for SFOC analysis,
- and creating supporting figures.

This separation is important:

- `v01_clean.csv` is the analysis table for exploratory work,
- `load_profile.csv` is the reduced model input for the optimizer.

## Step 9: Interpret Missing Load Categories Carefully

Not all vessel loads are explicitly measured in the current export.

In particular, the current dataset does not provide explicit tags for:

- HPU loads,
- hotel load,
- many auxiliary loads,
- or a trustworthy full-bus total-load measurement.

That means these loads are not absent physically. They are only absent as explicit measurements in the export.

In the current workflow they are therefore captured indirectly through:

- the residual difference between reconstructed supply and known measured propulsion/thruster loads.

This point is important in the thesis, because it explains why a reconstructed total load is needed at all.

## Step 10: Document the Main Assumptions Explicitly

The current extraction and preparation process depends on several assumptions that should be stated clearly in the thesis.

### Assumption 1

Generator `Load percentage` can be used as a proxy for generator electrical output when scaled by rated power.

### Assumption 2

Sparse `Load percentage` updates are valid until the next update, so forward-filling is appropriate.

### Assumption 3

Battery power sign is interpreted as:

- positive = discharge to the bus
- negative = charging from the bus

### Assumption 4

The reconstructed total load is an estimate of bus demand, not a direct metered total-load measurement.

### Assumption 5

Loads not explicitly present in the export, such as HPU and hotel load, are represented indirectly through the residual onboard-load component.

## Step 11: State the Main Limitations

The current extraction process is useful, but it has real limitations.

### Limitation 1

The dataset does not include measured per-genset active electrical `kW`.

### Limitation 2

The dataset does not include a useful full-bus total-load tag.

### Limitation 3

Some physically important onboard loads are not explicitly tagged in the current export.

### Limitation 4

The current export is `1 minute` data, not a faster raw stream such as `15 s`.

### Limitation 5

The generator-controller `load %` quantity may not be identical to true terminal active power, even if it is a good practical proxy.

These limitations do not invalidate the analysis. They define the strength of the claims that can be made from it.

## Recommended Thesis Description

The process can be described in the thesis in language like this:

"Operational data were exported from the customer data system as timestamped CSV files. The raw export was preserved, and a cleaned analysis table was created by removing signals that were zero throughout the observation period. Because the export did not include measured per-genset active electrical power, generator output was approximated from the generator-controller `Load percentage` signal and the rated generator power. Sparse `Load percentage` updates were forward-filled between register updates. A reconstructed total electrical load was then formed by combining the inferred generator output with the measured battery power. This reconstructed load was validated against the explicitly available propulsion and thruster power signals, with the remaining positive residual interpreted as unmetered onboard loads such as hotel and auxiliary demand. The resulting time series was resampled to the model timestep and used as input to the dispatch optimization model."

## Practical Summary

The full extraction workflow used in this repository is:

1. Export raw customer data to CSV.
2. Preserve the raw export unchanged.
3. Inspect the schema and identify usable signals.
4. Remove always-zero columns into a cleaned copy.
5. Forward-fill sparse generator `load %` signals.
6. Reconstruct total electrical load from generator `load %` and battery power.
7. Validate the generator-power proxy against the known measured load-side powers.
8. Resample the reconstructed load to the model timestep.
9. Save the reduced load profile for optimization.
10. Use the cleaned export for exploratory regime and SFOC analysis.
