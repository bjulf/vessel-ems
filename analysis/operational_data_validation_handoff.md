# Operational Data Validation Handoff

Date: 2026-04-14

## Purpose

This note records the current decisions and recommended next steps for the thesis treatment of operational data validation.

It is intended as a clean handoff for continuing the work in another AI thread without having to reconstruct the discussion.

The main conclusion is that the thesis should separate:

- general operational data / load reconstruction validation,
- and the more specific telemetry-based SFOC assessment.

The current `power_proxy_validation` plot is technically useful, but it is not the clearest main-text thesis figure for this purpose.

## Core Decision

Do not force the current proxy-validation scatter/histogram figure into the SFOC subsection.

Instead:

1. Create a more general Methods subsection for operational data validation or operational load validation.
2. Use a time-series style figure there to show how the operational electrical load was reconstructed.
3. Let the SFOC subsection refer back to that general validation step when introducing the generator power proxy.
4. Keep the SFOC-specific figure in Results focused on telemetry regime behavior and OEM comparison.

## Recommended Report Structure

### General Methods subsection

Suggested purpose:

- explain how operational electrical load was reconstructed,
- explain which measured signals existed and which did not,
- show that the reconstructed load follows the known vessel demand pattern,
- justify the use of generator `load %` as a practical proxy input.

Suggested title:

- `Operational data validation`
- or `Operational load validation`

### SFOC Methods subsection

This subsection should not repeat the full operational-load validation story.

It should instead say:

- measured per-generator electrical power in `kW` was not available,
- generator power was therefore approximated from `load % * 385`,
- this proxy was consistent with the operational load reconstruction method described earlier,
- and was then used for exploratory SFOC screening only.

### Results subsection

Use the SFOC scatter comparison figure here, not the proxy-validation figure.

## Why The Current Proxy-Validation Figure Is Not Ideal

The current figure:

- is technically correct,
- but it is still focused on an internal diagnostic question,
- and it does not communicate the broader reconstruction logic very clearly to a thesis reader.

The vertical pile-up near zero measured propulsion/thruster power is also distracting, even though it is not wrong.

For the thesis, the more important point is:

- the total electrical load had to be reconstructed from available signals,
- because a trustworthy measured total-load signal was not available.

That is easier to explain with a time-series reconstruction plot than with a scatter-plus-histogram diagnostic.

## Recommended New Figure For General Operational Data Validation

Use a new time-series figure instead of the current `power_proxy_validation_thesis.png`.

### Figure purpose

Show:

- how reconstructed electrical load is formed,
- how it compares with the explicitly measured propulsion and thruster load,
- and how generator proxy and battery power contribute to the reconstructed vessel load.

### Recommended layout

Two panels are likely enough.

#### Top panel

Plot:

- reconstructed total electrical load,
- measured propulsion and thruster load,
- optional shaded residual onboard load.

Interpretation:

- the reconstructed load should follow the same operating pattern as the measured propulsion/thruster load,
- the positive difference is consistent with onboard loads that are not explicitly measured in the export.

#### Bottom panel

Plot:

- generator 1 proxy power,
- generator 2 proxy power,
- battery power as a signed signal around zero.

Interpretation:

- this shows how the reconstructed load is supplied,
- and makes the load reconstruction process physically understandable.

### Optional third panel

Only add a third panel if needed for readability.

Possible third panel:

- battery power alone.

But this is likely not necessary if the bottom panel is kept visually simple.

## Plot Specification For Operational Load Validation Figure

### Dataset

Use:

- [data/v01.csv](../data/v01.csv)

This is enough for the current operational validation figure.

### Data preparation

Use the same preparation logic already implemented in:

- [analysis/reconstructed_total_load.py](./reconstructed_total_load.py)
- [analysis/power_proxy_validation.py](./power_proxy_validation.py)

The method is:

1. Read `v01.csv`.
2. Convert relevant columns to numeric.
3. Forward-fill sparse generator `Load percentage` signals.
4. Fill remaining missing generator load values with zero.
5. Fill missing battery power with zero.
6. Fill missing measured load-side powers with zero and clip them at zero.

### Definitions

Generator power proxy:

`gen_kw_proxy = load_pct / 100 * 385`

Combined generator proxy:

`genset_kw_proxy = gen1_kw_proxy + gen2_kw_proxy`

Reconstructed total load:

`reconstructed_total_load_kw = genset_kw_proxy + battery_power`

Measured load-side reference:

