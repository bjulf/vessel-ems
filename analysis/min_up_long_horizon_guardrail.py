from __future__ import annotations

import csv
import shutil
import tomllib
from copy import deepcopy
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from min_up_confirmatory_baseline_sweep import (
    BASE_CONFIG,
    GENERATED_CONFIG_DIR as CONFIRMATORY_CONFIG_DIR,
    OUTPUT_DIR as CONFIRMATORY_OUTPUT_DIR,
    SUMMARY_FIELDS,
    as_float,
    as_int,
    build_config,
    generate_top_contender_plots,
    is_valid,
    normalize_rows,
    ranking_key,
    run_case,
    run_plot_script,
    summary_row,
    verify_generated_config,
    write_csv,
)
from oracle_operational_tuning_screen import write_rolling_config
from sensitivity_common import REPO_ROOT


OUTPUT_DIR = (
    REPO_ROOT
    / "analysis"
    / "output"
    / "rolling_horizon"
    / "min_up_long_horizon_guardrail"
)
GENERATED_CONFIG_DIR = OUTPUT_DIR / "generated_configs"
PLOTS_DIR = OUTPUT_DIR / "plots"
CASE_PLOTS_DIR = PLOTS_DIR / "cases"

CASES = [
    {"case_id": "h20_startup500_softsoc10000_minup6", "horizon": 20, "startup": 500.0, "soft_soc": 10000.0},
    {"case_id": "h24_startup500_softsoc10000_minup6", "horizon": 24, "startup": 500.0, "soft_soc": 10000.0},
    {"case_id": "h20_startup500_softsoc20000_minup6", "horizon": 20, "startup": 500.0, "soft_soc": 20000.0},
    {"case_id": "h24_startup500_softsoc20000_minup6", "horizon": 24, "startup": 500.0, "soft_soc": 20000.0},
]


def load_existing_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def guardrail_config(base: dict, case: dict[str, object]) -> dict:
    config = build_config(base, case)
    config["run"]["description"] = (
        "Operational 15-minute rolling-horizon MILP long-horizon guardrail: "
        f"H={int(case['horizon'])}, startup={float(case['startup']):g} g/start, "
        f"mean soft-SOC penalty={float(case['soft_soc']):g} g/kWh, "
        "6-step minimum up-time"
    )
    return config


def write_appendix_plot(summary_path: Path, reference_path: Path) -> tuple[Path, Path]:
    df = pd.read_csv(summary_path)
    reference = pd.read_csv(reference_path)
    baseline = reference.loc[
        reference["case_id"].eq("h16_startup500_softsoc10000_minup6")
    ].iloc[0]

    baseline_row = baseline.to_dict()
    baseline_row["case_id"] = "h16_startup500_softsoc10000_minup6_reference"
    combined = pd.concat([pd.DataFrame([baseline_row]), df], ignore_index=True)
    combined["sort_h"] = combined["horizon_steps"].astype(int)
    combined["sort_p"] = combined["soft_soc_penalty_g_per_kwh"].astype(float)
    combined = combined.sort_values(["sort_p", "sort_h"]).reset_index(drop=True)

    labels = [
        f"H{int(row.horizon_steps)} P{int(float(row.soft_soc_penalty_g_per_kwh) / 1000)}k"
        + (" ref" if "reference" in row.case_id else "")
        for row in combined.itertuples()
    ]
    colors = [
        "#64748B" if "reference" in row.case_id else ("#059669" if float(row.soft_soc_penalty_g_per_kwh) == 10000 else "#B45309")
        for row in combined.itertuples()
    ]

    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "xtick.labelsize": 9,
            "ytick.labelsize": 10,
        }
    )
    fig, axes = plt.subplots(2, 1, figsize=(9.5, 6.2), sharex=True, constrained_layout=True)
    x = range(len(combined))
    axes[0].bar(x, combined["fuel_delta_vs_full_pct"], color=colors, alpha=0.88)
    axes[0].set_ylabel("Fuel penalty [%]")
    axes[0].set_title("Long-Horizon Guardrail: Fuel Penalty")
    axes[0].grid(axis="y", alpha=0.25)

    axes[1].bar(x, combined["rolling_starts"], color=colors, alpha=0.88)
    axes[1].set_ylabel("Generator starts")
    axes[1].set_title("Long-Horizon Guardrail: Starts")
    axes[1].grid(axis="y", alpha=0.25)
    axes[1].set_xticks(list(x), labels, rotation=30, ha="right")
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)

    png = PLOTS_DIR / "long_horizon_guardrail_fuel_starts.png"
    pdf = PLOTS_DIR / "long_horizon_guardrail_fuel_starts.pdf"
    fig.savefig(png, dpi=220)
    fig.savefig(pdf)
    plt.close(fig)
    return png, pdf


