from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = (
    REPO_ROOT
    / "analysis"
    / "output"
    / "rolling_horizon"
    / "forecast_soft_soc_high_startup_extension"
)
HIGH_SUMMARY = OUTPUT_DIR / "summary.csv"
TUNING_SUMMARY = (
    REPO_ROOT
    / "analysis"
    / "output"
    / "rolling_horizon"
    / "forecast_soft_soc_mean_penalty_tuning_screen"
    / "summary.csv"
)


def load_combined() -> pd.DataFrame:
    high = pd.read_csv(HIGH_SUMMARY)
    tuning = pd.read_csv(TUNING_SUMMARY)
    anchors = tuning.loc[
        (
            (tuning["horizon_steps"] == 12)
            & (tuning["soft_soc_penalty_g_per_kwh"] == 10000.0)
        )
        | (
            (tuning["horizon_steps"] == 16)
            & (tuning["soft_soc_penalty_g_per_kwh"] == 1000.0)
        )
    ].copy()
    anchors["source"] = "initial_screen"
    high["source"] = "high_startup_extension"
    df = pd.concat([anchors, high], ignore_index=True, sort=False)
    df["setting"] = df.apply(
        lambda row: f"H={int(row['horizon_steps'])}, SOC penalty={int(row['soft_soc_penalty_g_per_kwh'])}",
        axis=1,
    )
    return df.sort_values(["horizon_steps", "soft_soc_penalty_g_per_kwh", "startup_cost_g_per_start"])


