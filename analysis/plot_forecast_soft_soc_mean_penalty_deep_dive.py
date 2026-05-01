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


def load_summary() -> pd.DataFrame:
    df = pd.read_csv(SUMMARY_CSV)
    df = df.sort_values(
        ["horizon_steps", "startup_cost_g_per_start", "soft_soc_penalty_g_per_kwh"]
    ).reset_index(drop=True)
    df["soc_floor_violation_pct_points"] = (20.0 - df["rolling_min_soc_pct"]).clip(lower=0.0)
    df["final_soc_above_40_pct_points"] = (df["rolling_final_soc_pct"] - 40.0).clip(lower=0.0)
    df["candidate_flag"] = (
        (df["rolling_min_soc_pct"] >= 20.0)
        & (df["short_1_2_step_generator_runs"] <= 3)
        & (df["fuel_delta_vs_full_pct"] <= 6.5)
        & (df["rolling_final_soc_pct"] <= 43.0)
    )
    return df


def is_dominated(row: pd.Series, df: pd.DataFrame) -> bool:
    metrics = [
        "fuel_delta_vs_full_pct",
        "rolling_starts",
        "short_1_2_step_generator_runs",
        "soc_floor_violation_pct_points",
        "final_soc_above_40_pct_points",
    ]
    others = df.drop(index=row.name)
    better_or_equal = (others[metrics] <= row[metrics]).all(axis=1)
    strictly_better = (others[metrics] < row[metrics]).any(axis=1)
    return bool((better_or_equal & strictly_better).any())


def pareto_table(df: pd.DataFrame) -> pd.DataFrame:
    pareto = df.loc[[not is_dominated(row, df) for _, row in df.iterrows()]].copy()
    return pareto.sort_values(
        ["fuel_delta_vs_full_pct", "short_1_2_step_generator_runs", "rolling_starts"]
    )


