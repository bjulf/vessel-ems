from __future__ import annotations

import csv
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from sensitivity_common import REPO_ROOT


CONFIRMATORY_DIR = (
    REPO_ROOT
    / "analysis"
    / "output"
    / "rolling_horizon"
    / "min_up_confirmatory_baseline_sweep"
)
GUARDRAIL_DIR = (
    REPO_ROOT
    / "analysis"
    / "output"
    / "rolling_horizon"
    / "min_up_long_horizon_guardrail"
)
OUTPUT_DIR = (
    REPO_ROOT
    / "analysis"
    / "output"
    / "rolling_horizon"
    / "combined_baseline_assessment"
)
PLOTS_DIR = OUTPUT_DIR / "plots"
SELECTED_PLOTS_DIR = PLOTS_DIR / "selected_case_panels"

H16_BASELINE = "h16_startup500_softsoc10000_minup6"
H24_CONSERVATIVE = "h24_startup500_softsoc20000_minup6"
FUEL_MIN = "h12_startup500_softsoc5000_minup6"
CURRENT_H12 = "h12_startup500_softsoc10000_minup6"
LONG_H20 = "h20_startup500_softsoc10000_minup6"

SELECTED_CASES = [H16_BASELINE, H24_CONSERVATIVE, FUEL_MIN, CURRENT_H12, LONG_H20]

CASE_LABELS = {
    H16_BASELINE: "H16 C500 P10k",
    H24_CONSERVATIVE: "H24 C500 P20k",
    FUEL_MIN: "H12 C500 P5k",
    CURRENT_H12: "H12 C500 P10k",
    LONG_H20: "H20 C500 P10k",
}


