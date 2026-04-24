from __future__ import annotations

import argparse
import tomllib
from pathlib import Path

import matplotlib.pyplot as plt

from sensitivity_common import (
    REPO_ROOT,
    clone_case_config,
    compute_run_metrics,
    create_output_dirs,
    infer_case_warning,
    resolve_repo_path,
    repo_relative_str,
    run_case,
    sensitivity_output_root,
    write_config,
    write_csv,
    write_markdown_summary,
)


DEFAULT_INITIAL_SOCS_PCT = [50, 60, 70, 80]
BASELINE_INITIAL_SOC_PCT = 70


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an initial-SOC sensitivity sweep from a baseline model config."
    )
    parser.add_argument(
        "config",
        nargs="?",
        default="config/baseline_model.toml",
        help="Config path relative to repo root or absolute path.",
    )
    parser.add_argument(
        "--initial-soc-values",
        type=float,
        nargs="+",
        default=DEFAULT_INITIAL_SOCS_PCT,
        help="Initial SOC values in percent of battery capacity.",
    )
    return parser.parse_args()


def build_case_config(base_config: dict, initial_soc_pct: float) -> dict:
    initial_soc_label = str(int(initial_soc_pct)) if float(initial_soc_pct).is_integer() else str(initial_soc_pct)
    case_config = clone_case_config(
        base_config,
        label_suffix=f"initialsoc_{initial_soc_label}pct",
        description_suffix=f"initial-SOC sensitivity case: {initial_soc_label} percent",
    )
    e_max = float(case_config["battery"]["E_max"])
    case_config["initial_conditions"]["battery_energy_kwh"] = e_max * float(initial_soc_pct) / 100.0
    return case_config


