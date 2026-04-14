from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


RATED_POWER_KW = 385.0
FUEL_DENSITY_G_PER_L = 840.0
REGIME_SPLIT_RPM = 1600.0

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "v01_clean.csv"

GEN_COLS = {
    1: {
        "fuel_lph": "Electric Power System > Generator Set > 1 > Engine > Fuel Rate",
        "load_pct": "Electric Power System > Generator Set > 1 > Engine > Load percentage",
        "speed_rpm": "Electric Power System > Generator Set > 1 > Engine > Speed",
    },
    2: {
        "fuel_lph": "Electric Power System > Generator Set > 2 > Engine > Fuel Rate",
        "load_pct": "Electric Power System > Generator Set > 2 > Engine > Load percentage",
        "speed_rpm": "Electric Power System > Generator Set > 2 > Engine > Speed",
    },
}


def fmt_range(series: pd.Series, decimals: int = 2) -> str:
    return f"{series.min():.{decimals}f} to {series.max():.{decimals}f}"


def summarize_generator(df: pd.DataFrame, gen: int) -> list[str]:
    cols = GEN_COLS[gen]
    sub = df[list(cols.values())].rename(columns={v: k for k, v in cols.items()}).copy()

    sub["fuel_lph"] = sub["fuel_lph"].fillna(0.0)
    sub["load_pct"] = sub["load_pct"].fillna(0.0)
    sub["speed_rpm"] = sub["speed_rpm"].fillna(0.0)

    valid = sub.loc[
        (sub["fuel_lph"] > 0.0)
        & (sub["load_pct"] > 0.0)
        & (sub["speed_rpm"] > 0.0)
    ].copy()

    lines = [
        f"Gen {gen}",
        f"  non-null counts: fuel={int((sub['fuel_lph'] > 0).sum())}, load={int((sub['load_pct'] > 0).sum())}, speed={int((sub['speed_rpm'] > 0).sum())}",
        f"  valid points (fuel+load+speed > 0): {len(valid)}",
    ]

    if valid.empty:
        lines.append("  no valid points")
        return lines

    valid["power_kw"] = valid["load_pct"] / 100.0 * RATED_POWER_KW
    valid["fuel_gph"] = valid["fuel_lph"] * FUEL_DENSITY_G_PER_L
    valid["sfoc_gkwh"] = valid["fuel_gph"] / valid["power_kw"]
    valid["regime"] = np.where(valid["speed_rpm"] < REGIME_SPLIT_RPM, "lt1600", "ge1600")

    top_speeds = valid["speed_rpm"].round().value_counts().head(6)
    lines.extend(
        [
            f"  load_pct range: {fmt_range(valid['load_pct'])}",
            f"  fallback power_kw range: {fmt_range(valid['power_kw'])}",
            f"  fuel_lph range: {fmt_range(valid['fuel_lph'])}",
            f"  provisional sfoc range: {fmt_range(valid['sfoc_gkwh'])}",
            f"  regime counts: {valid['regime'].value_counts().to_dict()}",
            "  top rounded speeds:",
        ]
    )
    lines.extend(f"    {int(speed)} rpm: {count}" for speed, count in top_speeds.items())

    for regime, regime_df in valid.groupby("regime"):
        sfoc = regime_df["sfoc_gkwh"]
        lines.append(
            f"  {regime} sfoc median/p10/p90: "
            f"{sfoc.median():.1f} / {sfoc.quantile(0.1):.1f} / {sfoc.quantile(0.9):.1f}"
        )

    return lines


def main() -> None:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Missing {DATA_PATH}")

    df = pd.read_csv(DATA_PATH, parse_dates=["DateTime"])
    dt_minutes = df["DateTime"].sort_values().diff().dropna().dt.total_seconds() / 60.0

    print("SFOC screening")
    print(f"data: {DATA_PATH}")
    print(f"rows: {len(df)}")
    print(f"columns: {len(df.columns)}")
    print(f"time range: {df['DateTime'].min()} to {df['DateTime'].max()}")
    print(f"dominant cadence counts: {dt_minutes.value_counts().sort_index().to_dict()}")

    both_online = (
        (df[GEN_COLS[1]["load_pct"]].fillna(0.0) > 0.0)
        & (df[GEN_COLS[1]["speed_rpm"]].fillna(0.0) > 0.0)
        & (df[GEN_COLS[2]["load_pct"]].fillna(0.0) > 0.0)
        & (df[GEN_COLS[2]["speed_rpm"]].fillna(0.0) > 0.0)
    )
    print(f"both gensets online points: {int(both_online.sum())}")

    for gen in GEN_COLS:
        for line in summarize_generator(df, gen):
            print(line)


if __name__ == "__main__":
    main()