def copy_case_plots(rows: list[dict[str, object]]) -> list[str]:
    CASE_PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for row in sorted(rows, key=lambda item: (as_int(item, "horizon_steps"), as_float(item, "soft_soc_penalty_g_per_kwh"))):
        run_dir = Path(str(row["run_dir"]))
        case_id = str(row["case_id"])
        dispatch_panel = run_plot_script("plot_rolling_horizon_run_panel.py", run_dir)
        comparison_panel = run_plot_script("plot_rolling_full_horizon_comparison.py", run_dir)
        for source, suffix in [(dispatch_panel, "dispatch_panel"), (comparison_panel, "rolling_vs_full")]:
            target = CASE_PLOTS_DIR / f"{case_id}_{suffix}{source.suffix}"
            shutil.copy2(source, target)
            copied.append(str(target))
    return copied


def write_markdown(rows: list[dict[str, object]], copied_plots: list[str]) -> None:
    reference_path = CONFIRMATORY_OUTPUT_DIR / "summary.csv"
    reference = pd.read_csv(reference_path)
    baseline = reference.loc[
        reference["case_id"].eq("h16_startup500_softsoc10000_minup6")
    ].iloc[0].to_dict()

    valid = [row for row in rows if is_valid(row)]
    fuel_ranked = sorted(valid, key=lambda row: (as_float(row, "fuel_delta_vs_full_pct"), as_int(row, "rolling_starts")))
    best_fuel = fuel_ranked[0] if fuel_ranked else sorted(rows, key=lambda row: as_float(row, "fuel_delta_vs_full_pct"))[0]

    lines = [
        "# Long-Horizon Guardrail Sweep",
        "",
        "Four-case extension of the compact baseline confirmation sweep: H20/H24, startup 500 g/start, soft SOC penalty 10000 or 20000 g/kWh, 6-step minimum up-time, no soft-band terminal reserve.",
        "",
        "Reference from the 18-case sweep: `h16_startup500_softsoc10000_minup6`.",
        "",
        "| Case | H | SOC penalty | Fuel kg | Delta % | Starts | Min SOC % | Final SOC % | Run lengths | P95 solve s | Max solve s | Nonopt/time/infeas |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |",
        (
            f"| `h16_startup500_softsoc10000_minup6` ref | {int(baseline['horizon_steps'])} | "
            f"{float(baseline['soft_soc_penalty_g_per_kwh']):.0f} | "
            f"{float(baseline['rolling_fuel_kg']):.2f} | {float(baseline['fuel_delta_vs_full_pct']):.2f} | "
            f"{int(baseline['rolling_starts'])} | {float(baseline['minimum_soc_pct']):.2f} | "
            f"{float(baseline['final_soc_pct']):.2f} | {baseline['run_lengths_steps']} | "
            f"{float(baseline['p95_solve_s']):.3f} | {float(baseline['max_solve_s']):.3f} | "
            f"{int(baseline['nonoptimal_timeout_infeasible_local_solve_count'])} |"
        ),
    ]
    for row in sorted(rows, key=lambda item: (as_int(item, "horizon_steps"), as_float(item, "soft_soc_penalty_g_per_kwh"))):
        lines.append(
            f"| `{row['case_id']}` | {as_int(row, 'horizon_steps')} | "
            f"{as_float(row, 'soft_soc_penalty_g_per_kwh'):.0f} | "
            f"{as_float(row, 'rolling_fuel_kg'):.2f} | {as_float(row, 'fuel_delta_vs_full_pct'):.2f} | "
            f"{as_int(row, 'rolling_starts')} | {as_float(row, 'minimum_soc_pct'):.2f} | "
            f"{as_float(row, 'final_soc_pct'):.2f} | {row['run_lengths_steps']} | "
            f"{as_float(row, 'p95_solve_s'):.3f} | {as_float(row, 'max_solve_s'):.3f} | "
            f"{as_int(row, 'nonoptimal_timeout_infeasible_local_solve_count')} |"
        )

    lines.extend(["", "## Recommendation", ""])
    if valid:
        lines.append("Keep `h16_startup500_softsoc10000_minup6` as the rolling-horizon baseline.")
        lines.append("")
        lines.append(
            f"The best-fuel long-horizon guardrail case is `{best_fuel['case_id']}` at "
            f"{as_float(best_fuel, 'rolling_fuel_kg'):.2f} kg and "
            f"{as_float(best_fuel, 'fuel_delta_vs_full_pct'):.2f}% fuel penalty, "
            f"but this is worse than the H16 reference at {float(baseline['rolling_fuel_kg']):.2f} kg "
            f"and {float(baseline['fuel_delta_vs_full_pct']):.2f}%."
        )
        lines.append("")
        lines.append(
            "The P20k cases mainly push SOC upward and increase final SOC carryover; they do not improve the fuel/start tradeoff. The long-horizon guardrail therefore supports freezing H16 C500 P10k rather than extending the controller horizon."
        )
    else:
        lines.append("No long-horizon guardrail case passed the clean filters; keep H16 C500 P10k.")

    lines.extend(["", "## Generated Plots", ""])
    lines.append("- `plots/long_horizon_guardrail_fuel_starts.png`: fuel/start guardrail plot with H16 reference.")
    lines.append("- `plots/cases/`: dispatch-panel and rolling-vs-full plots for all four guardrail cases.")
    for path in copied_plots:
        lines.append(f"- `{Path(path).relative_to(OUTPUT_DIR).as_posix()}`")
    lines.append("")

    (OUTPUT_DIR / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(BASE_CONFIG, "rb") as fh:
        base_config = tomllib.load(fh)

    summary_path = OUTPUT_DIR / "summary.csv"
    rows: list[dict[str, object]] = [dict(row) for row in load_existing_rows(summary_path)]
    completed_cases = {str(row["case_id"]) for row in rows}

    for case in CASES:
        case_id = str(case["case_id"])
        if case_id in completed_cases:
            print(f"Skipping existing {case_id}", flush=True)
            continue

        config = guardrail_config(base_config, case)
        config_path = GENERATED_CONFIG_DIR / f"{case_id}.toml"
        write_rolling_config(config, config_path)
        verify_generated_config(config_path, case)

        print(f"Running {case_id}", flush=True)
        metadata, run_dir, wall_clock_s = run_case(config_path)
        row = summary_row(case, config_path, metadata, run_dir, wall_clock_s)
        rows.append(row)
        rows = normalize_rows(rows)
        write_csv(summary_path, rows)
        print(
            f"  fuel={as_float(row, 'rolling_fuel_kg'):.2f} kg, "
            f"delta={as_float(row, 'fuel_delta_vs_full_pct'):.2f}%, "
            f"starts={as_int(row, 'rolling_starts')}, "
            f"min SOC={as_float(row, 'minimum_soc_pct'):.2f}%, "
            f"final SOC={as_float(row, 'final_soc_pct'):.2f}%, "
            f"nonopt={as_int(row, 'nonoptimal_timeout_infeasible_local_solve_count')}, "
            f"run={run_dir}",
            flush=True,
        )

    rows = normalize_rows(rows)
    write_csv(summary_path, rows)
    appendix_png, appendix_pdf = write_appendix_plot(
        summary_path, CONFIRMATORY_OUTPUT_DIR / "summary.csv"
    )
    copied_plots = copy_case_plots(rows)
    write_markdown(rows, copied_plots)

    print(f"Saved {summary_path}", flush=True)
    print(f"Saved {OUTPUT_DIR / 'summary.md'}", flush=True)
    print(f"Saved {appendix_png}", flush=True)
    print(f"Saved {appendix_pdf}", flush=True)
    print(f"Saved case plots under {CASE_PLOTS_DIR}", flush=True)


if __name__ == "__main__":
    main()
