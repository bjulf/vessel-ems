from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt

from sensitivity_common import NO_TERMINAL_SENSITIVITY_OUTPUT_ROOT, SENSITIVITY_OUTPUT_ROOT, read_csv_rows


SWEEP_SPECS = {
    "startup_cost": {
        "field": "startup_cost_g_per_start",
        "label": "Startup cost [g/start]",
        "baseline_value": 700.0,
    },
    "soc_min": {
        "field": "soc_min_pct",
        "label": "Minimum SOC [%]",
        "baseline_value": 20.0,
    },
    "initial_soc": {
        "field": "initial_soc_pct",
        "label": "Initial SOC [%]",
        "baseline_value": 70.0,
    },
    "battery_efficiency": {
        "field": "battery_efficiency",
        "label": "Battery efficiency [-]",
        "baseline_value": 0.95,
    },
}


def format_number(value: float, digits: int = 2) -> str:
    formatted = f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return formatted if formatted else "0"


def load_sweep_rows(root: Path, sweep_name: str, field: str) -> list[dict[str, float | str]]:
    rows = read_csv_rows(root / sweep_name / "summary.csv")
    parsed_rows: list[dict[str, float | str]] = []

    for row in rows:
        parsed: dict[str, float | str] = {}
        for key, value in row.items():
            if value == "":
                parsed[key] = value
                continue
            try:
                parsed[key] = float(value)
            except ValueError:
                parsed[key] = value
        parsed_rows.append(parsed)

    parsed_rows.sort(key=lambda item: float(item[field]))
    return parsed_rows


def find_baseline_row(rows: list[dict[str, float | str]], field: str, baseline_value: float) -> dict[str, float | str]:
    for row in rows:
        if abs(float(row[field]) - baseline_value) <= 1e-9:
            return row
    raise KeyError(f"Missing baseline value {baseline_value} for {field}")


def find_row(rows: list[dict[str, float | str]], field: str, value: float) -> dict[str, float | str]:
    for row in rows:
        if abs(float(row[field]) - value) <= 1e-9:
            return row
    raise KeyError(f"Missing sweep value {value} for {field}")


def metric_span(rows: list[dict[str, float | str]], metric: str) -> float:
    return max(float(row[metric]) for row in rows) - min(float(row[metric]) for row in rows)


def write_metrics_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "sweep",
        "old_fuel_span_kg",
        "new_fuel_span_kg",
        "old_starts_span",
        "new_starts_span",
        "old_terminal_soc_span_pct",
        "new_terminal_soc_span_pct",
        "baseline_old_fuel_kg",
        "baseline_new_fuel_kg",
        "baseline_fuel_delta_kg",
        "baseline_old_starts",
        "baseline_new_starts",
        "baseline_starts_delta",
        "baseline_old_terminal_soc_pct",
        "baseline_new_terminal_soc_pct",
        "baseline_terminal_soc_delta_pct",
        "new_avg_solve_time_s",
        "new_total_wall_clock_s",
    ]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def plot_metric_comparison(
    metric: str,
    metric_label: str,
    output_path: Path,
    package_rows: dict[str, tuple[list[dict[str, float | str]], list[dict[str, float | str]]]],
) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), constrained_layout=True)

    for ax, (sweep_name, spec) in zip(axes.flatten(), SWEEP_SPECS.items()):
        old_rows, new_rows = package_rows[sweep_name]
        field = spec["field"]
        baseline_value = spec["baseline_value"]

        old_x = [float(row[field]) for row in old_rows]
        old_y = [float(row[metric]) for row in old_rows]
        new_x = [float(row[field]) for row in new_rows]
        new_y = [float(row[metric]) for row in new_rows]

        ax.plot(old_x, old_y, marker="o", linewidth=2.2, label="Terminal constrained", color="#1d4ed8")
        ax.plot(new_x, new_y, marker="o", linewidth=2.2, label="No terminal SOC", color="#b45309")

        for rows, color in ((old_rows, "#1d4ed8"), (new_rows, "#b45309")):
            baseline_row = find_baseline_row(rows, field, baseline_value)
            ax.scatter(
                [float(baseline_row[field])],
                [float(baseline_row[metric])],
                marker="*",
                s=180,
                color=color,
                edgecolors="black",
                linewidths=0.8,
                zorder=5,
            )

        ax.set_title(sweep_name.replace("_", " ").title(), fontsize=14)
        ax.set_xlabel(spec["label"], fontsize=11)
        ax.set_ylabel(metric_label, fontsize=11)
        ax.tick_params(axis="both", labelsize=10)

    handles, labels = axes.flatten()[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, fontsize=11)
    fig.suptitle(f"No-terminal vs terminal-constrained sensitivity: {metric_label}", fontsize=17, fontweight="bold")
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def sweep_ranking(metrics_rows: list[dict[str, object]], key: str) -> str:
    ordered = sorted(metrics_rows, key=lambda row: float(row[key]), reverse=True)
    return ", ".join(
        f"{str(row['sweep']).replace('_', ' ')} ({format_number(float(row[key]))})"
        for row in ordered
    )


