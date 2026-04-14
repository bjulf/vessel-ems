# Load Percentage Proxy Validation

Date: 2026-04-13

## Purpose

This note checks whether the generator `Load percentage` signals from the generator Modbus registers behave like a sensible proxy for generator electrical output.

This matters because the current operational export does **not** contain measured per-genset active electrical power in `kW`.

That means the current SFOC and operating-mode analysis uses the fallback:

`generator power proxy = load_pct / 100 * 385`

where `385 kW` is the rated power of each genset.

The purpose of this validation is not to prove that `load %` is exactly equal to true per-genset electrical `kW`.

The purpose is to answer a narrower question:

- does the `load %` signal behave consistently with the rest of the electrical data in the export,
- or does it look physically inconsistent and therefore unsuitable even as a first-pass proxy.

## Data Used

Source file:

- [data/v01.csv](../data/v01.csv)

Related note:

- [analysis/signal_inventory.md](./signal_inventory.md)

Relevant exported signals:

- generator 1 `Load percentage`
- generator 2 `Load percentage`
- battery power
- propulsion inverter powers
- thruster inverter powers

Important limitation:

- the export does **not** contain a trustworthy per-genset active-power `kW` signal,
- the export also does **not** contain a useful full-bus or total-vessel load tag in this dataset,
- the `Microgrid > Power` tag exists in the raw file but is zero throughout the inspected period.

So the validation can only compare the generator-power proxy against the **known measured load-side powers that are present**.

## What Is Being Compared

The following quantities are constructed:

### 1. Generator Power Proxy

`genset_kw_proxy = (gen1_load_pct + gen2_load_pct) / 100 * 385`

This is the inferred total generator electrical output from the two genset `load %` signals.

### 2. Proxy Supply at the Bus

`supply_kw_proxy = genset_kw_proxy + battery_power`

Sign convention used:

- `battery_power > 0` means the battery is discharging and supplying the bus,
- `battery_power < 0` means the battery is charging and consuming power from the bus.

This is the same convention already used in [data/preprocess.py](../data/preprocess.py).

### 3. Known Measured Load

`known_load_kw = propulsion inverter powers + thruster inverter powers`

This is **not** the full vessel load.

It is only the sum of the load-side powers that are actually present and nonzero in the export.

### 4. Residual Other Load

`other_load_kw = supply_kw_proxy - known_load_kw`

This residual should be interpreted as the part of vessel load that is **not** captured by the exported propulsion/thruster tags.

Likely examples:

- hotel load
- auxiliary services
- other onboard electrical consumers
- instrumentation and miscellaneous vessel loads

For an inventory of which signals are explicit, zero-only, or missing in this export, see [analysis/signal_inventory.md](./signal_inventory.md).

If the proxy is reasonable, this residual should usually be:

- positive or near zero,
- fairly stable in normal operating windows,
- not strongly negative for long periods.

If the proxy were clearly wrong, we would expect frequent large negative residuals, meaning the inferred supply would fail to cover even the known measured loads.

## Results

Generated outputs:

- [analysis/output/power_proxy_validation.png](../analysis/output/power_proxy_validation.png)
- [analysis/output/power_proxy_validation_summary.txt](../analysis/output/power_proxy_validation_summary.txt)

Key numbers:

- rows: `3959`
- active rows used in comparison: `3958`
- correlation between `supply_kw_proxy` and `known_load_kw`: `0.986`
- battery power min / max: `-293.1 / 104.1 kW`
- battery charging rows / discharging rows: `1114 / 2840`
- residual `other_load_kw` mean / median: `27.6 / 22.8 kW`
- residual `other_load_kw` p10 / p90: `18.4 / 51.8 kW`
- residual `other_load_kw` min / max: `-4.4 / 125.3 kW`
- share with residual below `-5 kW`: `0.00%`

## How To Read the Figure

### Top Panel

This panel compares:

- `Generator proxy from load %`
- `Proxy supply`
- `Known measured load`

It also shows two explicit battery contributions:

- green band: `battery discharge`
- red band: `battery charging`

The grey shaded gap between `Proxy supply` and `Known measured load` is the estimated `other onboard load`.

What we want to see:

- the proxy supply should rise and fall together with the known measured load,
- the gap between `Generator proxy from load %` and `Proxy supply` should show where battery power is entering or leaving the bus,
- the proxy supply should usually stay above the known measured load,
- the gap should look like a plausible missing-load component rather than random inconsistency.

How to interpret the battery shading:

- if the green band is present, the battery is discharging and adding power on top of the generator proxy,
- if the red band is present, the battery is charging and absorbing part of the generator output,
- this makes it easier to distinguish between:
  - power that goes into or comes from the battery,
  - and the remaining power that must be going to other onboard consumers not directly metered in the export.

### Middle Panel

This is a pointwise scatter plot of:

- x-axis: `known measured load`
- y-axis: `proxy supply`

The dashed diagonal is the `1:1` line.

If the proxy is sensible and there are unmetered onboard loads, most points should sit:

- close to the line,
- but slightly above it.

That is exactly what happens here.

### Bottom Panel

This shows the distribution of:

`other_load_kw = proxy supply - known measured load`

This is the estimated unmetered onboard load.

What we want to see:

- mostly positive values,
- not many strongly negative values,
- a range that looks plausible for hotel and auxiliary loads.

That is also what happens here.

## Interpretation

The validation supports the following conclusion:

- the generator `Load percentage` signals behave like a sensible proxy for generator electrical output in this dataset.

Why:

- the proxy supply tracks the known measured load-side powers very closely,
- the residual is mostly positive,
- the residual magnitude is plausible as an unmetered onboard-load bucket,
- the balance almost never goes negative in a way that would suggest a broken proxy or wrong battery sign convention.

## What This Does Prove

- the Modbus generator `load %` values are internally consistent with the rest of the export,
- the current use of `load % * 385 kW` is reasonable for exploratory screening and first-pass analysis,
- the battery sign convention used in preprocessing is consistent with the observed electrical balance.

## What This Does Not Prove

- that `load %` is exactly equal to true measured per-genset active electrical power,
- that the PLC threshold logic uses this same quantity,
- that a threshold such as `< 90 kW` can be inferred exactly from this proxy,
- that OEM-efficiency comparisons are exact on the power axis.

Those stronger claims still require a real per-genset active-power `kW` signal, or direct supplier confirmation of how `Load percentage` is defined in the generator controller.

## Practical Conclusion

For the current thesis workflow:

- use `load % * 385 kW` as a defensible **proxy** for exploratory SFOC and operating-regime analysis,
- do **not** describe it as measured per-genset electrical power,
- keep the limitation explicit whenever interpreting exact power thresholds or exact alignment with OEM curves.

## Recommended Thesis Wording

"Because the operational export did not include measured per-genset active electrical power, generator output was approximated from the generator-controller `Load percentage` signal and rated power. A consistency check against battery power and measured propulsion/thruster loads showed that the resulting proxy tracked the electrical demand pattern closely, with the remaining positive residual interpreted as unmetered hotel and auxiliary loads. The proxy was therefore considered suitable for exploratory analysis, while still being treated as an approximation rather than a direct power measurement."
