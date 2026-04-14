# March SFOC Case Comparison

This note compares the preserved March SFOC cases under `analysis/sfoc_cases/`.

## Inputs

- Baseline March case:
  - `data/v01_clean.csv`
- New March window:
  - `analysis/sfoc_datasets/march_window_2026-03-04_2026-03-06.csv`
- Combined March case:
  - both datasets above

## Case Folders

- `analysis/sfoc_cases/march_v01_baseline`
- `analysis/sfoc_cases/march_window_2026_03_04_to_03_06`
- `analysis/sfoc_cases/march_combined_v01_plus_window`

## Main Comparison

### Baseline March

- steady points: `788`
- `~1800 rpm`: `390` points
- `~1400 rpm`: `398` points
- supported `~1800 rpm` bins:
  - `50-60%`
  - `60-70%`
  - `70-80%`
- supported `~1400 rpm` bins:
  - `40-50%`
  - `50-60%`
- `~1400 rpm` supported span: `2.3` percentage points

### New March Window

- steady points: `918`
- `~1800 rpm`: `826` points
- `~1400 rpm`: `92` points
- supported `~1800 rpm` bins:
  - `40-50%`
  - `50-60%`
  - `60-70%`
  - `70-80%`
- supported `~1400 rpm` bins:
  - `40-50%`
  - `50-60%`
- `~1400 rpm` supported span: `6.5` percentage points

### Combined March

- steady points: `1706`
- `~1800 rpm`: `1216` points
- `~1400 rpm`: `490` points
- supported `~1800 rpm` bins:
  - `40-50%`
  - `50-60%`
  - `60-70%`
  - `70-80%`
- supported `~1400 rpm` bins:
  - `40-50%`
  - `50-60%`
- `~1400 rpm` supported span: `2.8` percentage points

## Interpretation

- The new March window clearly strengthens the `~1800 rpm` case.
- The new March window adds more low-speed points, but the `~1400 rpm` telemetry is still concentrated around roughly `45-50%` load.
- Combining the two March datasets does not create a defensible regime-wide `~1400 rpm` curve.
- The main defensible conclusion remains unchanged:
  - keep OEM as baseline
  - use telemetry as a sensitivity case
  - treat the `~1800 rpm` telemetry curve as the strongest telemetry-supported result

## OEM Comparison

Across all three March cases:

- `~1800 rpm` telemetry remains above OEM by roughly `+8%` to `+14%`
- `~1400 rpm` telemetry remains below OEM by roughly `-6%` to `-10%` in SFOC terms
- the mismatch remains visible in fuel-versus-power as well, not only after converting to `g/kWh`

## Tracking

- Preserved case outputs live in `analysis/sfoc_cases/`
- Repo-owned fetched window lives in `analysis/sfoc_datasets/`
- Legacy one-off outputs in `analysis/output/` were intentionally left unchanged
