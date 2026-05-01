from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SWEEP_DIR = REPO_ROOT / "analysis" / "output" / "rolling_horizon" / "forecast_soft_soc_horizon_sweep"


def parse_args() -> tuple[Path]:
    import argparse

    parser = argparse.ArgumentParser(
        description="Plot a forecast soft-SOC rolling-horizon sweep."
    )
    parser.add_argument(
        "--sweep-dir",
        type=Path,
        default=DEFAULT_SWEEP_DIR,
        help="Directory containing summary.csv and receiving the generated figures.",
    )
    args = parser.parse_args()
    sweep_dir = args.sweep_dir if args.sweep_dir.is_absolute() else REPO_ROOT / args.sweep_dir
    return (sweep_dir,)


def annotate_points(ax: plt.Axes, x: pd.Series, y: pd.Series, labels: pd.Series, *, dy: float = 0.0) -> None:
    for x_val, y_val, label in zip(x, y, labels):
        ax.annotate(
            f"H={int(label)}",
            (x_val, y_val),
            xytext=(0, 8 + dy),
            textcoords="offset points",
            ha="center",
            fontsize=10,
            color="#111827",
        )


def save_composed(df: pd.DataFrame, sweep_dir: Path) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9), constrained_layout=True)

    x = df["horizon_hours"]
    labels = df["horizon_steps"]
    color = "#2563EB"

    ax = axes[0, 0]
    ax.plot(x, df["fuel_delta_vs_full_pct"], marker="o", linewidth=2.4, color=color)
    annotate_points(ax, x, df["fuel_delta_vs_full_pct"], labels)
    ax.axhline(0.0, color="#111827", linestyle="--", linewidth=1.2, alpha=0.7)
    ax.set_title("Fuel Penalty vs Offline MILP", fontsize=15)
    ax.set_xlabel("Rolling horizon [h]", fontsize=12)
    ax.set_ylabel("Fuel delta [%]", fontsize=12)

    ax = axes[0, 1]
    ax.plot(x, df["rolling_starts"], marker="o", linewidth=2.4, color="#DC2626")
    ax.axhline(float(df["full_starts"].iloc[0]), color="#111827", linestyle="--", linewidth=1.2, alpha=0.7)
    annotate_points(ax, x, df["rolling_starts"], labels)
    ax.set_title("Generator Starts", fontsize=15)
    ax.set_xlabel("Rolling horizon [h]", fontsize=12)
    ax.set_ylabel("Starts", fontsize=12)

    ax = axes[1, 0]
    ax.plot(x, df["rolling_min_soc_pct"], marker="o", linewidth=2.2, color="#059669", label="Minimum SOC")
    ax.plot(x, df["rolling_final_soc_pct"], marker="s", linewidth=2.2, color="#7C3AED", label="Final SOC")
    ax.axhline(20.0, color="#64748B", linestyle="--", linewidth=1.1, label="SOC min")
    ax.set_title("SOC Behavior", fontsize=15)
    ax.set_xlabel("Rolling horizon [h]", fontsize=12)
    ax.set_ylabel("SOC [%]", fontsize=12)
    ax.legend(fontsize=10)

    ax = axes[1, 1]
    ax.plot(x, df["p95_solve_s"], marker="o", linewidth=2.2, color="#EA580C", label="P95 local solve")
    ax.plot(x, df["max_solve_s"], marker="s", linewidth=2.2, color="#9333EA", label="Max local solve")
    ax.set_title("Local Solve Time", fontsize=15)
    ax.set_xlabel("Rolling horizon [h]", fontsize=12)
    ax.set_ylabel("Seconds", fontsize=12)
    ax.legend(fontsize=10)

    for axis in axes.flatten():
        axis.tick_params(axis="both", labelsize=11)
        axis.grid(alpha=0.25)

    fig.suptitle("Forecast Rolling MILP Horizon Sweep, Operational Profile", fontsize=18, fontweight="bold")
    fig.savefig(sweep_dir / "forecast_soft_soc_horizon_sweep_overview.png", dpi=200, bbox_inches="tight")
    fig.savefig(sweep_dir / "forecast_soft_soc_horizon_sweep_overview.pdf", bbox_inches="tight")
    plt.close(fig)