def load_summary(path: Path, source: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["source_sweep"] = source
    return df


def load_combined() -> pd.DataFrame:
    frames = [
        load_summary(CONFIRMATORY_DIR / "summary.csv", "confirmatory_18_case"),
        load_summary(GUARDRAIL_DIR / "summary.csv", "long_horizon_guardrail"),
    ]
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates("case_id", keep="last")
    df["case_label"] = df["case_id"].map(CASE_LABELS).fillna(
        df.apply(
            lambda row: (
                f"H{int(row['horizon_steps'])} "
                f"C{int(row['startup_cost_g_per_start'])} "
                f"P{int(row['soft_soc_penalty_g_per_kwh'] / 1000)}k"
            ),
            axis=1,
        )
    )
    df["is_clean"] = (
        (df["nonoptimal_timeout_infeasible_local_solve_count"] == 0)
        & (df["realized_low_soc_slack_kwh"].abs() <= 1e-6)
        & (df["realized_high_soc_slack_kwh"].abs() <= 1e-6)
        & (df["shorter_than_min_up_runs"] == 0)
    )
    df["final_soc_carryover_vs_full_pp"] = df["final_soc_delta_pct_points"]
    df["fuel_rank"] = df["fuel_delta_vs_full_pct"].rank(method="min")
    df["clean_commitment_score"] = (
        10.0 * df["rolling_starts"]
        + 1.5 * df["minimum_length_runs"]
        + 0.2 * (df["final_soc_pct"] - 30.0).abs()
        + df["fuel_delta_vs_full_pct"]
    )
    df["commitment_rank"] = df["clean_commitment_score"].rank(method="min")
    return df.sort_values(
        ["horizon_steps", "startup_cost_g_per_start", "soft_soc_penalty_g_per_kwh"]
    ).reset_index(drop=True)


def write_combined_csv(df: pd.DataFrame) -> Path:
    path = OUTPUT_DIR / "combined_summary.csv"
    df.to_csv(path, index=False)
    return path


def annotate_selected(ax: plt.Axes, df: pd.DataFrame, x_col: str, y_col: str) -> None:
    selected = df[df["case_id"].isin(SELECTED_CASES)]
    for row in selected.itertuples():
        ax.annotate(
            CASE_LABELS[row.case_id],
            (getattr(row, x_col), getattr(row, y_col)),
            xytext=(7, 5),
            textcoords="offset points",
            fontsize=9,
            color="#0F172A",
        )


def plot_tradeoff(df: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(10.5, 6.8), constrained_layout=True)
    horizon_colors = {8: "#94A3B8", 12: "#2563EB", 16: "#059669", 20: "#B45309", 24: "#7C3AED"}
    penalty_markers = {5000: "o", 10000: "s", 20000: "D"}

    for (horizon, penalty), group in df.groupby(["horizon_steps", "soft_soc_penalty_g_per_kwh"]):
        ax.scatter(
            group["rolling_starts"],
            group["fuel_delta_vs_full_pct"],
            s=75 + group["startup_cost_g_per_start"] / 20.0,
            marker=penalty_markers.get(int(penalty), "o"),
            color=horizon_colors.get(int(horizon), "#334155"),
            alpha=0.82,
            edgecolor="white",
            linewidth=0.7,
            label=f"H{int(horizon)} P{int(penalty / 1000)}k",
        )

    selected = df[df["case_id"].isin(SELECTED_CASES)]
    ax.scatter(
        selected["rolling_starts"],
        selected["fuel_delta_vs_full_pct"],
        s=220,
        facecolor="none",
        edgecolor="#111827",
        linewidth=1.6,
        zorder=5,
    )
    annotate_selected(ax, df, "rolling_starts", "fuel_delta_vs_full_pct")
    ax.set_xlabel("Generator starts")
    ax.set_ylabel("Fuel penalty vs full horizon [%]")
    ax.set_title("Combined Rolling-Horizon Baseline Tradeoff")
    ax.grid(alpha=0.25)
    handles, labels = ax.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    ax.legend(unique.values(), unique.keys(), loc="upper left", ncol=2, fontsize=8, frameon=True)
    out = PLOTS_DIR / "combined_fuel_start_tradeoff.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def plot_soc_tradeoff(df: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(10.5, 6.8), constrained_layout=True)
    scatter = ax.scatter(
        df["final_soc_pct"],
        df["fuel_delta_vs_full_pct"],
        c=df["rolling_starts"],
        s=85 + df["horizon_steps"] * 4,
        cmap="viridis_r",
        alpha=0.82,
        edgecolor="white",
        linewidth=0.7,
    )
    selected = df[df["case_id"].isin(SELECTED_CASES)]
    ax.scatter(
        selected["final_soc_pct"],
        selected["fuel_delta_vs_full_pct"],
        s=230,
        facecolor="none",
        edgecolor="#111827",
        linewidth=1.6,
        zorder=5,
    )
    annotate_selected(ax, df, "final_soc_pct", "fuel_delta_vs_full_pct")
    ax.axvline(30.0, color="#64748B", linestyle="--", linewidth=1.0)
    ax.set_xlabel("Final SOC [%]")
    ax.set_ylabel("Fuel penalty vs full horizon [%]")
    ax.set_title("Fuel Cost vs Final SOC Carryover")
    ax.grid(alpha=0.25)
    cbar = fig.colorbar(scatter, ax=ax)
    cbar.set_label("Generator starts")
    out = PLOTS_DIR / "combined_fuel_final_soc_tradeoff.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def plot_case_bars(df: pd.DataFrame) -> Path:
    ordered = df.sort_values(["rolling_starts", "fuel_delta_vs_full_pct", "final_soc_pct"]).reset_index(drop=True)
    labels = [
        f"H{int(row.horizon_steps)} C{int(row.startup_cost_g_per_start)} P{int(row.soft_soc_penalty_g_per_kwh / 1000)}k"
        for row in ordered.itertuples()
    ]
    colors = ordered["case_id"].apply(
        lambda value: "#111827"
        if value == H24_CONSERVATIVE
        else ("#059669" if value == H16_BASELINE else "#64748B")
    )
    fig, axes = plt.subplots(3, 1, figsize=(13.5, 9.0), sharex=True, constrained_layout=True)
    x = range(len(ordered))
    axes[0].bar(x, ordered["fuel_delta_vs_full_pct"], color=colors, alpha=0.86)
    axes[0].set_ylabel("Fuel penalty [%]")
    axes[0].set_title("Cases Sorted by Starts, Fuel Penalty, and Final SOC")
    axes[0].grid(axis="y", alpha=0.25)

    axes[1].bar(x, ordered["rolling_starts"], color=colors, alpha=0.86)
    axes[1].set_ylabel("Starts")
    axes[1].grid(axis="y", alpha=0.25)

    axes[2].bar(x, ordered["final_soc_pct"], color=colors, alpha=0.86)
    axes[2].axhline(20.0, color="#374151", linestyle="--", linewidth=1.0)
    axes[2].set_ylabel("Final SOC [%]")
    axes[2].grid(axis="y", alpha=0.25)
    axes[2].set_xticks(list(x), labels, rotation=55, ha="right")

    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)

    out = PLOTS_DIR / "combined_case_bars.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def read_dispatch(run_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    dispatch = pd.read_csv(run_dir / "dispatch_results.csv")
    dispatch["datetime"] = pd.to_datetime(dispatch["datetime"])
    dispatch["generator"] = dispatch["generator"].astype(str)
    wide = (
        dispatch.groupby("timestep")
        .agg(
            datetime=("datetime", "first"),
            load_kw=("load_kw", "first"),
            P_ch_kw=("P_ch_kw", "first"),
            P_dis_kw=("P_dis_kw", "first"),
            soc_pct=("soc_pct", "first"),
            total_gen_kw=("Pg_kw", "sum"),
        )
        .reset_index()
    )
    wide["battery_net_kw"] = wide["P_dis_kw"] - wide["P_ch_kw"]
    return dispatch, wide


