from __future__ import annotations

import argparse
import math
import tomllib
from pathlib import Path

import matplotlib.pyplot as plt

from sensitivity_common import (
    REPO_ROOT,
    compute_run_metrics,
    create_output_dirs,
    infer_case_warning,
    read_csv_rows,
    repo_relative_str,
    resolve_repo_path,
    run_case,
    sensitivity_output_root,
    write_config,
    write_csv,
    write_markdown_summary,
)
from startup_cost_sensitivity import build_case_config


DEFAULT_SCAN_COSTS_G = [500, 550, 600, 650, 700, 750, 800, 850, 900, 1000, 1100]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a supplemental high-resolution startup-cost scan without "
            "overwriting the main startup-cost sweep outputs."
        )
    )
    parser.add_argument(
        "config",
        nargs="?",
        default="config/baseline_model_no_terminal_soc_startup1000g.toml",
        help="Config path relative to repo root or absolute path.",
    )
    parser.add_argument(
        "--startup-costs",
        type=float,
        nargs="+",
        default=DEFAULT_SCAN_COSTS_G,
        help="Startup-cost values in g/start to include in the focused scan.",
    )
    return parser.parse_args()


def startup_cost_key(value: object) -> float:
    return float(value)


def load_cached_rows(*paths: Path) -> dict[float, dict[str, object]]:
    cached: dict[float, dict[str, object]] = {}
    for path in paths:
        if not path.exists():
            continue
        for row in read_csv_rows(path):
            cached[startup_cost_key(row["startup_cost_g_per_start"])] = dict(row)
    return cached


def format_point_label(value: float) -> str:
    return f"{int(value)}" if float(value).is_integer() else f"{value:g}"


def run_missing_case(
    *,
    base_config: dict,
    generated_configs_dir: Path,
    startup_cost_g: float,
) -> dict[str, object]:
    case_config = build_case_config(base_config, startup_cost_g)
    config_stub = (
        str(int(startup_cost_g))
        if float(startup_cost_g).is_integer()
        else str(startup_cost_g).replace(".", "p")
    )
    case_config_path = generated_configs_dir / f"startup_cost_{config_stub}g.toml"
    write_config(case_config, case_config_path)

    metadata, run_dir, wall_clock_runtime_s = run_case(case_config_path)
    metrics = compute_run_metrics(run_dir, metadata)
    terminal_reference_soc_pct = float(
        metadata["validation"]["battery_energy"].get("terminal_target_min_soc_pct", 0.0)
    )
    configured_soc_min_pct = float(case_config["battery"]["SOC_min"]) * 100.0

    row = {
        "startup_cost_g_per_start": int(startup_cost_g)
        if float(startup_cost_g).is_integer()
        else float(startup_cost_g),
        "config_path": str(case_config_path),
        "run_dir": str(run_dir),
        "objective_value": float(metadata["solver"]["objective"]),
        "total_fuel_kg": float(metrics["total_fuel_kg"]),
        "total_starts": int(metrics["total_starts"]),
        "total_stops": int(metrics["total_stops"]),
        "time_two_gensets_online_h": float(metrics["time_two_gensets_online_h"]),
        "share_two_gensets_online_pct": float(metrics["share_two_gensets_online_pct"]),
        "total_online_genset_hours": float(metrics["total_online_genset_hours"]),
        "min_soc_pct": float(metrics["min_soc_pct"]),
        "terminal_soc_pct": float(metrics["terminal_soc_pct"]),
        "terminal_reference_soc_pct": terminal_reference_soc_pct,
        "configured_soc_min_pct": configured_soc_min_pct,
        "battery_throughput_kwh": float(metrics["battery_throughput_kwh"]),
        "solve_time_s": float(metadata["solver"]["solve_time_s"]),
        "wall_clock_runtime_s": float(wall_clock_runtime_s),
    }
    row["warning"] = infer_case_warning(
        terminal_soc_pct=float(row["terminal_soc_pct"]),
        terminal_reference_soc_pct=float(row["terminal_reference_soc_pct"]),
        min_soc_pct=float(row["min_soc_pct"]),
        configured_soc_min_pct=float(row["configured_soc_min_pct"]),
        solve_time_s=float(row["solve_time_s"]),
    )
    return row


