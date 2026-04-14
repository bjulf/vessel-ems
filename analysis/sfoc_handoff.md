# SFOC Workstream Handoff

Date: 2026-04-13

## Purpose

This note is a handoff summary for continuing the telemetry-based SFOC work in another AI session.

It records:

- what has already been established,
- what files and scripts now exist,
- what conclusions are currently defensible,
- and what the next step should be.

## Current Repository State Relevant to SFOC

Operational-data files have been brought into the working branch from the `operational_data` branch without performing a full branch merge:

- [data/v01.csv](../data/v01.csv)
- [data/v01_clean.csv](../data/v01_clean.csv)
- [data/preprocess.py](../data/preprocess.py)

Important analysis files created during this work:

- [analysis/sfoc_assessment.md](./sfoc_assessment.md)
- [analysis/sfoc_screen.py](./sfoc_screen.py)
- [analysis/sfoc_fit.py](./sfoc_fit.py)
- [analysis/output/sfoc_fit_summary.txt](./output/sfoc_fit_summary.txt)
- [analysis/output/sfoc_regime_breakpoints.csv](./output/sfoc_regime_breakpoints.csv)
- [analysis/output/sfoc_regime_overlay.png](./output/sfoc_regime_overlay.png)
- [analysis/signal_inventory.md](./signal_inventory.md)
- [analysis/power_proxy_validation.md](./power_proxy_validation.md)
- [analysis/output/power_proxy_validation.png](./output/power_proxy_validation.png)
- [analysis/output/power_proxy_validation_summary.txt](./output/power_proxy_validation_summary.txt)
- [analysis/data_extraction_process.md](./data_extraction_process.md)
- [analysis/output/reconstructed_total_load.png](./output/reconstructed_total_load.png)
- [analysis/output/reconstructed_total_load.md](./output/reconstructed_total_load.md)

## What Has Been Established

### 1. The Operational Dataset Is Usable for Exploratory SFOC Work

From `v01_clean.csv`:

- rows: `3959`
- time range: `2026-03-01 00:00:00` to `2026-03-03 18:00:00`
- dominant cadence: `1 minute`
- only a few `2 minute` gaps

This is good enough for first-pass regime screening and steady-state filtering.

### 2. The Dataset Contains the Core SFOC Signals

Available per genset:

- `Fuel Rate`
- `Load percentage`
- `Speed`
- `Torque percentage`

Not available:

- measured per-genset active electrical `kW`
- explicit generator power setpoint
- explicit HPU load
- trustworthy full-bus total-load tag

### 3. The Generator `load %` Signal Is a Defensible Power Proxy

This was checked in [analysis/power_proxy_validation.md](./power_proxy_validation.md).

Main result:

- correlation between proxy supply and known measured propulsion/thruster load: `0.986`
- residual other onboard load is mostly positive and plausible
- negative residuals below `-5 kW`: `0.00%`

Working conclusion:

- `load % * 385 kW` is acceptable for exploratory analysis,
- but it must still be described as a proxy, not measured per-genset power.

### 4. Two Real Speed Regimes Exist

The operational data show two sustained operating clusters:

- `~1400 rpm`
- `~1800 rpm`

This is not just startup/shutdown behavior.

Sustained segments `>= 30 min` show:

- multiple long `~1400 rpm` runs
- multiple long `~1800 rpm` runs

So the low-speed mode is a real operating mode, not only a transient artifact.

### 5. The Speed Regimes Map to Different Power Ranges

Using the current power proxy:

- below about `190-200 kW`, the gensets are usually at `~1400 rpm`
- above about `200 kW`, they are effectively always at `~1800 rpm`

This is only approximate because the dataset lacks measured per-genset `kW`.

### 6. The OEM Datasheet Does Not Suggest That `1800 rpm` Is the Most Efficient Setpoint

From [VolvoPentaMHVG.pdf](/c:/Users/bulve/OneDrive/master/Datasheets/Generator/VolvoPentaMHVG.pdf):

For the `385 kWe` package, the listed efficient points are around:

- `192 kWe / 1300 rpm` -> `193 g/kWh`
- `288 kWe / 1400 rpm` -> `191 g/kWh`
- `310 kWe / 1400 rpm` -> `191 g/kWh`
- rated point around `385 kWe / 1900 rpm` -> `198 g/kWh`

Working interpretation:

- the OEM information points to the low-speed region around `1300-1400 rpm` as the efficient operating region over a broad mid-load range,
- so sustained `~1800 rpm` operation at medium load is likely a control or operability choice rather than the fuel-optimal point.

