from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
SWEEP_DIR = (
    REPO_ROOT
    / "analysis"
    / "output"
    / "rolling_horizon"
    / "forecast_soft_soc_mean_penalty_tuning_screen"
)
SUMMARY_CSV = SWEEP_DIR / "summary.csv"


def pivot_metric(df: pd.DataFrame, horizon: int, metric: str) -> pd.DataFrame:
    part = df.loc[df["horizon_steps"] == horizon]
    return part.pivot(
        index="soft_soc_penalty_g_per_kwh",
        columns="startup_cost_g_per_start",
        values=metric,
    ).sort_index(ascending=False)


def annotate_heatmap(ax: plt.Axes, data: pd.DataFrame, fmt: str) -> None:
    for y_idx, (_, row) in enumerate(data.iterrows()):
        for x_idx, value in enumerate(row):
            ax.text(
                x_idx,
                y_idx,
                format(value, fmt),
                ha="center",
                va="center",
                fontsize=10,
                color="#111827",
            )


def save_metric_heatmaps(df: pd.DataFrame, metric: str, title: str, filename: str, fmt: str) -> None:
    horizons = sorted(df["horizon_steps"].unique())
    fig, axes = plt.subplots(
        1,
        len(horizons),
        figsize=(7.2 * len(horizons), 5.6),
        constrained_layout=True,
        squeeze=False,
    )
    values = df[metric]
    vmin = values.min()
    vmax = values.max()

    for ax, horizon in zip(axes[0], horizons):
        data = pivot_metric(df, horizon, metric)
        image = ax.imshow(data.to_numpy(), cmap="viridis", aspect="auto", vmin=vmin, vmax=vmax)
        annotate_heatmap(ax, data, fmt)
        ax.set_title(f"H={int(horizon)}", fontsize=15)
        ax.set_xticks(range(len(data.columns)), labels=[f"{float(v):.0f}" for v in data.columns])
        ax.set_yticks(range(len(data.index)), labels=[f"{float(v):.0f}" for v in data.index])
        ax.set_xlabel("Startup cost [g/start]", fontsize=12)
        ax.set_ylabel("Soft SOC penalty [g/kWh]", fontsize=12)
        ax.tick_params(axis="both", labelsize=11)

    fig.colorbar(image, ax=axes.ravel().tolist(), shrink=0.9)
    fig.suptitle(title, fontsize=17, fontweight="bold")
    fig.savefig(SWEEP_DIR / filename, dpi=200, bbox_inches="tight")
    plt.close(fig)


def save_tradeoff(df: pd.DataFrame) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6), constrained_layout=True, sharey=True)

    for ax, horizon in zip(axes, sorted(df["horizon_steps"].unique())):
        part = df.loc[df["horizon_steps"] == horizon]
        scatter = ax.scatter(
            part["rolling_starts"],
            part["fuel_delta_vs_full_pct"],
            c=part["soft_soc_penalty_g_per_kwh"],
            s=95,
            cmap="plasma",
            edgecolor="#111827",
            linewidth=0.6,
        )
        for _, row in part.iterrows():
            ax.annotate(
                f"C{int(row['startup_cost_g_per_start'])}",
                (row["rolling_starts"], row["fuel_delta_vs_full_pct"]),
                xytext=(6, 5),
                textcoords="offset points",
                fontsize=9,
            )
        ax.set_title(f"H={int(horizon)}", fontsize=15)
        ax.set_xlabel("Generator starts", fontsize=12)
        ax.grid(alpha=0.25)
        ax.tick_params(axis="both", labelsize=11)
    axes[0].set_ylabel("Fuel delta vs offline [%]", fontsize=12)
    cbar = fig.colorbar(scatter, ax=axes.ravel().tolist())
    cbar.set_label("Soft SOC penalty [g/kWh]", fontsize=11)
    fig.suptitle("Fuel and Start Tradeoff, Mean Soft-SOC Tuning", fontsize=17, fontweight="bold")
    fig.savefig(SWEEP_DIR / "fuel_start_tradeoff.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def write_assessment(df: pd.DataFrame) -> None:
    ranked = df.sort_values(
        ["fuel_delta_vs_full_pct", "short_1_2_step_generator_runs", "rolling_starts"]
    ).head(10)
    low_pulse = df.sort_values(
        ["short_1_2_step_generator_runs", "fuel_delta_vs_full_pct", "rolling_starts"]
    ).head(10)

    lines = [
        "# Forecast Mean Soft-SOC Tuning Assessment",
        "",
        "Operational 15-minute average profile, moving-average forecast, H=12/16, mean-normalized soft SOC penalty.",
        "",
        "## Best Fuel Cases",
        "",
        "| Rank | H | Startup | SOC penalty | Fuel delta % | Fuel kg | Starts | Short runs | Min SOC % | Final SOC % |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for idx, row in enumerate(ranked.itertuples(index=False), start=1):
        lines.append(
            f"| {idx} | {int(row.horizon_steps)} | {row.startup_cost_g_per_start:.0f} | "
            f"{row.soft_soc_penalty_g_per_kwh:.0f} | {row.fuel_delta_vs_full_pct:.2f} | "
            f"{row.rolling_fuel_kg:.3f} | {int(row.rolling_starts)} | "
            f"{int(row.short_1_2_step_generator_runs)} | {row.rolling_min_soc_pct:.2f} | "
            f"{row.rolling_final_soc_pct:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Lowest Pulse Cases",
            "",
            "| Rank | H | Startup | SOC penalty | Short runs | Fuel delta % | Starts | Min SOC % | Final SOC % |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for idx, row in enumerate(low_pulse.itertuples(index=False), start=1):
        lines.append(
            f"| {idx} | {int(row.horizon_steps)} | {row.startup_cost_g_per_start:.0f} | "
            f"{row.soft_soc_penalty_g_per_kwh:.0f} | {int(row.short_1_2_step_generator_runs)} | "
            f"{row.fuel_delta_vs_full_pct:.2f} | {int(row.rolling_starts)} | "
            f"{row.rolling_min_soc_pct:.2f} | {row.rolling_final_soc_pct:.2f} |"
        )
    lines.append("")
    (SWEEP_DIR / "assessment.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    df = pd.read_csv(SUMMARY_CSV)
    df = df.sort_values(
        ["horizon_steps", "startup_cost_g_per_start", "soft_soc_penalty_g_per_kwh"]
    ).reset_index(drop=True)
    save_metric_heatmaps(
        df,
        "fuel_delta_vs_full_pct",
        "Fuel Delta vs Offline MILP [%]",
        "heatmap_fuel_delta_pct.png",
        ".2f",
    )
    save_metric_heatmaps(df, "rolling_starts", "Generator Starts", "heatmap_starts.png", ".0f")
    save_metric_heatmaps(
        df,
        "short_1_2_step_generator_runs",
        "Short 1-2 Timestep Generator Runs",
        "heatmap_short_runs.png",
        ".0f",
    )
    save_metric_heatmaps(df, "rolling_final_soc_pct", "Final SOC [%]", "heatmap_final_soc.png", ".1f")
    save_tradeoff(df)
    write_assessment(df)
    print(f"Saved plots and assessment in {SWEEP_DIR}")


if __name__ == "__main__":
    main()
