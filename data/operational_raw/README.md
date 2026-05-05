# Operational Raw Telemetry

This folder stores canonical raw telemetry exports used to build operational
load profiles in `data/operational_profiles/`.

The 3-day source remains at `data/v01.csv` for compatibility with existing
analysis notes and scripts. The 6-day exports are copied here from the earlier
working case folder under `analysis/operational_load_cases/`.

Use `data/preprocess.py` to regenerate the operational 1-minute and 15-minute
profiles from these raw inputs.