def plot_selected_timeline(df: pd.DataFrame) -> Path:
    selected = df[df["case_id"].isin(SELECTED_CASES)].set_index("case_id").loc[SELECTED_CASES].reset_index()
    fig, axes = plt.subplots(
        len(selected),
        1,
        figsize=(15.0, 2.25 * len(selected)),
        sharex=True,
        constrained_layout=True,
    )
    if len(selected) == 1:
        axes = [axes]

    for ax, row in zip(axes, selected.itertuples()):
        dispatch, wide = read_dispatch(Path(row.run_dir))
        times = wide["datetime"]
        ax.step(times, wide["soc_pct"], where="post", color="#2563EB", linewidth=1.8, label="SOC")
        ax.axhline(20.0, color="#64748B", linestyle="--", linewidth=1.0)
        ax.axhline(80.0, color="#64748B", linestyle=":", linewidth=1.0)
        ax.set_ylim(15, 85)
        ax.set_ylabel("SOC [%]")
        ax.grid(axis="y", alpha=0.22)

        twin = ax.twinx()
        for idx, (generator, group) in enumerate(dispatch.groupby("generator"), start=1):
            group = group.sort_values("timestep")
            twin.fill_between(
                times,
                idx - 0.27,
                idx + 0.27,
                where=group["u"].to_numpy() > 0.5,
                step="post",
                color="#059669" if generator == "1" else "#B45309",
                alpha=0.42,
            )
        twin.set_ylim(0.4, 2.7)
        twin.set_yticks([1, 2], labels=["G1", "G2"])

        ax.set_title(
            f"{CASE_LABELS[row.case_id]} | fuel {row.rolling_fuel_kg:.1f} kg, "
            f"delta {row.fuel_delta_vs_full_pct:.2f}%, starts {int(row.rolling_starts)}, "
            f"min/final SOC {row.minimum_soc_pct:.1f}/{row.final_soc_pct:.1f}%, "
            f"runs {row.run_lengths_steps}",
            loc="left",
            fontsize=10,
        )

    axes[-1].set_xlabel("Time")
    out = PLOTS_DIR / "selected_commitment_soc_timeline.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def plot_third_peak_focus(df: pd.DataFrame) -> Path:
    focus_cases = [H16_BASELINE, H24_CONSERVATIVE, CURRENT_H12, FUEL_MIN]
    selected = df[df["case_id"].isin(focus_cases)].set_index("case_id").loc[focus_cases].reset_index()
    start = pd.Timestamp("2026-03-02 13:00")
    end = pd.Timestamp("2026-03-02 21:00")

    fig, axes = plt.subplots(
        len(selected),
        1,
        figsize=(15.0, 2.45 * len(selected)),
        sharex=True,
        constrained_layout=True,
    )
    if len(selected) == 1:
        axes = [axes]

    for ax, row in zip(axes, selected.itertuples()):
        dispatch, wide = read_dispatch(Path(row.run_dir))
        window = wide[(wide["datetime"] >= start) & (wide["datetime"] <= end)].copy()
        gen_window = dispatch[
            (dispatch["datetime"] >= start) & (dispatch["datetime"] <= end)
        ].copy()
        times = window["datetime"]

        ax.step(times, window["load_kw"], where="post", color="#111827", linewidth=2.1, label="Load")
        ax.step(
            times,
            window["total_gen_kw"],
            where="post",
            color="#2563EB",
            linewidth=1.8,
            label="Generation",
        )
        ax.fill_between(
            times,
            0,
            window["battery_net_kw"].clip(lower=0),
            step="post",
            color="#DC2626",
            alpha=0.22,
            label="Battery discharge",
        )
        ax.fill_between(
            times,
            0,
            window["battery_net_kw"].clip(upper=0),
            step="post",
            color="#059669",
            alpha=0.20,
            label="Battery charge",
        )
        ax.set_ylabel("Power [kW]")
        ax.grid(axis="y", alpha=0.22)

        soc_ax = ax.twinx()
        soc_ax.step(times, window["soc_pct"], where="post", color="#7C3AED", linewidth=1.5, label="SOC")
        soc_ax.axhline(20.0, color="#64748B", linestyle="--", linewidth=0.8)
        soc_ax.set_ylim(15, 70)
        soc_ax.set_ylabel("SOC [%]")

        for generator, group in gen_window.groupby("generator"):
            group = group.sort_values("timestep")
            starts = group.loc[group["startup"] > 0.5, "datetime"]
            if not starts.empty:
                ax.scatter(
                    starts,
                    [window["load_kw"].max() + 18] * len(starts),
                    marker="^",
                    s=55,
                    color="#B45309" if generator == "1" else "#059669",
                    edgecolor="white",
                    linewidth=0.6,
                    zorder=5,
                )

        ax.set_title(
            f"{CASE_LABELS[row.case_id]} | runs {row.run_lengths_steps} | "
            f"fuel delta {row.fuel_delta_vs_full_pct:.2f}%, starts {int(row.rolling_starts)}, "
            f"window SOC {window['soc_pct'].min():.1f}-{window['soc_pct'].max():.1f}%",
            loc="left",
            fontsize=10,
        )

    axes[0].legend(loc="upper left", ncol=4, fontsize=8, frameon=True)
    axes[-1].set_xlabel("March 2 afternoon/evening variable peak")
    out = PLOTS_DIR / "third_peak_focused_comparison.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def copy_selected_case_panels(df: pd.DataFrame) -> list[Path]:
    SELECTED_PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for row in df[df["case_id"].isin(SELECTED_CASES)].itertuples():
        run_plots = Path(row.run_dir) / "plots"
        for name in ["rolling_horizon_dispatch_panel.png", "rolling_vs_full_horizon_comparison.png"]:
            source = run_plots / name
            if not source.exists():
                continue
            target = SELECTED_PLOTS_DIR / f"{row.case_id}_{name}"
            shutil.copy2(source, target)
            copied.append(target)
    return copied