def format_annotation(value: float) -> str:
    if math.isclose(value, round(value), abs_tol=1e-9):
        return str(int(round(value)))
    if abs(value) >= 100:
        return f"{value:.1f}"
    return f"{value:.2f}".rstrip("0").rstrip(".")


def plot_scan(rows: list[dict[str, object]], path: Path, *, baseline_startup_cost_g: float) -> None:
    startup_costs = [float(row["startup_cost_g_per_start"]) for row in rows]
    total_fuel = [float(row["total_fuel_kg"]) for row in rows]
    starts = [int(float(row["total_starts"])) for row in rows]
    time_two_online = [float(row["time_two_gensets_online_h"]) for row in rows]

    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(
        {
            "font.family": "DejaVu Serif",
            "font.size": 13,
            "axes.titlesize": 16,
            "axes.labelsize": 14,
            "xtick.labelsize": 12,
            "ytick.labelsize": 12,
        }
    )

    fig, axes = plt.subplots(3, 1, figsize=(12, 12.5), constrained_layout=True, sharex=True)
    panels = [
        (total_fuel, "Total fuel [kg]", "Fuel response", "#177e89"),
        (starts, "Total starts [count]", "Generator starts", "#8c5a3c"),
        (time_two_online, "Time with 2 gensets online [h]", "Two-generator overlap", "#1d4ed8"),
    ]

    baseline_index = startup_costs.index(float(baseline_startup_cost_g))
    baseline_x = startup_costs[baseline_index]

    for ax, (values, ylabel, title, color) in zip(axes, panels):
        ax.axvline(baseline_x, color="#c1121f", linestyle="--", linewidth=1.3, alpha=0.85, zorder=1)
        ax.plot(
            startup_costs,
            values,
            color=color,
            linewidth=2.6,
            marker="o",
            markersize=7.5,
            markerfacecolor=color,
            markeredgecolor="white",
            markeredgewidth=1.0,
            zorder=2,
        )
        ax.scatter(
            [baseline_x],
            [values[baseline_index]],
            s=140,
            color="#c1121f",
            edgecolors="#111111",
            linewidths=1.2,
            zorder=3,
        )
        for x, y in zip(startup_costs, values):
            ax.annotate(
                format_annotation(float(y)),
                (x, y),
                textcoords="offset points",
                xytext=(0, 8),
                ha="center",
                fontsize=10,
            )
        ax.set_title(title, fontsize=15)
        ax.set_ylabel(ylabel)
        ax.grid(True, axis="y", alpha=0.35)
        ax.grid(False, axis="x")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    axes[-1].set_xlabel("Startup cost [g/start]")
    axes[-1].set_xticks(startup_costs, [format_point_label(value) for value in startup_costs])
    fig.suptitle("Startup-cost focused scan (500-1100 g/start)", fontsize=18, fontweight="bold")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def write_scan_markdown(
    *,
    rows: list[dict[str, object]],
    path: Path,
    baseline_startup_cost_g: float,
    new_case_costs: list[float],
) -> None:
    baseline_row = next(
        row for row in rows if startup_cost_key(row["startup_cost_g_per_start"]) == float(baseline_startup_cost_g)
    )
    intro_lines = [
        "Focused startup-cost scan built as a supplement to the main sweep.",
        (
            "Newly solved cases for this scan: "
            + ", ".join(f"{format_point_label(value)} g/start" for value in new_case_costs)
            if new_case_costs
            else "No new solves were needed; all scan cases were already available."
        ),
        (
            f"Baseline case at {format_point_label(baseline_startup_cost_g)} g/start: "
            f"{float(baseline_row['total_fuel_kg']):.3f} kg fuel, "
            f"{int(float(baseline_row['total_starts']))} starts, "
            f"terminal SOC {float(baseline_row['terminal_soc_pct']):.2f}%."
        ),
    ]
    write_markdown_summary(
        path,
        title="Startup-Cost Focused Scan Summary",
        intro_lines=intro_lines,
        columns=[
            ("Startup Cost [g/start]", "startup_cost_g_per_start"),
            ("Config", lambda row: f"`{repo_relative_str(str(row['config_path']))}`"),
            ("Run Dir", lambda row: f"`{repo_relative_str(str(row['run_dir']))}`"),
            ("Fuel [kg]", "total_fuel_kg"),
            ("Starts", "total_starts"),
            ("Two-Gen Time [h]", "time_two_gensets_online_h"),
            ("Min SOC [%]", "min_soc_pct"),
            ("Terminal SOC [%]", "terminal_soc_pct"),
            ("Solve [s]", "solve_time_s"),
            ("Warnings", "warning"),
        ],
        rows=rows,
    )


