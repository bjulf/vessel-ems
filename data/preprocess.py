"""Build harmonized operational load profiles from vessel telemetry exports.

Outputs:
  - v01_clean.csv: 3-day raw export with always-zero columns removed
  - operational_profiles/operational_load_profile_1min.csv
  - operational_profiles/operational_load_profile_15min_avg.csv
  - operational_profiles/operational_load_profile_6day_1min.csv
  - operational_profiles/operational_load_profile_6day_15min_avg.csv

The 3-day and 6-day profiles use the same reconstruction pipeline:
  1. read raw telemetry exports
  2. sort and deduplicate timestamps
  3. forward-fill sparse generator load-percentage signals
  4. reconstruct total load from generator load percentage and battery power
  5. resample to a continuous 1-minute grid and time-interpolate gaps
  6. save rounded 1-minute profiles
  7. average the rounded 1-minute profiles to the model timestep

To change the model resolution, update RESAMPLE_MINUTES and keep the relevant
dt_minutes setting in the Julia configuration aligned.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


RESAMPLE_MINUTES = 15
COMPARISON_RESAMPLE_MINUTES = 1
P_MAX = 385.0

DATA_DIR = Path(__file__).parent
OPERATIONAL_RAW_DIR = DATA_DIR / "operational_raw"
OPERATIONAL_PROFILES_DIR = DATA_DIR / "operational_profiles"

BATT_POWER_COL = "Electric Power System > Energy Storage Main > 1 > Battery Space > Power"
GEN1_LOAD_PCT_COL = "Electric Power System > Generator Set > 1 > Engine > Load percentage"
GEN2_LOAD_PCT_COL = "Electric Power System > Generator Set > 2 > Engine > Load percentage"


@dataclass(frozen=True)
class OperationalCase:
    label: str
    raw_paths: tuple[Path, ...]
    profile_1min_path: Path
    profile_15min_path: Path
    cleaned_copy_path: Path | None = None


CASES = (
    OperationalCase(
        label="3-day",
        raw_paths=(DATA_DIR / "v01.csv",),
        profile_1min_path=OPERATIONAL_PROFILES_DIR / "operational_load_profile_1min.csv",
        profile_15min_path=OPERATIONAL_PROFILES_DIR / "operational_load_profile_15min_avg.csv",
        cleaned_copy_path=DATA_DIR / "v01_clean.csv",
    ),
    OperationalCase(
        label="6-day",
        raw_paths=(
            OPERATIONAL_RAW_DIR / "6day" / "all-data-types_2026-01-26_to_2026-01-28.csv",
            OPERATIONAL_RAW_DIR / "6day" / "all-data-types_2026-01-28_to_2026-01-31.csv",
        ),
        profile_1min_path=OPERATIONAL_PROFILES_DIR / "operational_load_profile_6day_1min.csv",
        profile_15min_path=OPERATIONAL_PROFILES_DIR / "operational_load_profile_6day_15min_avg.csv",
    ),
)


def build_profile(series: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestep": range(1, len(series) + 1),
            "load_kw": series.round(2).values,
            "datetime": series.index.strftime("%Y-%m-%d %H:%M"),
        }
    )


def load_raw_inputs(paths: tuple[Path, ...]) -> pd.DataFrame:
    missing_paths = [path for path in paths if not path.exists()]
    if missing_paths:
        missing = "\n".join(f"  - {path}" for path in missing_paths)
        raise FileNotFoundError(f"Missing raw telemetry input(s):\n{missing}")

    frames = [pd.read_csv(path, parse_dates=["DateTime"]) for path in paths]
    raw = pd.concat(frames, ignore_index=True)
    return raw.sort_values("DateTime").drop_duplicates(subset=["DateTime"], keep="first").reset_index(drop=True)


def write_cleaned_copy(raw: pd.DataFrame, path: Path) -> None:
    zero_cols = [
        col
        for col in raw.columns
        if col not in ("DateTime", "Latitude", "Longitude") and (raw[col].fillna(0) != 0).sum() == 0
    ]
    cleaned = raw.drop(columns=zero_cols)
    cleaned.to_csv(path, index=False)

    print(f"{path.name}: {cleaned.shape[0]} rows x {cleaned.shape[1]} columns")
    print(f"  Removed {len(zero_cols)} always-zero columns")
    for col in zero_cols:
        print(f"    - {col}")


def reconstruct_load(raw: pd.DataFrame) -> pd.Series:
    df = raw.rename(
        columns={
            BATT_POWER_COL: "batt_power",
            GEN1_LOAD_PCT_COL: "gen1_load_pct",
            GEN2_LOAD_PCT_COL: "gen2_load_pct",
        }
    ).set_index("DateTime")

    # Generator load percentages are reported sparsely; hold the last value
    # until the next telemetry update.
    df["gen1_load_pct"] = df["gen1_load_pct"].ffill().fillna(0.0)
    df["gen2_load_pct"] = df["gen2_load_pct"].ffill().fillna(0.0)

    # batt_power > 0 means discharge to the bus; batt_power < 0 means charging.
    return (
        df["gen1_load_pct"] / 100.0 * P_MAX
        + df["gen2_load_pct"] / 100.0 * P_MAX
        + df["batt_power"]
    ).clip(lower=0.0)


def profile_15min_from_saved_1min(profile_1min: pd.DataFrame) -> pd.DataFrame:
    rounded_1min = pd.Series(
        profile_1min["load_kw"].to_numpy(),
        index=pd.to_datetime(profile_1min["datetime"]),
        name="load_kw",
    )
    resampled = rounded_1min.resample(f"{RESAMPLE_MINUTES}min").mean().dropna()
    return build_profile(resampled)


def process_case(case: OperationalCase) -> None:
    raw = load_raw_inputs(case.raw_paths)
    if case.cleaned_copy_path is not None:
        write_cleaned_copy(raw, case.cleaned_copy_path)

    load_kw = reconstruct_load(raw)
    load_1min = load_kw.resample(f"{COMPARISON_RESAMPLE_MINUTES}min").mean()
    missing_1min_rows = int(load_1min.isna().sum())
    load_1min = load_1min.interpolate(method="time").ffill().bfill()

    OPERATIONAL_PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    profile_1min = build_profile(load_1min)
    profile_15min = profile_15min_from_saved_1min(profile_1min)

    profile_1min.to_csv(case.profile_1min_path, index=False)
    profile_15min.to_csv(case.profile_15min_path, index=False)

    print(f"\n{case.label} operational profile")
    print(f"  Raw rows: {len(raw)}")
    print(f"  Raw range: {raw['DateTime'].iloc[0]} to {raw['DateTime'].iloc[-1]}")
    print(f"  Filled missing 1-minute timestamps by interpolation: {missing_1min_rows}")
    print(
        f"  1-minute profile: {len(profile_1min)} steps, "
        f"{profile_1min['datetime'].iloc[0]} to {profile_1min['datetime'].iloc[-1]}"
    )
    print(
        f"  {RESAMPLE_MINUTES}-minute profile: {len(profile_15min)} steps, "
        f"{profile_15min['datetime'].iloc[0]} to {profile_15min['datetime'].iloc[-1]}"
    )
    print(
        f"  Load range: {profile_15min['load_kw'].min():.1f} "
        f"- {profile_15min['load_kw'].max():.1f} kW"
    )
    print(f"  Mean load: {profile_15min['load_kw'].mean():.1f} kW")
    print(f"  Saved: {case.profile_1min_path}")
    print(f"  Saved: {case.profile_15min_path}")


def main() -> None:
    for case in CASES:
        process_case(case)


if __name__ == "__main__":
    main()