def save_pareto_plot(df: pd.DataFrame) -> None:
    pareto = pareto_table(df)
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(10.5, 7), constrained_layout=True)
    markers = {12: "o", 16: "s"}

    for horizon, part in df.groupby("horizon_steps"):
        ax.scatter(
            part["short_1_2_step_generator_runs"],
            part["fuel_delta_vs_full_pct"],
            c=part["rolling_final_soc_pct"],
            cmap="viridis",
            marker=markers[int(horizon)],
            s=95,
            edgecolor="#111827",
            linewidth=0.5,
            alpha=0.72,
            label=f"H={int(horizon)}",
            vmin=df["rolling_final_soc_pct"].min(),
            vmax=df["rolling_final_soc_pct"].max(),
        )

    ax.scatter(
        pareto["short_1_2_step_generator_runs"],
        pareto["fuel_delta_vs_full_pct"],
        facecolors="none",
        edgecolors="#DC2626",
        linewidths=2.0,
        s=190,
        label="Non-dominated",
    )
    for _, row in pareto.iterrows():
        ax.annotate(
            f"H{int(row['horizon_steps'])} C{int(row['startup_cost_g_per_start'])} S{int(row['soft_soc_penalty_g_per_kwh'])}",
            (row["short_1_2_step_generator_runs"], row["fuel_delta_vs_full_pct"]),
            xytext=(7, 6),
            textcoords="offset points",
            fontsize=9,
        )

    ax.axvline(3, color="#64748B", linestyle="--", linewidth=1.1)
    ax.axhline(6.5, color="#64748B", linestyle="--", linewidth=1.1)
    ax.set_title("Fuel vs Short Generator Runs", fontsize=17, fontweight="bold")
    ax.set_xlabel("Short 1-2 timestep generator runs", fontsize=12)
    ax.set_ylabel("Fuel delta vs offline [%]", fontsize=12)
    ax.tick_params(axis="both", labelsize=11)
    ax.legend(loc="upper left", fontsize=10)
    cbar = fig.colorbar(ax.collections[0], ax=ax)
    cbar.set_label("Final SOC [%]", fontsize=11)
    fig.savefig(SWEEP_DIR / "pareto_fuel_vs_short_runs.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def save_parameter_effects(df: pd.DataFrame) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    metrics = [
        ("fuel_delta_vs_full_pct", "Fuel delta [%]"),
        ("rolling_final_soc_pct", "Final SOC [%]"),
        ("short_1_2_step_generator_runs", "Short runs"),
        ("rolling_min_soc_pct", "Minimum SOC [%]"),
    ]
    horizons = sorted(df["horizon_steps"].unique())
    fig, axes = plt.subplots(
        len(metrics),
        len(horizons),
        figsize=(13.5, 12.5),
        sharex=True,
        constrained_layout=True,
    )

    for col, horizon in enumerate(horizons):
        part_h = df.loc[df["horizon_steps"] == horizon]
        for row_idx, (metric, ylabel) in enumerate(metrics):
            ax = axes[row_idx, col]
            for startup, part in part_h.groupby("startup_cost_g_per_start"):
                part = part.sort_values("soft_soc_penalty_g_per_kwh")
                ax.plot(
                    part["soft_soc_penalty_g_per_kwh"],
                    part[metric],
                    marker="o",
                    linewidth=2,
                    label=f"C_start={startup:.0f}",
                )
            ax.set_xscale("log")
            ax.set_ylabel(ylabel, fontsize=11)
            ax.grid(alpha=0.25)
            ax.tick_params(axis="both", labelsize=10)
            if row_idx == 0:
                ax.set_title(f"H={int(horizon)}", fontsize=15)
            if metric == "rolling_min_soc_pct":
                ax.axhline(20.0, color="#DC2626", linestyle="--", linewidth=1.0)
            if metric == "rolling_final_soc_pct":
                ax.axhline(40.0, color="#64748B", linestyle="--", linewidth=1.0)
            if row_idx == len(metrics) - 1:
                ax.set_xlabel("Soft SOC penalty [g/kWh]", fontsize=11)
            if row_idx == 0 and col == len(horizons) - 1:
                ax.legend(loc="upper left", fontsize=9)

    fig.suptitle("Parameter Effects Under Mean Soft-SOC Scaling", fontsize=18, fontweight="bold")
    fig.savefig(SWEEP_DIR / "parameter_effects_by_horizon.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def save_soc_tradeoff(df: pd.DataFrame) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.8), constrained_layout=True)

    for ax, horizon in zip(axes, sorted(df["horizon_steps"].unique())):
        part = df.loc[df["horizon_steps"] == horizon]
        scatter = ax.scatter(
            part["rolling_final_soc_pct"],
            part["fuel_delta_vs_full_pct"],
            c=part["startup_cost_g_per_start"],
            s=part["short_1_2_step_generator_runs"].mul(18).add(80),
            cmap="cividis",
            edgecolor="#111827",
            linewidth=0.6,
        )
        for _, row in part.iterrows():
            ax.annotate(
                f"S{int(row['soft_soc_penalty_g_per_kwh'])}",
                (row["rolling_final_soc_pct"], row["fuel_delta_vs_full_pct"]),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=8,
            )
        ax.axvline(40.0, color="#64748B", linestyle="--", linewidth=1.0)
        ax.set_title(f"H={int(horizon)}", fontsize=15)
        ax.set_xlabel("Final SOC [%]", fontsize=12)
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Fuel delta vs offline [%]", fontsize=12)
    cbar = fig.colorbar(scatter, ax=axes.ravel().tolist())
    cbar.set_label("Startup cost [g/start]", fontsize=11)
    fig.suptitle("SOC Reserve vs Fuel Cost", fontsize=17, fontweight="bold")
    fig.savefig(SWEEP_DIR / "soc_reserve_vs_fuel.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def save_candidate_map(df: pd.DataFrame) -> None:
    horizons = sorted(df["horizon_steps"].unique())
    fig, axes = plt.subplots(1, len(horizons), figsize=(7.0 * len(horizons), 5.4), constrained_layout=True)
    if len(horizons) == 1:
        axes = [axes]

    for ax, horizon in zip(axes, horizons):
        part = df.loc[df["horizon_steps"] == horizon].copy()
        pivot = part.pivot(
            index="soft_soc_penalty_g_per_kwh",
            columns="startup_cost_g_per_start",
            values="candidate_flag",
        ).sort_index(ascending=False)
        ax.imshow(pivot.to_numpy(dtype=float), cmap="Greens", vmin=0, vmax=1, aspect="auto")
        ax.set_title(f"H={int(horizon)} candidate region", fontsize=15)
        ax.set_xticks(range(len(pivot.columns)), labels=[f"{v:.0f}" for v in pivot.columns])
        ax.set_yticks(range(len(pivot.index)), labels=[f"{v:.0f}" for v in pivot.index])
        ax.set_xlabel("Startup cost [g/start]", fontsize=12)
        ax.set_ylabel("Soft SOC penalty [g/kWh]", fontsize=12)
        for y_idx, soc_penalty in enumerate(pivot.index):
            for x_idx, startup in enumerate(pivot.columns):
                row = part.loc[
                    (part["soft_soc_penalty_g_per_kwh"] == soc_penalty)
                    & (part["startup_cost_g_per_start"] == startup)
                ].iloc[0]
                label = (
                    f"{row['fuel_delta_vs_full_pct']:.1f}%\n"
                    f"{int(row['short_1_2_step_generator_runs'])} short\n"
                    f"{row['rolling_min_soc_pct']:.0f}/{row['rolling_final_soc_pct']:.0f}%"
                )
                ax.text(x_idx, y_idx, label, ha="center", va="center", fontsize=9, color="#111827")

    fig.suptitle(
        "Candidate Map: Fuel <= 6.5%, Short Runs <= 3, Min SOC >= 20%, Final SOC <= 43%",
        fontsize=16,
        fontweight="bold",
    )
    fig.savefig(SWEEP_DIR / "candidate_region_map.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def write_deep_assessment(df: pd.DataFrame) -> None:
    pareto = pareto_table(df)
    candidates = df.loc[df["candidate_flag"]].sort_values(
        ["fuel_delta_vs_full_pct", "short_1_2_step_generator_runs", "rolling_starts"]
    )
    best_valid_fuel = df.loc[df["rolling_min_soc_pct"] >= 20.0].sort_values("fuel_delta_vs_full_pct").iloc[0]
    best_low_pulse_valid = df.loc[
        (df["rolling_min_soc_pct"] >= 20.0) & (df["short_1_2_step_generator_runs"] <= 2)
    ].sort_values("fuel_delta_vs_full_pct").iloc[0]
    best_h12 = df.loc[
        (df["horizon_steps"] == 12) & (df["rolling_min_soc_pct"] >= 20.0)
    ].sort_values("fuel_delta_vs_full_pct").iloc[0]
    best_h16 = df.loc[
        (df["horizon_steps"] == 16) & (df["rolling_min_soc_pct"] >= 20.0)
    ].sort_values("fuel_delta_vs_full_pct").iloc[0]

    lines = [
        "# Deep Assessment: Forecast Mean Soft-SOC Tuning",
        "",
        "Scope: operational 15-minute average profile, moving-average forecast with window 4, H=12/16, mean-normalized soft SOC penalty.",
        "",
        "The screen confirms that normalized SOC penalty reduces excessive terminal charge compared with the old summed penalty, but tuning still exposes a three-way tradeoff: fuel, SOC reserve, and short generator pulses.",
        "",
        "## Main Read",
        "",
        f"- Best fuel while keeping realized minimum SOC at or above 20%: `{best_valid_fuel['case_id']}` with {best_valid_fuel['fuel_delta_vs_full_pct']:.2f}% fuel delta, {int(best_valid_fuel['rolling_starts'])} starts, {int(best_valid_fuel['short_1_2_step_generator_runs'])} short runs, and final SOC {best_valid_fuel['rolling_final_soc_pct']:.2f}%.",
        f"- Best low-pulse case with realized minimum SOC at or above 20% and at most two short runs: `{best_low_pulse_valid['case_id']}` with {best_low_pulse_valid['fuel_delta_vs_full_pct']:.2f}% fuel delta, {int(best_low_pulse_valid['rolling_starts'])} starts, {int(best_low_pulse_valid['short_1_2_step_generator_runs'])} short runs, and final SOC {best_low_pulse_valid['rolling_final_soc_pct']:.2f}%.",
        f"- Best valid H=12 case: `{best_h12['case_id']}` at {best_h12['fuel_delta_vs_full_pct']:.2f}% fuel delta, {int(best_h12['short_1_2_step_generator_runs'])} short runs, final SOC {best_h12['rolling_final_soc_pct']:.2f}%.",
        f"- Best valid H=16 case: `{best_h16['case_id']}` at {best_h16['fuel_delta_vs_full_pct']:.2f}% fuel delta, {int(best_h16['short_1_2_step_generator_runs'])} short runs, final SOC {best_h16['rolling_final_soc_pct']:.2f}%.",
        "",
        "## Candidate Region",
        "",
        "Using a pragmatic filter of fuel delta <= 6.5%, short runs <= 3, minimum SOC >= 20%, and final SOC <= 43%, the strongest candidates are:",
        "",
        "| Case | H | Startup | SOC penalty | Fuel delta % | Starts | Short runs | Min SOC % | Final SOC % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in candidates.iterrows():
        lines.append(
            f"| {row['case_id']} | {int(row['horizon_steps'])} | {row['startup_cost_g_per_start']:.0f} | "
            f"{row['soft_soc_penalty_g_per_kwh']:.0f} | {row['fuel_delta_vs_full_pct']:.2f} | "
            f"{int(row['rolling_starts'])} | {int(row['short_1_2_step_generator_runs'])} | "
            f"{row['rolling_min_soc_pct']:.2f} | {row['rolling_final_soc_pct']:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Non-Dominated Cases",
            "",
            "A case is treated as dominated if another case is no worse on fuel delta, starts, short runs, SOC floor violation, and final SOC above 40%, and strictly better on at least one of those metrics.",
            "",
            "| Case | H | Startup | SOC penalty | Fuel delta % | Starts | Short runs | SOC floor violation pp | Final SOC % |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in pareto.iterrows():
        lines.append(
            f"| {row['case_id']} | {int(row['horizon_steps'])} | {row['startup_cost_g_per_start']:.0f} | "
            f"{row['soft_soc_penalty_g_per_kwh']:.0f} | {row['fuel_delta_vs_full_pct']:.2f} | "
            f"{int(row['rolling_starts'])} | {int(row['short_1_2_step_generator_runs'])} | "
            f"{row['soc_floor_violation_pct_points']:.2f} | {row['rolling_final_soc_pct']:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Very low mean SOC penalty, especially 250 g/kWh, can make fuel look excellent because the controller is allowed to borrow too aggressively from the battery. Several of those cases fall below the 20% preferred SOC floor, so they should not be treated as clean operating candidates unless the thesis explicitly allows preferred-band violations.",
            "- Higher startup cost generally reduces starts and short pulses, but it is not monotonic across all SOC penalties because the rolling forecast and SOC penalty can change when charging becomes attractive.",
            "- Raising the mean SOC penalty protects minimum SOC but tends to increase final SOC and fuel. This is most visible around 5000-10000 g/kWh, where pulse counts can improve but the battery reserve becomes more conservative.",
            "- H=12 gives the clearest low-fuel balanced candidate in this grid. H=16 can produce fewer pulses at high startup cost, but the better low-pulse H=16 cases carry more final SOC and fuel.",
            "",
            "## Where To Look Next",
            "",
            "1. Refine around the candidate region instead of widening the full grid: H=12 with startup 500-2500 and SOC penalty 7500-12500; H=16 with startup 1500-3000 and SOC penalty 750-2000.",
            "2. Add a small minimum-up-time or switching penalty experiment. Startup cost alone reduces pulses only indirectly; the remaining 1-2 timestep runs are a commitment-regularity issue.",
            "3. Consider asymmetric soft SOC penalties. A higher low-SOC penalty and lower high-SOC penalty could protect reserve without rewarding excessive final charge as strongly.",
            "4. Add a terminal-value term or final-SOC accounting in the KPI comparison. Some low-fuel cases partly win by ending with a lower battery reserve than other cases.",
            "5. Check whether forecast bias is driving unnecessary charging. The moving-average forecast may understate/overstate load around transitions, so forecast diagnostics around pulse windows are worth inspecting before adding more MILP constraints.",
            "",
            "## Generated Diagnostic Plots",
            "",
            "- `pareto_fuel_vs_short_runs.png`",
            "- `parameter_effects_by_horizon.png`",
            "- `soc_reserve_vs_fuel.png`",
            "- `candidate_region_map.png`",
            "- Existing heatmaps: `heatmap_fuel_delta_pct.png`, `heatmap_starts.png`, `heatmap_short_runs.png`, `heatmap_final_soc.png`",
            "",
            "Every case also has `plots/rolling_horizon_dispatch_panel.png` and `plots/rolling_vs_full_horizon_comparison.png` in its run directory.",
            "",
        ]
    )
    (SWEEP_DIR / "deep_assessment.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    df = load_summary()
    save_pareto_plot(df)
    save_parameter_effects(df)
    save_soc_tradeoff(df)
    save_candidate_map(df)
    write_deep_assessment(df)
    print(f"Saved deep-dive diagnostics in {SWEEP_DIR}")


if __name__ == "__main__":
    main()