def save_trend_plot(df: pd.DataFrame) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    metrics = [
        ("fuel_delta_vs_full_pct", "Fuel delta [%]"),
        ("rolling_starts", "Starts"),
        ("short_1_2_step_generator_runs", "Short runs"),
        ("rolling_min_soc_pct", "Minimum SOC [%]"),
        ("rolling_final_soc_pct", "Final SOC [%]"),
    ]
    fig, axes = plt.subplots(len(metrics), 1, figsize=(10.5, 14), sharex=True, constrained_layout=True)

    for ax, (metric, ylabel) in zip(axes, metrics):
        for setting, part in df.groupby("setting"):
            part = part.sort_values("startup_cost_g_per_start")
            ax.plot(
                part["startup_cost_g_per_start"],
                part[metric],
                marker="o",
                linewidth=2.2,
                label=setting,
            )
        if metric == "rolling_min_soc_pct":
            ax.axhline(20.0, color="#DC2626", linestyle="--", linewidth=1.0)
        if metric == "rolling_final_soc_pct":
            ax.axhline(40.0, color="#64748B", linestyle="--", linewidth=1.0)
        ax.set_xscale("log")
        ax.set_ylabel(ylabel, fontsize=12)
        ax.grid(alpha=0.25)
        ax.tick_params(axis="both", labelsize=11)
    axes[0].legend(loc="upper left", fontsize=10)
    axes[-1].set_xlabel("Startup cost [g/start], log scale", fontsize=12)
    fig.suptitle("High Startup-Cost Extension", fontsize=18, fontweight="bold")
    fig.savefig(OUTPUT_DIR / "high_startup_trends.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def save_tradeoff_plot(df: pd.DataFrame) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(9.5, 6.5), constrained_layout=True)
    markers = {
        "H=12, SOC penalty=10000": "o",
        "H=16, SOC penalty=1000": "s",
    }
    for setting, part in df.groupby("setting"):
        ax.scatter(
            part["short_1_2_step_generator_runs"],
            part["fuel_delta_vs_full_pct"],
            c=part["startup_cost_g_per_start"],
            cmap="plasma",
            marker=markers.get(setting, "o"),
            s=115,
            edgecolor="#111827",
            linewidth=0.6,
            label=setting,
            vmin=df["startup_cost_g_per_start"].min(),
            vmax=df["startup_cost_g_per_start"].max(),
        )
        for _, row in part.iterrows():
            ax.annotate(
                f"{int(row['startup_cost_g_per_start'])}",
                (row["short_1_2_step_generator_runs"], row["fuel_delta_vs_full_pct"]),
                xytext=(7, 5),
                textcoords="offset points",
                fontsize=9,
            )
    ax.set_title("Fuel vs Short Runs Under Higher Startup Cost", fontsize=16, fontweight="bold")
    ax.set_xlabel("Short 1-2 timestep generator runs", fontsize=12)
    ax.set_ylabel("Fuel delta vs offline [%]", fontsize=12)
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right", fontsize=10)
    cbar = fig.colorbar(ax.collections[0], ax=ax)
    cbar.set_label("Startup cost [g/start]", fontsize=11)
    fig.savefig(OUTPUT_DIR / "high_startup_tradeoff.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def write_assessment(df: pd.DataFrame) -> None:
    lines = [
        "# High Startup-Cost Extension Assessment",
        "",
        "This extension tests whether much higher startup cost is enough to keep generators online longer and reduce short 1-2 timestep runs.",
        "",
        "The table includes the earlier lower-startup anchor points for the same two controller settings, plus the new high-startup cases.",
        "",
        "| Setting | Startup | Fuel delta % | Fuel kg | Starts | Short runs | Min SOC % | Final SOC % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in df.iterrows():
        lines.append(
            f"| {row['setting']} | {row['startup_cost_g_per_start']:.0f} | "
            f"{row['fuel_delta_vs_full_pct']:.2f} | {row['rolling_fuel_kg']:.3f} | "
            f"{int(row['rolling_starts'])} | {int(row['short_1_2_step_generator_runs'])} | "
            f"{row['rolling_min_soc_pct']:.2f} | {row['rolling_final_soc_pct']:.2f} |"
        )

    valid = df.loc[df["rolling_min_soc_pct"] >= 20.0].copy()
    best_valid_fuel = valid.sort_values("fuel_delta_vs_full_pct").iloc[0]
    best_valid_low_pulse = valid.sort_values(
        ["short_1_2_step_generator_runs", "fuel_delta_vs_full_pct"]
    ).iloc[0]

    lines.extend(
        [
            "",
            "## Readout",
            "",
            f"- Best valid fuel case in this comparison: `{best_valid_fuel['case_id']}` at {best_valid_fuel['fuel_delta_vs_full_pct']:.2f}% fuel delta, {int(best_valid_fuel['short_1_2_step_generator_runs'])} short runs, final SOC {best_valid_fuel['rolling_final_soc_pct']:.2f}%.",
            f"- Best valid low-pulse case: `{best_valid_low_pulse['case_id']}` at {best_valid_low_pulse['fuel_delta_vs_full_pct']:.2f}% fuel delta, {int(best_valid_low_pulse['short_1_2_step_generator_runs'])} short runs, final SOC {best_valid_low_pulse['rolling_final_soc_pct']:.2f}%.",
            "- Very high startup cost is not monotonic. In several cases it changes the SOC trajectory enough that fuel and pulse counts do not move smoothly.",
            "- Startup cost can reduce pulses, but pushing it very high can either increase reserve/fuel or allow deeper SOC spending depending on the horizon and SOC penalty.",
            "- This supports treating startup cost as a coarse regularization lever, not a clean anti-chatter mechanism.",
            "",
            "## Practical Implication",
            "",
            "The higher startup-cost extension does not remove the need for a direct commitment-regularity experiment. If short runs remain unacceptable, a minimum-up-time or explicit switching/stop penalty is a cleaner next test than continuing to raise startup cost.",
            "",
            "## Generated Plots",
            "",
            "- `high_startup_trends.png`",
            "- `high_startup_tradeoff.png`",
            "",
        ]
    )
    (OUTPUT_DIR / "assessment.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    df = load_combined()
    save_trend_plot(df)
    save_tradeoff_plot(df)
    write_assessment(df)
    print(f"Saved high-startup plots and assessment in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