def markdown_table(rows: pd.DataFrame) -> list[str]:
    lines = [
        "| Case | H | C | P | Fuel kg | Delta % | Starts | Min SOC % | Final SOC % | Run lengths | P95 s | Max s |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    for row in rows.itertuples():
        lines.append(
            f"| `{row.case_id}` | {int(row.horizon_steps)} | {int(row.startup_cost_g_per_start)} | "
            f"{int(row.soft_soc_penalty_g_per_kwh)} | {row.rolling_fuel_kg:.2f} | "
            f"{row.fuel_delta_vs_full_pct:.2f} | {int(row.rolling_starts)} | "
            f"{row.minimum_soc_pct:.2f} | {row.final_soc_pct:.2f} | {row.run_lengths_steps} | "
            f"{row.p95_solve_s:.3f} | {row.max_solve_s:.3f} |"
        )
    return lines


def write_assessment(df: pd.DataFrame, plot_paths: list[Path], copied_panels: list[Path]) -> Path:
    h16 = df[df["case_id"] == H16_BASELINE].iloc[0]
    h24 = df[df["case_id"] == H24_CONSERVATIVE].iloc[0]
    fuel_min = df[df["case_id"] == FUEL_MIN].iloc[0]
    selected = df[df["case_id"].isin(SELECTED_CASES)].set_index("case_id").loc[SELECTED_CASES].reset_index()
    best_fuel = df.sort_values(["fuel_delta_vs_full_pct", "rolling_starts"]).head(6)
    best_starts = df.sort_values(["rolling_starts", "fuel_delta_vs_full_pct"]).head(8)

    lines = [
        "# Combined Rolling-Horizon Baseline Assessment",
        "",
        "This combines the 18-case confirmatory sweep with the 4-case H20/H24 guardrail sweep. All 22 cases are clean on realized SOC slack, minimum-up violations, and nonoptimal/time-limited/infeasible local solves.",
        "",
        "## Main Read",
        "",
        f"`{H24_CONSERVATIVE}` is visually and operationally attractive because it has only {int(h24.rolling_starts)} starts, long commitment blocks (`{h24.run_lengths_steps}`), and a higher SOC buffer: minimum SOC {h24.minimum_soc_pct:.2f}% and final SOC {h24.final_soc_pct:.2f}%.",
        "",
        "Its strongest operational argument is the March 2 afternoon/evening variable peak: it keeps one genset committed continuously from 15:15 to 19:45, while the H16 P10k baseline splits that part of the day into two shorter blocks with an off-period before the evening spike. That makes H24 P20k look more like a cautious watchstanding policy through uncertain high-load operation.",
        "",
        f"The cost is material: {h24.rolling_fuel_kg:.2f} kg fuel and {h24.fuel_delta_vs_full_pct:.2f}% penalty versus {h16.rolling_fuel_kg:.2f} kg and {h16.fuel_delta_vs_full_pct:.2f}% for `{H16_BASELINE}`. It also ends {h24.final_soc_pct - h16.final_soc_pct:.2f} percentage points higher in SOC, so part of the impression is a more conservative energy carryover rather than pure dispatch efficiency.",
        "",
        "## Recommendation",
        "",
        f"Keep `{H16_BASELINE}` as the main thesis baseline if the baseline should be quantitatively efficient while still clean: {int(h16.rolling_starts)} starts, fuel penalty {h16.fuel_delta_vs_full_pct:.2f}%, final SOC {h16.final_soc_pct:.2f}%, and long enough commitment blocks (`{h16.run_lengths_steps}`).",
        "",
        f"Use `{H24_CONSERVATIVE}` as a conservative/visual comparison case rather than replacing the baseline. It is defensible if the narrative is operational reserve and smoothness, but it should be described as a higher-SOC, higher-fuel controller setting.",
        "",
        f"`{FUEL_MIN}` remains the fuel-minimum clean case at {fuel_min.fuel_delta_vs_full_pct:.2f}% penalty, but it has {int(fuel_min.rolling_starts)} starts and a low final SOC of {fuel_min.final_soc_pct:.2f}%, so it is less attractive as the final baseline.",
        "",
        "## Selected Cases",
        "",
        *markdown_table(selected),
        "",
        "## Best Fuel Cases",
        "",
        *markdown_table(best_fuel),
        "",
        "## Lowest-Start Cases",
        "",
        *markdown_table(best_starts),
        "",
        "## Plots",
        "",
    ]
    for path in plot_paths:
        lines.append(f"- `{path.relative_to(OUTPUT_DIR).as_posix()}`")
    lines.append("- `plots/selected_case_panels/`: copied dispatch and rolling-vs-full panels for selected cases.")
    for path in copied_panels:
        lines.append(f"- `{path.relative_to(OUTPUT_DIR).as_posix()}`")
    lines.append("")

    out = OUTPUT_DIR / "assessment.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    df = load_combined()
    summary_path = write_combined_csv(df)
    plot_paths = [
        plot_tradeoff(df),
        plot_soc_tradeoff(df),
        plot_case_bars(df),
        plot_selected_timeline(df),
        plot_third_peak_focus(df),
    ]
    copied_panels = copy_selected_case_panels(df)
    assessment_path = write_assessment(df, plot_paths, copied_panels)

    print(f"Saved {summary_path}")
    print(f"Saved {assessment_path}")
    for path in plot_paths:
        print(f"Saved {path}")
    print(f"Saved selected panels under {SELECTED_PLOTS_DIR}")


if __name__ == "__main__":
    main()
