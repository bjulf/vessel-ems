"""Preprocesses operational data from v01.csv:
  1. Creates v01_clean.csv  — always-zero columns removed
  2. Creates load_profile.csv — resampled electrical load for the dispatch model
  3. Creates operational_profiles/operational_load_profile_1min.csv — continuous 1-minute comparison profile

To change the time resolution, update RESAMPLE_MINUTES below and re-run.
The same value must be reflected as dt_minutes in main.jl.
"""

import pandas as pd
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────────
RESAMPLE_MINUTES = 15   # ← change resolution here (and update dt_minutes in main.jl)
COMPARISON_RESAMPLE_MINUTES = 1
P_MAX = 385.0           # kW, generator rated power (both units identical)

DATA_DIR = Path(__file__).parent
OPERATIONAL_PROFILES_DIR = DATA_DIR / "operational_profiles"
COMPARISON_PROFILE_PATH = OPERATIONAL_PROFILES_DIR / "operational_load_profile_1min.csv"


def build_profile(series: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({
        "timestep": range(1, len(series) + 1),
        "load_kw": series.round(2).values,
        "datetime": series.index.strftime("%Y-%m-%d %H:%M"),
    })

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

# ── Build a continuous 1-minute operational profile ─────────────────────────
load_1min = df["load_kw"].resample(f"{COMPARISON_RESAMPLE_MINUTES}min").mean()
missing_1min_rows = int(load_1min.isna().sum())
load_1min = load_1min.interpolate(method="time").ffill().bfill()

OPERATIONAL_PROFILES_DIR.mkdir(parents=True, exist_ok=True)
comparison_profile = build_profile(load_1min)
comparison_profile.to_csv(COMPARISON_PROFILE_PATH, index=False)

# ── Resample to target resolution for the dispatch model ─────────────────────
resampled = load_1min.resample(f"{RESAMPLE_MINUTES}min").mean().dropna()
profile = build_profile(resampled)
profile.to_csv(DATA_DIR / "load_profile.csv", index=False)

print(
    f"\noperational_load_profile_1min.csv: {len(comparison_profile)} timesteps "
    f"at {COMPARISON_RESAMPLE_MINUTES}-min resolution"
)
print(f"  Filled missing 1-minute timestamps by interpolation: {missing_1min_rows}")
print(
    f"  Datetime range: {comparison_profile['datetime'].iloc[0]} "
    f"to {comparison_profile['datetime'].iloc[-1]}"
)
print(
    f"  Load range: {comparison_profile['load_kw'].min():.1f} "
    f"- {comparison_profile['load_kw'].max():.1f} kW"
)
print(f"  Mean load:  {comparison_profile['load_kw'].mean():.1f} kW")
print(f"  Saved to: {COMPARISON_PROFILE_PATH}")

print(f"\nload_profile.csv: {len(profile)} timesteps at {RESAMPLE_MINUTES}-min resolution")
print(f"  Datetime range: {profile['datetime'].iloc[0]} to {profile['datetime'].iloc[-1]}")
print(f"  Load range: {profile['load_kw'].min():.1f} - {profile['load_kw'].max():.1f} kW")
print(f"  Mean load:  {profile['load_kw'].mean():.1f} kW")
