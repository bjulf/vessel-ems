from __future__ import annotations

import argparse
from pathlib import Path
import sys
from textwrap import dedent

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
ANALYSIS_DIR = SCRIPT_DIR.parent
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))

from sensitivity_common import REPO_ROOT


OUTPUT_DIR = REPO_ROOT / "analysis" / "output" / "rolling_horizon" / "oracle_operational_tuning_screen"
SUMMARY_CSV = OUTPUT_DIR / "summary.csv"
PLOTS_DIR = OUTPUT_DIR / "plots"

TITLE_COLOR = "#111827"
GRID_COLOR = "#CBD5E1"
SOFT_COLOR = "#2563EB"
TERM_COLOR = "#C2410C"
BEST_COLOR = "#15803D"
REFERENCE_COLOR = "#64748B"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compose metrics and thesis-candidate plots from the oracle operational tuning screen."
    )
    parser.add_argument(
        "--summary-csv",
        type=Path,
        default=SUMMARY_CSV,
        help="Path to oracle tuning screen summary.csv.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory for composed CSV, plots, and assessment markdown.",
    )
    return parser.parse_args()


def parse_case_id(case_id: str) -> dict[str, str]:
    parts = case_id.split("_")
    parsed: dict[str, str] = {"strategy": parts[0]}
    for part in parts[1:]:
        if part.startswith("h"):
            parsed["horizon"] = part[1:]
        elif part.startswith("soc"):
            parsed["soc_min"] = part[3:]
        elif part.startswith("t"):
            parsed["terminal_target"] = part[1:]
        elif part.startswith("p"):
            parsed["penalty"] = part[1:]
        elif part.startswith("c"):
            parsed["startup"] = part[1:]
    return parsed


def case_label(case_id: str, *, multiline: bool = False) -> str:
    parsed = parse_case_id(case_id)
    horizon = parsed.get("horizon", "?")
    penalty = parsed.get("penalty", "?")
    startup = parsed.get("startup", "?")
    if parsed["strategy"] == "soft":
        soc = parsed.get("soc_min", "?")
        if multiline:
            return f"soft H={horizon}\nSOC min {soc}%\nSOC pen {penalty}, start {startup}"
        return f"soft H={horizon}, SOC {soc}%, pen {penalty}, start {startup}"
    target = parsed.get("terminal_target", "?")
    if multiline:
        return f"terminal H={horizon}\ntarget {target}%\nterm pen {penalty}, start {startup}"
    return f"terminal H={horizon}, target {target}%, pen {penalty}, start {startup}"