def write_markdown_table(
    lines: list[str],
    headers: list[str],
    rows: list[list[str]],
) -> None:
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")


def baseline_assessment_rows(
    package_rows: dict[str, tuple[list[dict[str, float | str]], list[dict[str, float | str]]]],
    metrics_rows: list[dict[str, object]],
) -> list[list[str]]:
    startup_rows = package_rows["startup_cost"][1]
    soc_min_rows = package_rows["soc_min"][1]
    initial_soc_rows = package_rows["initial_soc"][1]
    efficiency_rows = package_rows["battery_efficiency"][1]

    startup_500 = find_row(startup_rows, "startup_cost_g_per_start", 500.0)
    startup_700 = find_row(startup_rows, "startup_cost_g_per_start", 700.0)
    startup_1000 = find_row(startup_rows, "startup_cost_g_per_start", 1000.0)

    soc_20 = find_row(soc_min_rows, "soc_min_pct", 20.0)
    soc_30 = find_row(soc_min_rows, "soc_min_pct", 30.0)
    soc_40 = find_row(soc_min_rows, "soc_min_pct", 40.0)

    initial_50 = find_row(initial_soc_rows, "initial_soc_pct", 50.0)
    initial_60 = find_row(initial_soc_rows, "initial_soc_pct", 60.0)
    initial_70 = find_row(initial_soc_rows, "initial_soc_pct", 70.0)
    initial_80 = find_row(initial_soc_rows, "initial_soc_pct", 80.0)

    efficiency_92 = find_row(efficiency_rows, "battery_efficiency", 0.92)
    efficiency_95 = find_row(efficiency_rows, "battery_efficiency", 0.95)
    efficiency_98 = find_row(efficiency_rows, "battery_efficiency", 0.98)

    baseline_delta = next(row for row in metrics_rows if row["sweep"] == "startup_cost")

    return [
        [
            "Startup cost = 700 g/start",
            "still defensible",
            (
                f"The 500-700 g/start band is flat at {format_number(float(startup_500['total_fuel_kg']))} kg fuel "
                f"and {int(float(startup_500['total_starts']))} starts. Moving to 1000 g/start only saves "
                f"{int(float(startup_700['total_starts']) - float(startup_1000['total_starts']))} starts at "
                f"+{format_number(float(startup_1000['total_fuel_kg']) - float(startup_700['total_fuel_kg']))} kg fuel."
            ),
        ],
        [
            "Minimum SOC = 20%",
            "overly influential",
            (
                "Every no-terminal case finishes on the floor. Raising the floor to 30% and 40% increases fuel by "
                f"{format_number(float(soc_30['total_fuel_kg']) - float(soc_20['total_fuel_kg']))} and "
                f"{format_number(float(soc_40['total_fuel_kg']) - float(soc_20['total_fuel_kg']))} kg and lifts "
                "terminal SOC one-for-one."
            ),
        ],
        [
            "Initial SOC = 70%",
            "weakly justified",
            (
                f"Moving from 70% to 80% cuts fuel by {format_number(float(initial_70['total_fuel_kg']) - float(initial_80['total_fuel_kg']))} kg "
                "with the same 4 starts. Dropping to 60% and 50% adds "
                f"{format_number(float(initial_60['total_fuel_kg']) - float(initial_70['total_fuel_kg']))} and "
                f"{format_number(float(initial_50['total_fuel_kg']) - float(initial_70['total_fuel_kg']))} kg and adds one start."
            ),
        ],
        [
            "Battery efficiency = 0.95",
            "still defensible",
            (
                f"The 0.92 to 0.98 range shifts fuel from {format_number(float(efficiency_92['total_fuel_kg']))} to "
                f"{format_number(float(efficiency_98['total_fuel_kg']))} kg and starts from "
                f"{int(float(efficiency_92['total_starts']))} to {int(float(efficiency_98['total_starts']))}. "
                "The baseline sits near the middle of a plausible range."
            ),
        ],
        [
            "No terminal SOC constraint",
            "weakly justified",
            (
                f"Removing the reserve lowers baseline fuel by {format_number(abs(float(baseline_delta['baseline_fuel_delta_kg'])))} kg, "
                f"lowers terminal SOC by {format_number(abs(float(baseline_delta['baseline_terminal_soc_delta_pct'])))} pp, "
                f"and changes starts by +{int(float(baseline_delta['baseline_starts_delta']))}. "
                "It works as a lower-bound scenario, not as a silent replacement for the terminal-constrained baseline."
            ),
        ],
    ]