def main() -> None:
    args = parse_args()
    config_path = resolve_repo_path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config file: {config_path}")
    if not config_path.is_relative_to(REPO_ROOT):
        raise ValueError("Config path must be inside the repository.")

    with open(config_path, "rb") as fh:
        base_config = tomllib.load(fh)

    baseline_startup_cost_g = float(base_config["generators"][0]["startup_cost"])
    output_dir, generated_configs_dir = create_output_dirs("startup_cost", sensitivity_output_root(base_config))

    main_summary_csv = output_dir / "summary.csv"
    scan_summary_csv = output_dir / "high_res_scan_summary.csv"
    scan_manifest_csv = output_dir / "high_res_scan_manifest.csv"
    scan_summary_md = output_dir / "high_res_scan_summary.md"
    scan_plot_png = output_dir / "high_res_scan_overview.png"

    cached_rows = load_cached_rows(main_summary_csv, scan_summary_csv)
    requested_costs = sorted({float(value) for value in args.startup_costs})
    new_case_costs: list[float] = []

    for startup_cost_g in requested_costs:
        if startup_cost_g in cached_rows:
            print(f"Reusing startup_cost = {format_point_label(startup_cost_g)} g/start")
            continue
        print(f"Running startup_cost = {format_point_label(startup_cost_g)} g/start")
        cached_rows[startup_cost_g] = run_missing_case(
            base_config=base_config,
            generated_configs_dir=generated_configs_dir,
            startup_cost_g=startup_cost_g,
        )
        new_case_costs.append(startup_cost_g)

    focus_rows = [cached_rows[value] for value in requested_costs]
    focus_rows.sort(key=lambda row: startup_cost_key(row["startup_cost_g_per_start"]))
    manifest_rows = [
        {
            "startup_cost_g_per_start": row["startup_cost_g_per_start"],
            "config_path": row["config_path"],
            "run_dir": row["run_dir"],
        }
        for row in focus_rows
    ]

    write_csv(
        focus_rows,
        [
            "startup_cost_g_per_start",
            "config_path",
            "run_dir",
            "objective_value",
            "total_fuel_kg",
            "total_starts",
            "total_stops",
            "time_two_gensets_online_h",
            "share_two_gensets_online_pct",
            "total_online_genset_hours",
            "min_soc_pct",
            "terminal_soc_pct",
            "terminal_reference_soc_pct",
            "configured_soc_min_pct",
            "battery_throughput_kwh",
            "solve_time_s",
            "wall_clock_runtime_s",
            "warning",
        ],
        scan_summary_csv,
    )
    write_csv(
        manifest_rows,
        ["startup_cost_g_per_start", "config_path", "run_dir"],
        scan_manifest_csv,
    )
    write_scan_markdown(
        rows=focus_rows,
        path=scan_summary_md,
        baseline_startup_cost_g=baseline_startup_cost_g,
        new_case_costs=new_case_costs,
    )
    plot_scan(focus_rows, scan_plot_png, baseline_startup_cost_g=baseline_startup_cost_g)

    print(f"Saved {scan_manifest_csv}")
    print(f"Saved {scan_summary_csv}")
    print(f"Saved {scan_summary_md}")
    print(f"Saved {scan_plot_png}")


if __name__ == "__main__":
    main()