def write_summary_text(rows: list[dict[str, object]], config_path: Path, output_dir: Path, path: Path) -> None:
    fuel_values = [float(row["total_fuel_kg"]) for row in rows]
    start_values = [int(row["total_starts"]) for row in rows]
    throughput_values = [float(row["battery_throughput_kwh"]) for row in rows]

    lines = [
        f"Initial-SOC sensitivity summary for {config_path.relative_to(REPO_ROOT)}",
        "",
        "Cases [%]: " + ", ".join(str(int(row["initial_soc_pct"])) for row in rows),
        "",
        f"Fuel range [kg]: {min(fuel_values):.3f} to {max(fuel_values):.3f}",
        f"Starts range: {min(start_values)} to {max(start_values)}",
        f"Battery throughput range [kWh]: {min(throughput_values):.1f} to {max(throughput_values):.1f}",
        "",
        f"Manifest: {output_dir / 'run_manifest.csv'}",
        f"Summary: {output_dir / 'summary.csv'}",
        f"Overview plot: {output_dir / 'overview.png'}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary_markdown(rows: list[dict[str, object]], config_path: Path, output_dir: Path, path: Path) -> None:
    baseline_row = next(
        (row for row in rows if float(row["initial_soc_pct"]) == float(BASELINE_INITIAL_SOC_PCT)),
        None,
    )
    intro_lines = [
        f"Config: `{config_path.relative_to(REPO_ROOT).as_posix()}`",
        f"Cases run: {len(rows)}",
        (
            "Baseline case at 70% initial SOC: "
            f"{baseline_row['total_fuel_kg']:.3f} kg fuel, {baseline_row['total_starts']} starts, "
            f"terminal SOC {baseline_row['terminal_soc_pct']:.2f}%."
            if baseline_row
            else "Baseline case at 70% initial SOC was not present in this sweep."
        ),
    ]
    write_markdown_summary(
        path,
        title="Initial-SOC Sensitivity Summary",
        intro_lines=intro_lines,
        columns=[
            ("Initial SOC [%]", "initial_soc_pct"),
            ("Config", lambda row: f"`{repo_relative_str(str(row['config_path']))}`"),
            ("Run Dir", lambda row: f"`{repo_relative_str(str(row['run_dir']))}`"),
            ("Objective", "objective_value"),
            ("Fuel [kg]", "total_fuel_kg"),
            ("Starts", "total_starts"),
            ("Stops", "total_stops"),
            ("Min SOC [%]", "min_soc_pct"),
            ("Terminal SOC [%]", "terminal_soc_pct"),
            ("Throughput [kWh]", "battery_throughput_kwh"),
            ("Solve [s]", "solve_time_s"),
            ("Wall [s]", "wall_clock_runtime_s"),
            ("Warnings", "warning"),
        ],
        rows=rows,
    )


def plot_summary(rows: list[dict[str, object]], path: Path) -> None:
    labels = [str(int(row["initial_soc_pct"])) for row in rows]
    x = list(range(len(rows)))
    total_fuel = [float(row["total_fuel_kg"]) for row in rows]
    starts = [int(row["total_starts"]) for row in rows]
    terminal_soc = [float(row["terminal_soc_pct"]) for row in rows]
    throughput = [float(row["battery_throughput_kwh"]) for row in rows]

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)

    panels = [
        (total_fuel, "Total fuel [kg]", "Fuel response", "#0f766e"),
        (starts, "count", "Generator starts", "#7c2d12"),
        (terminal_soc, "SOC [%]", "Terminal SOC", "#9333ea"),
        (throughput, "kWh", "Battery throughput", "#b45309"),
    ]

    for ax, (values, ylabel, title, color) in zip(axes.flatten(), panels):
        ax.plot(x, values, marker="o", linewidth=2.4, markersize=7, color=color)
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=15)
        ax.set_xticks(x, labels)
        ax.tick_params(axis="both", labelsize=11)
        ax.set_xlabel("Initial SOC [%]", fontsize=12)

    fig.suptitle("Initial-SOC sensitivity sweep", fontsize=18, fontweight="bold")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    config_path = resolve_repo_path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config file: {config_path}")
    if not config_path.is_relative_to(REPO_ROOT):
        raise ValueError("Config path must be inside the repository.")

    with open(config_path, "rb") as fh:
        base_config = tomllib.load(fh)
    output_dir, generated_configs_dir = create_output_dirs("initial_soc", sensitivity_output_root(base_config))

    rows: list[dict[str, object]] = []
    manifest_rows: list[dict[str, object]] = []

    for initial_soc_pct in args.initial_soc_values:
        print(f"Running initial_soc = {initial_soc_pct:.0f}%")
        case_config = build_case_config(base_config, initial_soc_pct)
        config_stub = str(int(initial_soc_pct)) if float(initial_soc_pct).is_integer() else str(initial_soc_pct).replace(".", "p")
        case_config_path = generated_configs_dir / f"initial_soc_{config_stub}pct.toml"
        write_config(case_config, case_config_path)

        metadata, run_dir, wall_clock_runtime_s = run_case(case_config_path)
        metrics = compute_run_metrics(run_dir, metadata)
        terminal_reference_soc_pct = float(
            metadata["validation"]["battery_energy"].get("terminal_target_min_soc_pct", 0.0)
        )
        configured_soc_min_pct = float(case_config["battery"]["SOC_min"]) * 100.0

        row = {
            "initial_soc_pct": int(initial_soc_pct) if float(initial_soc_pct).is_integer() else float(initial_soc_pct),
            "config_path": str(case_config_path),
            "run_dir": str(run_dir),
            "objective_value": float(metadata["solver"]["objective"]),
            "total_fuel_kg": float(metrics["total_fuel_kg"]),
            "total_starts": int(metrics["total_starts"]),
            "total_stops": int(metrics["total_stops"]),
            "time_two_gensets_online_h": float(metrics["time_two_gensets_online_h"]),
            "terminal_soc_pct": float(metrics["terminal_soc_pct"]),
            "min_soc_pct": float(metrics["min_soc_pct"]),
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
        rows.append(row)
        manifest_rows.append(
            {
                "initial_soc_pct": row["initial_soc_pct"],
                "config_path": row["config_path"],
                "run_dir": row["run_dir"],
            }
        )

    rows.sort(key=lambda row: float(row["initial_soc_pct"]))
    manifest_rows.sort(key=lambda row: float(row["initial_soc_pct"]))

    summary_csv = output_dir / "summary.csv"
    manifest_csv = output_dir / "run_manifest.csv"
    summary_txt = output_dir / "summary.txt"
    summary_md = output_dir / "summary.md"
    summary_png = output_dir / "overview.png"

    write_csv(
        rows,
        [
            "initial_soc_pct",
            "config_path",
            "run_dir",
            "objective_value",
            "total_fuel_kg",
            "total_starts",
            "total_stops",
            "time_two_gensets_online_h",
            "terminal_soc_pct",
            "min_soc_pct",
            "terminal_reference_soc_pct",
            "configured_soc_min_pct",
            "battery_throughput_kwh",
            "solve_time_s",
            "wall_clock_runtime_s",
            "warning",
        ],
        summary_csv,
    )
    write_csv(
        manifest_rows,
        ["initial_soc_pct", "config_path", "run_dir"],
        manifest_csv,
    )
    write_summary_text(rows, config_path, output_dir, summary_txt)
    write_summary_markdown(rows, config_path, output_dir, summary_md)
    plot_summary(rows, summary_png)

    print(f"Saved {manifest_csv}")
    print(f"Saved {summary_csv}")
    print(f"Saved {summary_txt}")
    print(f"Saved {summary_md}")
    print(f"Saved {summary_png}")


if __name__ == "__main__":
    main()
