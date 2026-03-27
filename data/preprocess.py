"""Preprocesses operational data from v01.csv:
  1. Creates v01_clean.csv  — always-zero columns removed
  2. Creates load_profile.csv — resampled electrical load for the dispatch model

To change the time resolution, update RESAMPLE_MINUTES below and re-run.
The same value must be reflected as dt_minutes in main.jl.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────────
RESAMPLE_MINUTES = 15   # ← change resolution here (and update dt_minutes in main.jl)
P_MAX = 385.0           # kW, generator rated power (both units identical)

DATA_DIR = Path(__file__).parent

# ── Load raw data ─────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_DIR / "v01.csv", parse_dates=["DateTime"])

# ── Drop always-zero columns ─────────────────────────────────────────────────
zero_cols = [
    col for col in df.columns
    if col not in ("DateTime", "Latitude", "Longitude")
    and (df[col].fillna(0) != 0).sum() == 0
]
df_clean = df.drop(columns=zero_cols)
df_clean.to_csv(DATA_DIR / "v01_clean.csv", index=False)
print(f"v01_clean.csv: {df_clean.shape[0]} rows × {df_clean.shape[1]} columns")
print(f"  Removed {len(zero_cols)} always-zero columns:")
for c in zero_cols:
    print(f"    - {c}")

# ── Rename relevant columns ──────────────────────────────────────────────────
col_map = {
    "Electric Power System > Energy Storage Main > 1 > Battery Space > Power":
        "batt_power",
    "Electric Power System > Generator Set > 1 > Engine > Load percentage":
        "gen1_load_pct",
    "Electric Power System > Generator Set > 2 > Engine > Load percentage":
        "gen2_load_pct",
}
df = df.rename(columns=col_map).set_index("DateTime")

# ── Derive electrical load ────────────────────────────────────────────────────
# Generator load% is reported sparsely — forward-fill between sensor updates.
# batt_power > 0: battery discharging (supplying the bus)
# batt_power < 0: battery charging (consuming from generators)
# Total electrical load = generator output + battery net supply
df["gen1_load_pct"] = df["gen1_load_pct"].ffill().fillna(0.0)
df["gen2_load_pct"] = df["gen2_load_pct"].ffill().fillna(0.0)

df["load_kw"] = (
    df["gen1_load_pct"] / 100.0 * P_MAX
    + df["gen2_load_pct"] / 100.0 * P_MAX
    + df["batt_power"]
).clip(lower=0.0)

# ── Resample to target resolution ────────────────────────────────────────────
resampled = df["load_kw"].resample(f"{RESAMPLE_MINUTES}min").mean().dropna()

profile = pd.DataFrame({
    "timestep": range(1, len(resampled) + 1),
    "load_kw":  resampled.round(2).values,
    "datetime": resampled.index.strftime("%Y-%m-%d %H:%M"),
})
profile.to_csv(DATA_DIR / "load_profile.csv", index=False)

print(f"\nload_profile.csv: {len(profile)} timesteps at {RESAMPLE_MINUTES}-min resolution")
print(f"  Datetime range: {profile['datetime'].iloc[0]} to {profile['datetime'].iloc[-1]}")
print(f"  Load range: {profile['load_kw'].min():.1f} - {profile['load_kw'].max():.1f} kW")
print(f"  Mean load:  {profile['load_kw'].mean():.1f} kW")