def to_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = [
        "horizon_steps",
        "startup_cost_g",
        "preferred_soc_min",
        "soft_soc_penalty_g_per_kwh",
        "terminal_soc_target",
        "terminal_slack_penalty_g_per_kwh",
        "rolling_fuel_kg",
        "rolling_starts",
        "rolling_min_soc_pct",
        "rolling_final_soc_pct",
        "fuel_delta_vs_full_kg",
        "fuel_delta_vs_full_pct",
        "starts_delta_vs_full",
        "full_fuel_kg",
        "full_starts",
        "median_solve_s",
        "p95_solve_s",
        "max_solve_s",
        "nonoptimal_solves",
        "tail_padded_solves",
        "wall_clock_s",
        "realized_low_soc_slack_kwh",
        "local_low_soc_slack_kwh",
        "terminal_slack_kwh",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def classify_cases(summary: pd.DataFrame) -> pd.DataFrame:
    df = to_numeric_columns(summary.copy())
    df["horizon_hours"] = df["horizon_steps"] * 0.25
    df["rank_by_fuel"] = df["rolling_fuel_kg"].rank(method="first").astype(int)
    best_fuel = df["rolling_fuel_kg"].min()
    baseline_row = df.loc[df["case_id"].eq("soft_h24_soc20_p1000_c1000")]
    baseline_fuel = float(baseline_row["rolling_fuel_kg"].iloc[0]) if not baseline_row.empty else np.nan
    df["fuel_delta_vs_best_kg"] = df["rolling_fuel_kg"] - best_fuel
    df["fuel_delta_vs_screen_baseline_kg"] = df["rolling_fuel_kg"] - baseline_fuel

    def family(row: pd.Series) -> str:
        if row["strategy"] == "terminal_reserve":
            return "terminal reserve"
        if row["horizon_steps"] != 24:
            return "horizon length"
        if pd.notna(row["preferred_soc_min"]) and abs(row["preferred_soc_min"] - 0.20) > 1e-9:
            return "preferred SOC minimum"
        if pd.notna(row["soft_soc_penalty_g_per_kwh"]) and abs(row["soft_soc_penalty_g_per_kwh"] - 1000.0) > 1e-9:
            return "soft SOC penalty"
        if pd.notna(row["startup_cost_g"]) and abs(row["startup_cost_g"] - 1000.0) > 1e-9:
            return "startup penalty"
        return "soft baseline"

    df["sweep_family"] = df.apply(family, axis=1)
    df["case_label"] = df["case_id"].map(case_label)
    return df.sort_values(["rank_by_fuel", "case_id"]).reset_index(drop=True)


def load_dispatch_timeseries(cases: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for _, row in cases.iterrows():
        run_dir = Path(str(row["run_dir"]))
        path = run_dir / "dispatch_results.csv"
        if not path.exists():
            continue
        dispatch = pd.read_csv(path, parse_dates=["datetime"])
        grouped = (
            dispatch.groupby(["timestep", "datetime"], as_index=False)
            .agg(
                load_kw=("load_kw", "first"),
                total_generation_kw=("Pg_kw", "sum"),
                committed_generators=("u", "sum"),
                generator_starts=("startup", "sum"),
                fuel_gph=("fuel_gph", "sum"),
                charge_kw=("P_ch_kw", "first"),
                discharge_kw=("P_dis_kw", "first"),
                energy_kwh=("E_kwh", "first"),
                soc_pct=("soc_pct", "first"),
            )
        )
        grouped.insert(0, "case_id", row["case_id"])
        grouped.insert(1, "strategy", row["strategy"])
        grouped.insert(2, "sweep_family", row["sweep_family"])
        grouped.insert(3, "horizon_steps", row["horizon_steps"])
        frames.append(grouped)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def configure_axis(ax: plt.Axes) -> None:
    ax.grid(True, color=GRID_COLOR, alpha=0.45, linewidth=0.8)
    ax.tick_params(labelsize=10)
    for spine in ax.spines.values():
        spine.set_color("#CBD5E1")


def save_ranked_fuel_plot(cases: pd.DataFrame, path: Path) -> None:
    df = cases.sort_values("rolling_fuel_kg", ascending=True)
    colors = [TERM_COLOR if strategy == "terminal_reserve" else SOFT_COLOR for strategy in df["strategy"]]
    colors[0] = BEST_COLOR
    labels = [case_label(case_id, multiline=True) for case_id in df["case_id"]]

    fig, ax = plt.subplots(figsize=(12.4, 9.0))
    bars = ax.barh(labels, df["fuel_delta_vs_full_pct"], color=colors, alpha=0.88)
    ax.invert_yaxis()
    ax.axvline(0, color=REFERENCE_COLOR, linewidth=1.0)
    ax.set_xlabel("Fuel penalty vs full-horizon benchmark (%)", fontsize=12)
    ax.set_title("Oracle rolling-horizon tuning screen ranked by fuel", fontsize=16, color=TITLE_COLOR, pad=12)
    configure_axis(ax)
    for bar, (_, row) in zip(bars, df.iterrows()):
        ax.text(
            bar.get_width() + 0.15,
            bar.get_y() + bar.get_height() / 2,
            f"{row['rolling_fuel_kg']:.1f} kg, {int(row['rolling_starts'])} starts",
            va="center",
            fontsize=9.5,
            color=TITLE_COLOR,
        )
    ax.set_xlim(0, df["fuel_delta_vs_full_pct"].max() + 1.0)
    legend = [
        Line2D([0], [0], color=BEST_COLOR, lw=8, label="lowest fuel case"),
        Line2D([0], [0], color=SOFT_COLOR, lw=8, label="soft SOC band"),
        Line2D([0], [0], color=TERM_COLOR, lw=8, label="terminal reserve"),
    ]
    ax.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=10, frameon=False)
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_sweep_panel(
    ax: plt.Axes,
    df: pd.DataFrame,
    x: str,
    title: str,
    xlabel: str,
    *,
    x_scale_pct: bool = False,
) -> None:
    if df.empty:
        ax.set_axis_off()
        return
    ordered = df.sort_values(x)
    xvals = ordered[x] * 100.0 if x_scale_pct else ordered[x]
    ax.plot(xvals, ordered["fuel_delta_vs_full_pct"], marker="o", color=SOFT_COLOR, linewidth=2.2, label="fuel delta")
    ax.set_title(title, fontsize=13, color=TITLE_COLOR)
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel("Fuel delta (%)", fontsize=11, color=SOFT_COLOR)
    ax.tick_params(axis="y", labelcolor=SOFT_COLOR)
    configure_axis(ax)

    ax2 = ax.twinx()
    ax2.plot(xvals, ordered["rolling_starts"], marker="s", color="#7C2D12", linewidth=1.8, label="starts")
    ax2.plot(xvals, ordered["rolling_final_soc_pct"], marker="^", color="#047857", linewidth=1.8, label="final SOC")
    ax2.set_ylabel("Starts / final SOC (%)", fontsize=11)
    ax2.tick_params(labelsize=10)
    for spine in ax2.spines.values():
        spine.set_color("#CBD5E1")


def save_sweep_tradeoff_plot(cases: pd.DataFrame, path: Path) -> None:
    soft = cases[cases["strategy"].eq("soft_band")].copy()
    baseline_filters = (
        soft["preferred_soc_min"].fillna(-1).eq(0.20)
        & soft["soft_soc_penalty_g_per_kwh"].fillna(-1).eq(1000.0)
        & soft["startup_cost_g"].fillna(-1).eq(1000.0)
    )
    horizon = soft[baseline_filters]
    preferred_soc = soft[
        soft["horizon_steps"].eq(24)
        & soft["soft_soc_penalty_g_per_kwh"].fillna(-1).eq(1000.0)
        & soft["startup_cost_g"].fillna(-1).eq(1000.0)
    ]
    soft_penalty = soft[
        soft["horizon_steps"].eq(24)
        & soft["preferred_soc_min"].fillna(-1).eq(0.20)
        & soft["startup_cost_g"].fillna(-1).eq(1000.0)
    ]
    startup = soft[
        soft["horizon_steps"].eq(24)
        & soft["preferred_soc_min"].fillna(-1).eq(0.20)
        & soft["soft_soc_penalty_g_per_kwh"].fillna(-1).eq(1000.0)
    ]
    terminal = cases[cases["strategy"].eq("terminal_reserve")].sort_values("terminal_slack_penalty_g_per_kwh")

    fig, axes = plt.subplots(2, 3, figsize=(15, 8.8))
    plot_sweep_panel(axes[0, 0], horizon, "horizon_hours", "Horizon length", "Local horizon (h)")
    plot_sweep_panel(
        axes[0, 1],
        preferred_soc,
        "preferred_soc_min",
        "Preferred SOC minimum",
        "Preferred SOC minimum (%)",
        x_scale_pct=True,
    )
    plot_sweep_panel(axes[0, 2], soft_penalty, "soft_soc_penalty_g_per_kwh", "Soft SOC penalty", "Penalty (g/kWh)")
    plot_sweep_panel(axes[1, 0], startup, "startup_cost_g", "Startup penalty", "Startup penalty (g/start)")

    ax = axes[1, 1]
    if terminal.empty:
        ax.set_axis_off()
    else:
        xvals = terminal["terminal_slack_penalty_g_per_kwh"]
        ax.plot(xvals, terminal["fuel_delta_vs_full_pct"], marker="o", color=TERM_COLOR, linewidth=2.2)
        ax.set_title("Terminal reserve penalty", fontsize=13, color=TITLE_COLOR)
        ax.set_xlabel("Terminal slack penalty (g/kWh)", fontsize=11)
        ax.set_ylabel("Fuel delta (%)", fontsize=11, color=TERM_COLOR)
        ax.tick_params(axis="y", labelcolor=TERM_COLOR)
        configure_axis(ax)
        ax2 = ax.twinx()
        ax2.plot(xvals, terminal["rolling_starts"], marker="s", color="#7C2D12", linewidth=1.8)
        ax2.plot(xvals, terminal["nonoptimal_solves"], marker="x", color="#991B1B", linewidth=1.8)
        ax2.set_ylabel("Starts / non-opt solves", fontsize=11)
        ax2.tick_params(labelsize=10)
        for spine in ax2.spines.values():
            spine.set_color("#CBD5E1")

    ax = axes[1, 2]
    scatter_colors = cases["strategy"].map({"soft_band": SOFT_COLOR, "terminal_reserve": TERM_COLOR})
    sizes = 45 + cases["rolling_starts"] * 12
    ax.scatter(
        cases["rolling_final_soc_pct"],
        cases["fuel_delta_vs_full_pct"],
        s=sizes,
        c=scatter_colors,
        alpha=0.78,
        edgecolors="white",
        linewidths=0.8,
    )
    for _, row in cases.iterrows():
        if row["case_id"] in {
            "soft_h24_soc20_p350_c1000",
            "soft_h24_soc20_p1000_c1000",
            "soft_h72_soc20_p1000_c1000",
            "term_h24_t20_p1000_c1000",
        }:
            ax.annotate(
                case_label(row["case_id"]),
                (row["rolling_final_soc_pct"], row["fuel_delta_vs_full_pct"]),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=8.5,
            )
    ax.set_title("Fuel vs final reserve", fontsize=13, color=TITLE_COLOR)
    ax.set_xlabel("Final SOC (%)", fontsize=11)
    ax.set_ylabel("Fuel delta (%)", fontsize=11)
    configure_axis(ax)

    legend = [
        Line2D([0], [0], color=SOFT_COLOR, marker="o", lw=2, label="fuel delta"),
        Line2D([0], [0], color="#7C2D12", marker="s", lw=2, label="starts"),
        Line2D([0], [0], color="#047857", marker="^", lw=2, label="final SOC"),
    ]
    fig.legend(handles=legend, loc="lower center", ncol=3, frameon=False, fontsize=11)
    fig.suptitle("Oracle tuning sweep tradeoffs", fontsize=17, color=TITLE_COLOR, y=0.985)
    fig.tight_layout(rect=[0, 0.04, 1, 0.96])
    fig.savefig(path, dpi=220)
    plt.close(fig)


def save_soc_profiles_plot(timeseries: pd.DataFrame, path: Path) -> None:
    selected = [
        "soft_h24_soc20_p350_c1000",
        "soft_h24_soc20_p1000_c1000",
        "soft_h48_soc20_p1000_c1000",
        "soft_h72_soc20_p1000_c1000",
        "term_h24_t20_p350_c1000",
    ]
    available = [case for case in selected if case in set(timeseries["case_id"])]
    if not available:
        return
    palette = {
        "soft_h24_soc20_p350_c1000": BEST_COLOR,
        "soft_h24_soc20_p1000_c1000": SOFT_COLOR,
        "soft_h48_soc20_p1000_c1000": "#9333EA",
        "soft_h72_soc20_p1000_c1000": "#0891B2",
        "term_h24_t20_p350_c1000": TERM_COLOR,
    }
    fig, ax = plt.subplots(figsize=(14, 6.6))
    for case_id in available:
        df = timeseries[timeseries["case_id"].eq(case_id)].sort_values("datetime")
        ax.plot(df["datetime"], df["soc_pct"], label=case_label(case_id), linewidth=2.0, color=palette[case_id])
    ax.axhline(20, color="#475569", linewidth=1.1, linestyle="--", label="20% SOC")
    ax.axhline(80, color="#475569", linewidth=1.1, linestyle=":", label="80% SOC")
    ax.set_ylabel("SOC (%)", fontsize=12)
    ax.set_title("SOC trajectories for representative oracle cases", fontsize=16, color=TITLE_COLOR, pad=12)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d\n%H:%M"))
    configure_axis(ax)
    ax.legend(loc="upper left", ncol=2, fontsize=9.5, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def save_solve_profile_plot(cases: pd.DataFrame, path: Path) -> None:
    df = cases.sort_values("p95_solve_s", ascending=True)
    labels = [case_label(case_id, multiline=True) for case_id in df["case_id"]]
    colors = [TERM_COLOR if strategy == "terminal_reserve" else SOFT_COLOR for strategy in df["strategy"]]
    fig, ax = plt.subplots(figsize=(12, 7.5))
    y = np.arange(len(df))
    ax.barh(y - 0.18, df["median_solve_s"], height=0.34, color="#94A3B8", label="median")
    ax.barh(y + 0.18, df["p95_solve_s"], height=0.34, color=colors, label="p95")
    ax.scatter(df["max_solve_s"], y, color="#991B1B", s=35, marker="x", label="max")
    for idx, (_, row) in enumerate(df.iterrows()):
        if row["nonoptimal_solves"] > 0:
            ax.text(
                max(row["p95_solve_s"], row["median_solve_s"]) * 1.08,
                idx,
                f"{int(row['nonoptimal_solves'])} non-opt",
                va="center",
                fontsize=9.5,
                color="#991B1B",
            )
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xscale("log")
    ax.set_xlabel("Local solve time (s, log scale)", fontsize=12)
    ax.set_title("Local MILP solve-time profile", fontsize=16, color=TITLE_COLOR, pad=12)
    configure_axis(ax)
    ax.legend(loc="lower right", fontsize=10, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def write_assessment(cases: pd.DataFrame, output_path: Path) -> None:
    ranked = cases.sort_values("rolling_fuel_kg")
    best = ranked.iloc[0]
    baseline = cases.loc[cases["case_id"].eq("soft_h24_soc20_p1000_c1000")].iloc[0]
    full_fuel = float(cases["full_fuel_kg"].dropna().iloc[0])
    full_starts = int(cases["full_starts"].dropna().iloc[0])

    horizon = cases[cases["sweep_family"].eq("horizon length") | cases["sweep_family"].eq("soft baseline")].sort_values(
        "horizon_steps"
    )
    preferred = cases[
        cases["sweep_family"].eq("preferred SOC minimum") | cases["sweep_family"].eq("soft baseline")
    ].sort_values("preferred_soc_min")
    soft_penalty = cases[
        cases["sweep_family"].eq("soft SOC penalty") | cases["sweep_family"].eq("soft baseline")
    ].sort_values("soft_soc_penalty_g_per_kwh")
    startup = cases[
        cases["sweep_family"].eq("startup penalty") | cases["sweep_family"].eq("soft baseline")
    ].sort_values("startup_cost_g")
    terminal = cases[cases["sweep_family"].eq("terminal reserve")].sort_values("terminal_slack_penalty_g_per_kwh")

    lines = [
        "# Oracle Operational Tuning Screen Assessment",
        "",
        f"Completed cases assessed: {len(cases)}. Full-horizon benchmark reference is {full_fuel:.3f} kg fuel and {full_starts} starts.",
        "",
        "## Main readout",
        "",
        (
            f"- Lowest rolling-horizon fuel is `{best['case_id']}` at {best['rolling_fuel_kg']:.3f} kg, "
            f"{best['fuel_delta_vs_full_pct']:.2f}% above the full-horizon benchmark, with "
            f"{int(best['rolling_starts'])} starts and final SOC {best['rolling_final_soc_pct']:.2f}%."
        ),
        (
            f"- The screen baseline `{baseline['case_id']}` uses {baseline['rolling_fuel_kg']:.3f} kg, "
            f"{baseline['fuel_delta_vs_full_pct']:.2f}% above the full-horizon benchmark, with "
            f"{int(baseline['rolling_starts'])} starts and final SOC {baseline['rolling_final_soc_pct']:.2f}%."
        ),
        (
            f"- The best case saves {baseline['rolling_fuel_kg'] - best['rolling_fuel_kg']:.3f} kg "
            "relative to the screen baseline, so this screen is tuning small-to-moderate controller behavior rather "
            "than changing the fundamental gap to the offline benchmark."
        ),
        "",
        "## Sweep lessons",
        "",
    ]

    if len(horizon) > 1:
        h24 = horizon.loc[horizon["horizon_steps"].eq(24)].iloc[0]
        hmax = horizon.iloc[-1]
        lines.append(
            f"- Longer oracle horizons did not improve realized fuel in this screen. H=24 gives {h24['fuel_delta_vs_full_pct']:.2f}% "
            f"fuel delta, while H={int(hmax['horizon_steps'])} rises to {hmax['fuel_delta_vs_full_pct']:.2f}% and ends at "
            f"{hmax['rolling_final_soc_pct']:.2f}% SOC. The longer controller is carrying more reserve instead of converting "
            "the extra foresight into lower fuel."
        )
    if len(preferred) > 1:
        low = preferred.iloc[0]
        high = preferred.iloc[-1]
        lines.append(
            f"- Raising the preferred lower SOC band from {low['preferred_soc_min'] * 100:.0f}% to "
            f"{high['preferred_soc_min'] * 100:.0f}% increases fuel from {low['rolling_fuel_kg']:.3f} to "
            f"{high['rolling_fuel_kg']:.3f} kg. It buys higher final SOC, but the cost is visible and monotonic."
        )
    if len(soft_penalty) > 1:
        low = soft_penalty.iloc[0]
        high = soft_penalty.iloc[-1]
        lines.append(
            f"- A lower soft-SOC penalty performs best among the soft-band cases: {low['soft_soc_penalty_g_per_kwh']:.0f} g/kWh "
            f"gives {low['rolling_fuel_kg']:.3f} kg, while {high['soft_soc_penalty_g_per_kwh']:.0f} g/kWh gives "
            f"{high['rolling_fuel_kg']:.3f} kg. The lower penalty allows local plans to borrow against the preferred band, "
            "but realized SOC still respects the physical 20% minimum in these runs."
        )
    if len(startup) > 1:
        low = startup.iloc[0]
        high = startup.iloc[-1]
        lines.append(
            f"- Higher startup penalties do not reduce starts in the realized trajectory here. Starts move from "
            f"{int(low['rolling_starts'])} at {low['startup_cost_g']:.0f} g/start to {int(high['rolling_starts'])} at "
            f"{high['startup_cost_g']:.0f} g/start, with higher fuel. The local rolling decisions appear constrained by "
            "near-term load and SOC recovery more than by this startup-cost range."
        )
    if not terminal.empty:
        best_term = terminal.sort_values("rolling_fuel_kg").iloc[0]
        unstable = terminal[terminal["nonoptimal_solves"] > 0]
        lines.append(
            f"- Terminal-reserve variants sit close to the soft baseline in fuel, with the best terminal case at "
            f"{best_term['rolling_fuel_kg']:.3f} kg and {int(best_term['rolling_starts'])} starts. They reduce starts "
            "relative to the soft baseline but end with a higher reserve."
        )
        if not unstable.empty:
            worst = unstable.iloc[0]
            lines.append(
                f"- `{worst['case_id']}` should be treated cautiously: it has {int(worst['nonoptimal_solves'])} non-optimal "
                f"local solves and a maximum local solve time of {worst['max_solve_s']:.1f} s. Its fuel is competitive, "
                "but the solve profile is not robust enough for a clean recommendation."
            )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            dedent(
                """
                The practical lesson is that oracle load foresight is not enough by itself. The rolling controller still
                pays a nontrivial price relative to the full-horizon benchmark because it implements only the first step
                and must repeatedly re-create an end-of-local-horizon SOC policy. Cases that are more conservative about
                reserve, either through longer horizons or higher preferred SOC, leave more energy in the battery and use
                more fuel. The best-performing screen setting is therefore the less conservative soft-band penalty, not
                the longest horizon or highest reserve target.
                """
            ).strip().replace("\n", " "),
            "",
            "## Generated artifacts",
            "",
            "- `composed_case_metrics.csv`: ranked case-level metrics with sweep-family labels.",
            "- `composed_dispatch_timeseries.csv`: per-case, per-timestep composed dispatch/SOC time series.",
            "- `plots/oracle_tuning_ranked_fuel.png`: ranked fuel penalty and starts.",
            "- `plots/oracle_tuning_sweep_tradeoffs.png`: parameter sweep tradeoff panels.",
            "- `plots/oracle_tuning_soc_profiles.png`: representative SOC trajectories.",
            "- `plots/oracle_tuning_solve_profile.png`: local solve-time profile.",
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    plots_dir = output_dir / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)

    summary = pd.read_csv(args.summary_csv)
    cases = classify_cases(summary)
    cases.to_csv(output_dir / "composed_case_metrics.csv", index=False)

    timeseries = load_dispatch_timeseries(cases)
    if not timeseries.empty:
        timeseries.to_csv(output_dir / "composed_dispatch_timeseries.csv", index=False)

    save_ranked_fuel_plot(cases, plots_dir / "oracle_tuning_ranked_fuel.png")
    save_sweep_tradeoff_plot(cases, plots_dir / "oracle_tuning_sweep_tradeoffs.png")
    if not timeseries.empty:
        save_soc_profiles_plot(timeseries, plots_dir / "oracle_tuning_soc_profiles.png")
    save_solve_profile_plot(cases, plots_dir / "oracle_tuning_solve_profile.png")
    write_assessment(cases, output_dir / "assessment.md")

    print(f"Saved {output_dir / 'composed_case_metrics.csv'}")
    print(f"Saved {output_dir / 'composed_dispatch_timeseries.csv'}")
    print(f"Saved {output_dir / 'assessment.md'}")
    print(f"Saved plots in {plots_dir}")


if __name__ == "__main__":
    main()