### 7. First-Pass Telemetry SFOC Fit Has Been Completed

This is documented in:

- [analysis/output/sfoc_fit_summary.txt](./output/sfoc_fit_summary.txt)
- [analysis/output/sfoc_regime_breakpoints.csv](./output/sfoc_regime_breakpoints.csv)
- [analysis/output/sfoc_regime_overlay.png](./output/sfoc_regime_overlay.png)

Main result:

#### `~1800 rpm` regime

- filtered points: `390`
- power range: `194.4 to 302.2 kW`
- load range: `50.5 to 78.5 %`
- median SFOC: about `211.9 g/kWh`
- supported bins:
  - `50-60%`
  - `60-70%`
  - `70-80%`
- judgment: strong enough for a provisional sensitivity-case curve

#### `~1400 rpm` regime

- filtered points: `398`
- power range: `75.8 to 196.2 kW`
- load range: `19.7 to 51.0 %`
- median SFOC: about `180.9 g/kWh`
- supported bins:
  - mostly `40-50%`
  - some `50-60%`
- supported load-span: only `2.3` percentage points across supported bins
- judgment: too narrow for a defensible full regime-wide curve

### 8. Current SFOC Conclusion

The operational data are strong enough to support:

- a two-regime interpretation,
- a provisional telemetry-derived sensitivity case,
- and a credible `~1800 rpm` telemetry curve candidate.

The operational data are **not** yet strong enough to support:

- replacing OEM as the main source,
- or fitting a defensible full `~1400 rpm` regime curve.

Current defensible position:

- keep OEM as the baseline curve source,
- use telemetry as a sensitivity-case or exploratory comparison,
- especially for the `~1800 rpm` regime.

## What Has Been Established About Total Load

A reconstructed total electrical load figure has also been created:

- [analysis/output/reconstructed_total_load.png](./output/reconstructed_total_load.png)
- [analysis/output/reconstructed_total_load.md](./output/reconstructed_total_load.md)

Definition:

`reconstructed_total_load_kw = gen1_load_pct/100*385 + gen2_load_pct/100*385 + battery_power`

This is useful for the thesis as a reconstructed load profile, not as a directly measured total-load signal.

## What Has Not Been Resolved

These remain the main unresolved issues:

- no measured per-genset active electrical `kW`
- no explicit generator power setpoint tag
- no explicit HPU power tag
- no useful nonzero total-bus-load measurement
- no confirmation yet whether the `Fuel Rate` signal is measured or controller-estimated

These gaps do not block exploratory work, but they do limit how strong the final thesis claims can be.

## Recommended Next Step

The next best step is:

### Build a Telemetry Sensitivity Case in the Optimizer

Practical recommendation:

- keep the existing OEM curve as the baseline in [main.jl](../main.jl)
- add one alternative telemetry-based curve set as a comparison case

Suggested approach:

1. Use the `~1800 rpm` telemetry-supported bins directly as a provisional curve candidate.
2. Keep the `~1400 rpm` regime on OEM values for now, or use only a very conservative local approximation around the observed `~48-50%` load range.
3. Run the optimizer with:
   - OEM case
   - telemetry sensitivity case
4. Compare:
   - total fuel
   - starts/stops
   - battery behavior
   - dispatch pattern

This would answer the next important thesis question:

- does the curve source materially change dispatch conclusions?

## Good Continuation Prompt for Another AI

If another AI instance should continue from here, a good prompt is:

"Continue from [analysis/sfoc_handoff.md](./sfoc_handoff.md). The operational-data files are already imported. The generator `load %` proxy has been validated, the reconstructed total-load figure exists, and the first-pass SFOC fit is complete. Keep OEM as baseline. Next, implement a telemetry-based SFOC sensitivity case in `main.jl`, using the `~1800 rpm` telemetry-supported bins from `analysis/output/sfoc_regime_breakpoints.csv`, and compare optimizer outputs against the OEM baseline."

## Short One-Paragraph Handoff

The operational dataset is now in the working branch and has been screened successfully. The generator `load %` signal behaves like a sensible power proxy when checked against battery power and measured propulsion/thruster loads. The data show two real speed regimes around `1400 rpm` and `1800 rpm`. A first-pass telemetry SFOC fit shows that the `~1800 rpm` regime has enough load-span and data density for a provisional sensitivity-case curve, while the `~1400 rpm` regime is too narrowly concentrated around about `48-50%` load to support a defensible full curve. OEM therefore remains the baseline, while telemetry is ready to be used as a comparison/sensitivity case, especially for the `~1800 rpm` regime.
