# Operational Load Validation

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
- Bottom panel: generator 1 and generator 2 proxy output together with battery net power at the bus.

## Key Numbers

- Reconstructed load mean / median: 56.9 / 23.0 kW
- Reconstructed load min / max: 0.0 / 237.4 kW
- Raw reconstructed load min before clipping: -4.4 kW
- Residual other onboard load mean / median: 27.6 / 22.8 kW
- Battery charging max: 293.1 kW
- Battery discharging max: 104.1 kW

## Plotting Note

- Calendar dates are removed from the x-axis and shown as elapsed hours for a more anonymous presentation.
- The figure is reduced to two panels to keep the thesis Methods section focused on the reconstruction logic.
- Battery discharge is shown in red and battery charging is shown in green.
- Battery charge and discharge are shown as one signed bus-power signal around zero in the lower panel.
- The residual shading in the top panel visualizes load that is plausibly onboard but not explicitly metered in the export.