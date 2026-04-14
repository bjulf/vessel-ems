# Operational Profiles

This folder stores reconstructed operational load profiles derived from the vessel telemetry export.

Current file:

- `operational_load_profile_1min.csv`

This profile is intended for operational case comparison and timestep sensitivity work.
It uses the same reconstructed load logic as `data/preprocess.py`.
The source window is resampled to a continuous 1-minute grid, and the small number of missing 1-minute timestamps are filled by time interpolation after resampling.