`known_measured_load_kw = propulsion inverter powers + thruster inverter powers`

Residual onboard load:

`other_onboard_load_kw = reconstructed_total_load_kw - known_measured_load_kw`

### Plot style

Keep the figure simple and readable in the PDF.

Recommended colors:

- reconstructed total load: dark teal
- measured propulsion/thruster load: muted orange or brown
- residual onboard load: light gray shading
- generator 1 proxy: light blue
- generator 2 proxy: darker blue
- battery discharge: green
- battery charging: red

### What to avoid

Do not overload the figure with:

- correlation values,
- residual statistics,
- multiple annotation boxes,
- too many legends.

This figure should explain the reconstruction logic, not the full diagnostic statistics.

## Current SFOC Results Figure Recommendation

For the SFOC Results subsection, keep using the new thesis-style scatter figure:

- [analysis/sfoc_cases/full_combined_all_windows/sfoc_regime_thesis_scatter.png](./sfoc_cases/full_combined_all_windows/sfoc_regime_thesis_scatter.png)

This figure already communicates the right point:

- two operating regimes exist,
- telemetry points have real spread,
- supported medians can be seen directly,
- and the OEM mismatch is visible.

Do not replace this with the older clean-line comparison in the main text unless a cleaner but less data-rich presentation is explicitly preferred.

## Methods Text Guidance

For the general operational validation subsection, the text should emphasize:

- the dataset does not contain a trustworthy measured total-load signal,
- operational electrical load was therefore reconstructed from generator `load %` and battery power,
- the reconstruction follows the measured propulsion and thruster activity pattern,
- and the remaining difference is plausibly explained by onboard loads that are not explicitly measured.

For the SFOC subsection, the text should emphasize:

- measured per-generator `kW` was not available,
- a power proxy was therefore required,
- the proxy follows from the earlier operational-load reconstruction method,
- and it was used only for exploratory SFOC screening and comparison.

## Current Status Of New Thesis Figures

The following thesis-oriented figures were already generated during this thread:

- [analysis/output/power_proxy_validation_thesis.png](./output/power_proxy_validation_thesis.png)
- [analysis/sfoc_cases/full_combined_all_windows/sfoc_regime_thesis_scatter.png](./sfoc_cases/full_combined_all_windows/sfoc_regime_thesis_scatter.png)

Current judgment:

- `power_proxy_validation_thesis.png` is still more diagnostic than explanatory and is not the preferred main-text thesis figure.
- `sfoc_regime_thesis_scatter.png` is close to thesis-ready and is currently the preferred Results figure for the telemetry SFOC discussion.

## Should More Data Be Added For Operational Load Validation?

Probably not, unless a broader validation claim is needed.

### Current recommendation

For the operational load validation figure, the existing `v01.csv` dataset is sufficient if the purpose is:

- to show the reconstruction method,
- to show that the reconstructed load follows measured vessel activity,
- and to justify the operational-data workflow used in the thesis.

### Add more data only if one of these is true

Add more datasets only if the thesis text wants to claim that the reconstruction method has been checked across:

- several seasons,
- several operating modes,
- or clearly different vessel duty profiles.

If that broader claim is not needed, using the current March dataset is enough and keeps the method section simpler.

### Safe thesis position

The safest wording is:

- the reconstruction method was assessed on the available operational export,
- it behaved consistently with the known measured load-side powers,
- and it was therefore accepted for exploratory operational analysis.

That wording does not require expanding the validation dataset.

## Recommended Next Step In Another Thread

In the next thread, focus on creating a new figure for the general operational data validation subsection.

Suggested task:

1. Start from `analysis/reconstructed_total_load.py`.
2. Simplify it into a thesis-oriented figure with two panels.
3. Save the result under a new name, for example:
   - `analysis/output/operational_load_validation.png`
4. Keep the current SFOC thesis scatter figure as the Results figure candidate.

## Short Continuation Prompt

Use this in the next AI thread:

> Continue from `analysis/operational_data_validation_handoff.md`. We are working on the thesis report and need a cleaner general Methods figure for operational data validation. Do not touch the report files yet. Start from `analysis/reconstructed_total_load.py` and help design a two-panel thesis figure that shows reconstructed electrical load, measured propulsion/thruster load, residual onboard load, generator proxy contribution, and battery power in a clear way. Keep the SFOC Results figure based on `analysis/sfoc_cases/full_combined_all_windows/sfoc_regime_thesis_scatter.png`.