def write_package_summary(
    path: Path,
    *,
    metrics_rows: list[dict[str, object]],
    package_rows: dict[str, tuple[list[dict[str, float | str]], list[dict[str, float | str]]]],
) -> None:
    total_wall_clock_s = sum(
        float(row["wall_clock_runtime_s"])
        for _, new_rows in package_rows.values()
        for row in new_rows
    )
    total_cases = sum(len(new_rows) for _, new_rows in package_rows.values())
    old_ranking = sweep_ranking(metrics_rows, "old_fuel_span_kg")
    new_ranking = sweep_ranking(metrics_rows, "new_fuel_span_kg")

    lines = [
        "# No-Terminal SOC Sensitivity Package Summary",
        "",
        "This package reran the frozen baseline from `config/baseline_model_no_terminal_soc.toml` and compared it",
        "against the older terminal-constrained package in `analysis/output/sensitivity/`.",
        "",
        f"No-terminal cases completed: {total_cases}",
        f"Total no-terminal wall-clock runtime: {format_number(total_wall_clock_s, 1)} s",
        "Comparison outputs: `comparison/comparison_metrics.csv`, `comparison/fuel_response_comparison.png`,",
        "`comparison/starts_response_comparison.png`, and `comparison/terminal_soc_response_comparison.png`.",
        "",
        "## Sweep Comparison",
        "",
    ]

    comparison_rows = [
        [
            str(row["sweep"]).replace("_", " "),
            format_number(float(row["old_fuel_span_kg"])),
            format_number(float(row["new_fuel_span_kg"])),
            format_number(float(row["old_starts_span"])),
            format_number(float(row["new_starts_span"])),
            format_number(float(row["baseline_fuel_delta_kg"])),
            format_number(float(row["baseline_starts_delta"])),
            format_number(float(row["baseline_terminal_soc_delta_pct"])),
            format_number(float(row["new_avg_solve_time_s"])),
            format_number(float(row["new_total_wall_clock_s"]), 1),
        ]
        for row in metrics_rows
    ]
    write_markdown_table(
        lines,
        [
            "Sweep",
            "Old fuel span [kg]",
            "New fuel span [kg]",
            "Old starts span",
            "New starts span",
            "Baseline fuel delta [kg]",
            "Baseline starts delta",
            "Baseline terminal delta [pp]",
            "New avg solve [s]",
            "New wall total [s]",
        ],
        comparison_rows,
    )

    lines.extend(
        [
            "## Findings",
            "",
            (
                f"- Removing the terminal reserve cuts baseline fuel by {format_number(abs(float(metrics_rows[0]['baseline_fuel_delta_kg'])))} kg "
                f"across the package, drops terminal SOC from 50% to 20%, and increases starts from 2 to 4."
            ),
            f"- Old fuel-sensitivity ranking: {old_ranking}.",
            f"- New fuel-sensitivity ranking: {new_ranking}.",
            (
                "- The qualitative story changes mainly through `soc_min`: in the old package it was nearly inactive, "
                "while in the no-terminal package it becomes the second-strongest driver because the optimizer now uses "
                "the battery down to the configured floor."
            ),
            (
                "- `startup_cost` remains a low-leverage calibration parameter. `battery_efficiency` still matters, "
                "but it does not dominate the result the way available battery energy does."
            ),
            "",
            "## Baseline Assessment",
            "",
        ]
    )

    write_markdown_table(
        lines,
        ["Parameter", "Judgment", "Evidence"],
        baseline_assessment_rows(package_rows, metrics_rows),
    )

    lines.extend(
        [
            "## Additional Sensitivity Recommendations",
            "",
            "1. Add `battery.E_max` or an explicit usable-energy-window sweep if one more analysis is worth doing. The no-terminal package is clearly energy-budget limited, so this is the highest-value structural check.",
            "2. Consider a generator-minimum-load or SFOC-shape sweep only if the thesis needs robustness on engine-model assumptions. That is secondary to battery-energy assumptions.",
            "3. Do not add finer startup-cost sweeps. The current results already show a broad 500-700 g/start plateau, so extra resolution there is low value.",
            "",
            "If no more sweep time is available, the current four-sweep no-terminal package is already enough to support a clear report claim: removing the terminal reserve materially lowers fuel use, keeps startup-cost conclusions mostly intact, and makes `soc_min` plus available battery energy the dominant assumptions.",
            "",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    comparison_dir = NO_TERMINAL_SENSITIVITY_OUTPUT_ROOT / "comparison"
    comparison_dir.mkdir(parents=True, exist_ok=True)

    package_rows: dict[str, tuple[list[dict[str, float | str]], list[dict[str, float | str]]]] = {}
    metrics_rows: list[dict[str, object]] = []

    for sweep_name, spec in SWEEP_SPECS.items():
        field = spec["field"]
        old_rows = load_sweep_rows(SENSITIVITY_OUTPUT_ROOT, sweep_name, field)
        new_rows = load_sweep_rows(NO_TERMINAL_SENSITIVITY_OUTPUT_ROOT, sweep_name, field)
        package_rows[sweep_name] = (old_rows, new_rows)

        old_baseline = find_baseline_row(old_rows, field, float(spec["baseline_value"]))
        new_baseline = find_baseline_row(new_rows, field, float(spec["baseline_value"]))

        metrics_rows.append(
            {
                "sweep": sweep_name,
                "old_fuel_span_kg": metric_span(old_rows, "total_fuel_kg"),
                "new_fuel_span_kg": metric_span(new_rows, "total_fuel_kg"),
                "old_starts_span": metric_span(old_rows, "total_starts"),
                "new_starts_span": metric_span(new_rows, "total_starts"),
                "old_terminal_soc_span_pct": metric_span(old_rows, "terminal_soc_pct"),
                "new_terminal_soc_span_pct": metric_span(new_rows, "terminal_soc_pct"),
                "baseline_old_fuel_kg": float(old_baseline["total_fuel_kg"]),
                "baseline_new_fuel_kg": float(new_baseline["total_fuel_kg"]),
                "baseline_fuel_delta_kg": float(new_baseline["total_fuel_kg"]) - float(old_baseline["total_fuel_kg"]),
                "baseline_old_starts": float(old_baseline["total_starts"]),
                "baseline_new_starts": float(new_baseline["total_starts"]),
                "baseline_starts_delta": float(new_baseline["total_starts"]) - float(old_baseline["total_starts"]),
                "baseline_old_terminal_soc_pct": float(old_baseline["terminal_soc_pct"]),
                "baseline_new_terminal_soc_pct": float(new_baseline["terminal_soc_pct"]),
                "baseline_terminal_soc_delta_pct": float(new_baseline["terminal_soc_pct"])
                - float(old_baseline["terminal_soc_pct"]),
                "new_avg_solve_time_s": sum(float(row["solve_time_s"]) for row in new_rows) / len(new_rows),
                "new_total_wall_clock_s": sum(float(row["wall_clock_runtime_s"]) for row in new_rows),
            }
        )

    write_metrics_csv(comparison_dir / "comparison_metrics.csv", metrics_rows)
    plot_metric_comparison(
        "total_fuel_kg",
        "Total fuel [kg]",
        comparison_dir / "fuel_response_comparison.png",
        package_rows,
    )
    plot_metric_comparison(
        "total_starts",
        "Generator starts [count]",
        comparison_dir / "starts_response_comparison.png",
        package_rows,
    )
    plot_metric_comparison(
        "terminal_soc_pct",
        "Terminal SOC [%]",
        comparison_dir / "terminal_soc_response_comparison.png",
        package_rows,
    )
    write_package_summary(
        NO_TERMINAL_SENSITIVITY_OUTPUT_ROOT / "summary.md",
        metrics_rows=metrics_rows,
        package_rows=package_rows,
    )

    print(f"Saved {comparison_dir / 'comparison_metrics.csv'}")
    print(f"Saved {comparison_dir / 'fuel_response_comparison.png'}")
    print(f"Saved {comparison_dir / 'starts_response_comparison.png'}")
    print(f"Saved {comparison_dir / 'terminal_soc_response_comparison.png'}")
    print(f"Saved {NO_TERMINAL_SENSITIVITY_OUTPUT_ROOT / 'summary.md'}")


if __name__ == "__main__":
    main()
