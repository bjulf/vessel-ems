# Next AI Prompt

Continue from [analysis/sfoc_handoff.md](./sfoc_handoff.md).

Important context:

- Operational-data files are already imported:
  - [data/v01.csv](../data/v01.csv)
  - [data/v01_clean.csv](../data/v01_clean.csv)
  - [data/preprocess.py](../data/preprocess.py)
- The generator `load %` proxy has been validated:
  - [analysis/power_proxy_validation.md](./power_proxy_validation.md)
- The reconstructed total-load figure exists:
  - [analysis/output/reconstructed_total_load.png](./output/reconstructed_total_load.png)
- The first-pass SFOC fit is complete:
  - [analysis/output/sfoc_fit_summary.txt](./output/sfoc_fit_summary.txt)
  - [analysis/output/sfoc_regime_breakpoints.csv](./output/sfoc_regime_breakpoints.csv)
  - [analysis/output/sfoc_regime_overlay.png](./output/sfoc_regime_overlay.png)

Current conclusions:

- Keep OEM as the baseline curve source.
- The `~1800 rpm` telemetry regime is strong enough for a provisional sensitivity-case curve.
- The `~1400 rpm` telemetry regime is too narrowly supported to replace OEM as a full curve.
- There is still no measured per-genset active `kW` signal in the current dataset.

Next task:

Implement a telemetry-based SFOC sensitivity case in [main.jl](../main.jl), using the `~1800 rpm` telemetry-supported bins from [analysis/output/sfoc_regime_breakpoints.csv](./output/sfoc_regime_breakpoints.csv), while keeping the OEM curve as the baseline. Then run or prepare the comparison workflow so OEM and telemetry cases can be compared on total fuel, starts/stops, battery usage, and dispatch pattern.