def save_tradeoff(df: pd.DataFrame, sweep_dir: Path) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(9, 6), constrained_layout=True)

    scatter = ax.scatter(
        df["rolling_starts"],
        df["fuel_delta_vs_full_pct"],
        c=df["horizon_hours"],
        cmap="viridis",
        s=95,
        edgecolor="#111827",
        linewidth=0.6,
    )
    for _, row in df.iterrows():
        ax.annotate(
            f"H={int(row['horizon_steps'])}",
            (row["rolling_starts"], row["fuel_delta_vs_full_pct"]),
            xytext=(7, 5),
            textcoords="offset points",
            fontsize=10,
        )

    ax.axvline(float(df["full_starts"].iloc[0]), color="#111827", linestyle="--", linewidth=1.2, alpha=0.7)
    ax.axhline(0.0, color="#111827", linestyle="--", linewidth=1.2, alpha=0.7)
    ax.set_title("Fuel and Start Tradeoff", fontsize=16)
    ax.set_xlabel("Generator starts", fontsize=12)
    ax.set_ylabel("Fuel delta vs offline [%]", fontsize=12)
    ax.tick_params(axis="both", labelsize=11)
    ax.grid(alpha=0.25)
    cbar = fig.colorbar(scatter, ax=ax)
    cbar.set_label("Horizon [h]", fontsize=11)

    fig.savefig(sweep_dir / "forecast_soft_soc_horizon_tradeoff.png", dpi=200, bbox_inches="tight")
    fig.savefig(sweep_dir / "forecast_soft_soc_horizon_tradeoff.pdf", bbox_inches="tight")
    plt.close(fig)


def write_assessment(df: pd.DataFrame, sweep_dir: Path) -> None:
    best_fuel = df.sort_values("fuel_delta_vs_full_pct").iloc[0]
    best_starts = df.sort_values(["rolling_starts", "fuel_delta_vs_full_pct"]).iloc[0]
    current = df.loc[df["horizon_steps"] == 24].iloc[0] if (df["horizon_steps"] == 24).any() else None
    scaling = df["soft_soc_penalty_scaling"].iloc[0] if "soft_soc_penalty_scaling" in df.columns else "sum"

    lines = [
        "# Forecast Soft-SOC Horizon Sweep Assessment",
        "",
        f"Operational 15-minute average profile, moving-average forecast, soft 20-80% SOC band, `{scaling}` soft-SOC penalty scaling.",
        "",
        "## Completed Cases",
        "",
        "| H steps | Horizon [h] | Fuel [kg] | Delta vs offline [%] | Starts | Short runs | Min SOC [%] | Final SOC [%] | P95 solve [s] |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in df.sort_values("horizon_steps").iterrows():
        lines.append(
            "| "
            f"{int(row['horizon_steps'])} | {row['horizon_hours']:.2f} | "
            f"{row['rolling_fuel_kg']:.3f} | {row['fuel_delta_vs_full_pct']:.2f} | "
            f"{int(row['rolling_starts'])} | {int(row.get('short_1_2_step_generator_runs', 0))} | "
            f"{row['rolling_min_soc_pct']:.2f} | "
            f"{row['rolling_final_soc_pct']:.2f} | {row['p95_solve_s']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Assessment",
            "",
            f"- Best fuel result: H={int(best_fuel['horizon_steps'])} ({best_fuel['horizon_hours']:.1f} h), {best_fuel['rolling_fuel_kg']:.3f} kg, {best_fuel['fuel_delta_vs_full_pct']:.2f}% above offline, with {int(best_fuel['rolling_starts'])} starts.",
            f"- Best starts result among completed cases: H={int(best_starts['horizon_steps'])} ({best_starts['horizon_hours']:.1f} h), {int(best_starts['rolling_starts'])} starts, but {best_starts['fuel_delta_vs_full_pct']:.2f}% above offline.",
        ]
    )
    if current is not None:
        lines.append(
            f"- Current H=24 baseline: {current['fuel_delta_vs_full_pct']:.2f}% above offline, {int(current['rolling_starts'])} starts, final SOC {current['rolling_final_soc_pct']:.2f}%."
        )
    lines.extend(
        [
            "- Short 1-2 timestep generator runs are counted from realized commitment blocks in `dispatch_results.csv`.",
            "",
            "## Generated Figures",
            "",
            "- `forecast_soft_soc_horizon_sweep_overview.png`",
            "- `forecast_soft_soc_horizon_tradeoff.png`",
            "",
        ]
    )
    (sweep_dir / "assessment.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    (sweep_dir,) = parse_args()
    summary_csv = sweep_dir / "summary.csv"
    df = pd.read_csv(summary_csv)
    df = df.sort_values("horizon_steps").reset_index(drop=True)
    save_composed(df, sweep_dir)
    save_tradeoff(df, sweep_dir)
    write_assessment(df, sweep_dir)
    print(f"Saved {sweep_dir / 'forecast_soft_soc_horizon_sweep_overview.png'}")
    print(f"Saved {sweep_dir / 'forecast_soft_soc_horizon_tradeoff.png'}")
    print(f"Saved {sweep_dir / 'assessment.md'}")


if __name__ == "__main__":
    main()
