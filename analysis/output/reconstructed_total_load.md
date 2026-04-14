# Reconstructed Total Electrical Load

Source: [v01.csv](../data/v01.csv)

## Definition

`reconstructed_total_load_kw = gen1_load_pct/100*385 + gen2_load_pct/100*385 + battery_power`

This is a reconstructed bus-load estimate, not a directly measured total-load signal.

## Why This Makes Sense

- The dataset does not contain a useful nonzero total-bus-load tag.
- The generator `load %` proxy has already passed an internal consistency check against the explicit propulsion and thruster loads.
- Adding battery power accounts for power being supplied by or absorbed into the battery at the bus.

## What The Figure Shows

- Top panel: reconstructed total load, known measured propulsion/thruster load, and residual other onboard load.
- Middle panel: generator 1 proxy output, generator 2 proxy output, total genset proxy, and reconstructed total load.
- Bottom panel: battery power shown as a signed bus-power signal around zero, with discharge above zero and charging below zero.

## Key Numbers

- Reconstructed load mean / median: 56.9 / 23.0 kW
- Reconstructed load min / max: 0.0 / 237.4 kW
- Raw reconstructed load min before clipping: -4.4 kW
- Residual other onboard load mean / median: 27.6 / 22.8 kW
- Battery charging max: 293.1 kW
- Battery discharging max: 104.1 kW

## Plotting Note

- Battery charge and discharge are now shown with the same colors throughout the figure.
- The battery is plotted as a signed power signal around zero in the bottom panel.
- This avoids the earlier visual impression that charging and discharging were happening simultaneously.
- If both colors seemed to appear near the same time previously, that was a plotting artifact at state transitions rather than evidence of simultaneous charge and discharge.