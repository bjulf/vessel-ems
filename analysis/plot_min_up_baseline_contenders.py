from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "analysis" / "output" / "rolling_horizon" / "min_up_baseline_contenders"
SUMMARY_PATH = OUTPUT_DIR / "summary.csv"


CASE_LABELS = {
    "h12_startup500_softsoc10000_minup6": "Startup 500\nSOC penalty 10000",
    "h12_startup0_softsoc10000_minup6": "Startup 0\nSOC penalty 10000",
    "h12_startup0_softsoc1000_minup6": "Startup 0\nSOC penalty 1000",
    "h16_startup0_softsoc1000_minup6": "H16 startup 0\nSOC penalty 1000",
    "h12_startup1000_softsoc10000_minup6": "Startup 1000\nSOC penalty 10000",
}


def load_summary() -> pd.DataFrame:
    df = pd.read_csv(SUMMARY_PATH)
    df["case_label"] = df["case_id"].map(CASE_LABELS).fillna(df["case_id"])
    df = df.sort_values(["horizon_steps", "startup_cost_g_per_start", "soft_soc_penalty_g_per_kwh"])
    return df.reset_index(drop=True)


def annotate_bars(ax: plt.Axes, values: pd.Series, fmt: str, *, x_offset: float = 0.03) -> None:
    for idx, value in enumerate(values):
        ax.text(value + x_offset, idx, fmt.format(value), va="center", ha="left", fontsize=9)


def main() -> None:
    df = load_summary()
    y = range(len(df))

    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
        }
    )

    fig, axes = plt.subplots(
        2,
        2,
        figsize=(11.5, max(6.2, 1.25 * len(df) + 3.5)),
        constrained_layout=True,
    )
    ax_fuel, ax_starts, ax_soc, ax_solve = axes.ravel()

    colors = {
        "fuel": "#2563EB",
        "starts": "#B45309",
        "run_count": "#64748B",
        "soc_min": "#7C3AED",
        "soc_final": "#059669",
        "solve": "#DC2626",
        "p95": "#F59E0B",
    }

    ax_fuel.barh(y, df["fuel_delta_vs_full_pct"], color=colors["fuel"], alpha=0.85)
    ax_fuel.set_yticks(y, df["case_label"])
    ax_fuel.invert_yaxis()
    ax_fuel.set_xlabel("Fuel delta vs full horizon [%]")
    ax_fuel.set_title("Fuel Penalty")
    annotate_bars(ax_fuel, df["fuel_delta_vs_full_pct"], "{:.2f}%")
    ax_fuel.grid(axis="x", alpha=0.25)

    bar_height = 0.36
    ax_starts.barh(
        [v - bar_height / 2 for v in y],
        df["rolling_starts"],
        height=bar_height,
        color=colors["starts"],
        alpha=0.85,
        label="Starts",
    )
    ax_starts.barh(
        [v + bar_height / 2 for v in y],
        df["run_count"],
        height=bar_height,
        color=colors["run_count"],
        alpha=0.75,
        label="On-blocks",
    )
    ax_starts.set_yticks(y, df["case_label"])
    ax_starts.invert_yaxis()
    ax_starts.set_xlabel("Count")
    ax_starts.set_title("Commitment Activity")
    ax_starts.legend(loc="lower right", frameon=True)
    ax_starts.grid(axis="x", alpha=0.25)

    ax_soc.scatter(df["minimum_soc_pct"], y, s=70, color=colors["soc_min"], label="Minimum SOC")
    ax_soc.scatter(df["final_soc_pct"], y, s=70, color=colors["soc_final"], label="Final SOC")
    for idx, row in df.iterrows():
        ax_soc.plot(
            [row["minimum_soc_pct"], row["final_soc_pct"]],
            [idx, idx],
            color="#CBD5E1",
            linewidth=2,
            zorder=0,
        )
    ax_soc.axvline(20.0, color="#374151", linestyle="--", linewidth=1.2, label="20% bound")
    ax_soc.set_yticks(y, df["case_label"])
    ax_soc.invert_yaxis()
    ax_soc.set_xlabel("SOC [%]")
    ax_soc.set_title("SOC Outcome")
    ax_soc.set_xlim(0, max(65, df[["minimum_soc_pct", "final_soc_pct"]].max().max() + 8))
    ax_soc.legend(loc="lower right", frameon=True)
    ax_soc.grid(axis="x", alpha=0.25)

    ax_solve.barh(y, df["p95_solve_s"], color=colors["p95"], alpha=0.75, label="P95 solve")
    ax_solve.scatter(df["max_solve_s"], y, color=colors["solve"], s=60, marker="D", label="Max solve")
    for idx, row in df.iterrows():
        if float(row["nonoptimal_solves"]) > 0:
            ax_solve.text(
                row["max_solve_s"] * 1.12,
                idx,
                f"{int(row['nonoptimal_solves'])} nonoptimal",
                va="center",
                fontsize=9,
                color=colors["solve"],
            )
    ax_solve.set_xscale("log")
    ax_solve.set_yticks(y, df["case_label"])
    ax_solve.invert_yaxis()
    ax_solve.set_xlabel("Solve time [s], log scale")
    ax_solve.set_title("Solve Robustness")
    ax_solve.legend(loc="lower right", frameon=True)
    ax_solve.grid(axis="x", alpha=0.25, which="both")

    fig.suptitle(
        "Rolling-Horizon Baseline Contenders With 6-Step Minimum Up-Time",
        fontsize=14,
        fontweight="bold",
    )

    png_path = OUTPUT_DIR / "min_up_baseline_contenders_summary.png"
    pdf_path = OUTPUT_DIR / "min_up_baseline_contenders_summary.pdf"
    fig.savefig(png_path, dpi=220)
    fig.savefig(pdf_path)
    plt.close(fig)
    print(f"Saved {png_path}")
    print(f"Saved {pdf_path}")


if __name__ == "__main__":
    main()
