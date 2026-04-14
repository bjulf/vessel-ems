from __future__ import annotations

from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = REPO_ROOT / "data" / "v01_clean.csv"
OUTPUT_DIR = REPO_ROOT / "analysis" / "output"
CSV_PATH = OUTPUT_DIR / "startup_fuel_events.csv"
SUMMARY_PATH = OUTPUT_DIR / "startup_fuel_summary.txt"


def estimate_startup_fuel(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for gen in [1, 2]:
        fuel_col = f"Electric Power System > Generator Set > {gen} > Engine > Fuel Rate"
        load_col = f"Electric Power System > Generator Set > {gen} > Engine > Load percentage"
        speed_col = f"Electric Power System > Generator Set > {gen} > Engine > Speed"

        sub = df[["DateTime", fuel_col, load_col, speed_col]].rename(
            columns={fuel_col: "fuel_lph", load_col: "load_pct", speed_col: "speed_rpm"}
        ).copy()
        sub[["fuel_lph", "load_pct", "speed_rpm"]] = sub[["fuel_lph", "load_pct", "speed_rpm"]].fillna(0.0)
        sub["online"] = (sub["speed_rpm"] > 0.0) | (sub["fuel_lph"] > 0.0)
        starts = sub.index[(sub["online"]) & (~sub["online"].shift(fill_value=False))].tolist()

        for start_idx in starts:
            stable_idx = None
            regime = None
            for i in range(start_idx, min(len(sub) - 2, start_idx + 15)):
                speeds = sub.loc[i : i + 2, "speed_rpm"]
                if speeds.between(1350, 1450).all():
                    stable_idx = i
                    regime = "1400"
                    break
                if speeds.between(1750, 1850).all():
                    stable_idx = i
                    regime = "1800"
                    break

            if stable_idx is None:
                continue

            pre = sub.loc[start_idx : stable_idx - 1] if stable_idx > start_idx else sub.loc[start_idx : start_idx - 1]
            fuel_liters = pre["fuel_lph"].sum() / 60.0
            rows.append(
                {
                    "gen": gen,
                    "start_time": sub.loc[start_idx, "DateTime"],
                    "stable_time": sub.loc[stable_idx, "DateTime"],
                    "regime": regime,
                    "minutes_before_stable": len(pre),
                    "fuel_before_stable_l": round(fuel_liters, 3),
                    "fuel_before_stable_g": round(fuel_liters * 840.0, 1),
                    "max_load_before_stable_pct": round(pre["load_pct"].max() if len(pre) else 0.0, 2),
                    "max_speed_before_stable": round(pre["speed_rpm"].max() if len(pre) else 0.0, 2),
                }
            )

    return pd.DataFrame(rows)


def build_summary(events: pd.DataFrame) -> str:
    lines = ["Startup fuel estimate", f"Source: {DATA_PATH}", ""]
    lines.append("Per-event results:")
    lines.append(events.to_string(index=False))
    lines.append("")
    lines.append("Grouped by target stable regime:")
    lines.append(
        events.groupby("regime")[["minutes_before_stable", "fuel_before_stable_l", "fuel_before_stable_g"]]
        .agg(["count", "mean", "median", "min", "max"])
        .round(2)
        .to_string()
    )
    lines.append("")
    lines.append(
        f"Overall fuel_before_stable_g mean / median: {events['fuel_before_stable_g'].mean():.1f} / {events['fuel_before_stable_g'].median():.1f}"
    )
    return "\n".join(lines)


def main() -> None:
    df = pd.read_csv(DATA_PATH, parse_dates=["DateTime"])
    events = estimate_startup_fuel(df)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    events.to_csv(CSV_PATH, index=False)
    summary = build_summary(events)
    SUMMARY_PATH.write_text(summary, encoding="utf-8")
    print(summary)
    print("")
    print(f"Saved {CSV_PATH}")
    print(f"Saved {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
