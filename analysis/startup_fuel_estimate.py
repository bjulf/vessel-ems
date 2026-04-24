from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = REPO_ROOT / "data" / "v01_clean.csv"
OUTPUT_DIR = REPO_ROOT / "analysis" / "output"
CSV_PATH = OUTPUT_DIR / "startup_fuel_events.csv"
SUMMARY_PATH = OUTPUT_DIR / "startup_fuel_summary.txt"
FIG_PATH = OUTPUT_DIR / "startup_fuel_event_summary.png"


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


def make_plot(events: pd.DataFrame, fig_path: Path, title: str) -> None:
    if events.empty:
        return

    plot_df = events.copy().sort_values("start_time").reset_index(drop=True)
    labels = plot_df["start_time"].dt.strftime("%m-%d %H:%M")
    colors = plot_df["regime"].map({"1400": "#4c78a8", "1800": "#e45756"}).fillna("#64748b")
    mean_fuel = plot_df["fuel_before_stable_g"].mean()
    median_fuel = plot_df["fuel_before_stable_g"].median()
    median_time = plot_df["minutes_before_stable"].median()

    plt.rcParams.update(
        {
            "font.size": 15,
            "axes.titlesize": 22,
            "axes.labelsize": 18,
            "xtick.labelsize": 13,
            "ytick.labelsize": 15,
            "legend.fontsize": 14,
        }
    )

    fig, (ax_top, ax_bottom) = plt.subplots(
        2,
        1,
        figsize=(18, 10),
        sharex=True,
        gridspec_kw={"height_ratios": [2.2, 1.3]},
    )

    bars = ax_top.bar(labels, plot_df["fuel_before_stable_g"], color=colors, edgecolor="#1f2937", alpha=0.96)
    ax_top.axhline(mean_fuel, color="#1f2937", linestyle="--", linewidth=2.5, label=f"Mean = {mean_fuel:.0f} g")
    ax_top.axhline(median_fuel, color="#64748b", linestyle=":", linewidth=3.0, label=f"Median = {median_fuel:.0f} g")
    ax_top.set_ylabel("Start-up fuel [g]")
    ax_top.set_title(title, pad=18)
    ax_top.grid(axis="y", alpha=0.25)
    ax_top.legend(frameon=False, loc="upper left")
    ax_top.text(
        0.995,
        1.02,
        "Blue: ~1400 rpm regime    Red: ~1800 rpm regime",
        transform=ax_top.transAxes,
        ha="right",
        va="bottom",
        fontsize=14,
        color="#111827",
    )
    for bar, value in zip(bars, plot_df["fuel_before_stable_g"]):
        ax_top.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(plot_df["fuel_before_stable_g"]) * 0.02,
            f"{value:.0f}",
            ha="center",
            va="bottom",
            fontsize=13,
            color="#111827",
        )

    ax_bottom.plot(labels, plot_df["minutes_before_stable"], color="#1f2937", marker="o", linewidth=2.4, markersize=8)
    ax_bottom.axhline(2, color="#10b981", linestyle="--", linewidth=2.5, label="Control-system start time = 2 min")
    ax_bottom.axhline(median_time, color="#64748b", linestyle=":", linewidth=3.0, label=f"Median detected time = {median_time:.0f} min")
    ax_bottom.set_ylabel("Minutes to stable\nregime")
    ax_bottom.set_xlabel("Detected start event")
    ax_bottom.grid(axis="y", alpha=0.25)
    ax_bottom.legend(frameon=False, loc="upper left")
    for label in ax_bottom.get_xticklabels():
        label.set_rotation(35)
        label.set_horizontalalignment("right")

    fig.tight_layout()
    fig_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def build_paths(output_dir: Path) -> tuple[Path, Path, Path]:
    return (
        output_dir / "startup_fuel_events.csv",
        output_dir / "startup_fuel_summary.txt",
        output_dir / "startup_fuel_event_summary.png",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Estimate startup fuel from 1-minute telemetry.")
    parser.add_argument("--data", type=Path, default=DATA_PATH, help="Input CSV path.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="Directory for output files.")
    parser.add_argument(
        "--title",
        default="Generator Start-Up Fuel Estimate from Operational Telemetry",
        help="Figure title.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_path = args.data
    output_dir = args.output_dir
    csv_path, summary_path, fig_path = build_paths(output_dir)

    df = pd.read_csv(data_path, parse_dates=["DateTime"])
    events = estimate_startup_fuel(df)
    output_dir.mkdir(parents=True, exist_ok=True)
    events.to_csv(csv_path, index=False)
    summary = build_summary(events)
    summary = summary.replace(str(DATA_PATH), str(data_path))
    summary_path.write_text(summary, encoding="utf-8")
    make_plot(events, fig_path, args.title)
    print(summary)
    print("")
    print(f"Saved {csv_path}")
    print(f"Saved {summary_path}")
    if events.empty:
        print("No startup-fuel plot created because no valid starts were detected.")
    else:
        print(f"Saved {fig_path}")


if __name__ == "__main__":
    main()
