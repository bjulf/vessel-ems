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
    resolve_repo_path,
    run_case,
    write_config,
    write_csv,
)


OUTPUT_DIR, GENERATED_CONFIGS_DIR = create_output_dirs("battery_efficiency")
DEFAULT_BATTERY_EFFICIENCIES = [0.92, 0.95, 0.98]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a battery-efficiency sensitivity sweep from a baseline model config."
    )
    parser.add_argument(
        "config",
        nargs="?",
        default="config/baseline_model.toml",
        help="Config path relative to repo root or absolute path.",
    )
    parser.add_argument(
        "--efficiencies",
        type=float,
        nargs="+",
        default=DEFAULT_BATTERY_EFFICIENCIES,
        help="Battery charge/discharge efficiency values to apply symmetrically, as fractions.",
    )
    return parser.parse_args()


def build_case_config(base_config: dict, efficiency: float) -> dict:
    efficiency_pct = int(round(float(efficiency) * 100))
    case_config = clone_case_config(
        base_config,
        label_suffix=f"eta_{efficiency_pct}pct",
        description_suffix=f"battery-efficiency sensitivity case: {efficiency_pct} percent",
    )
    case_config["battery"]["eta_ch"] = float(efficiency)
    case_config["battery"]["eta_dis"] = float(efficiency)
    return case_config


def write_summary_text(rows: list[dict[str, object]], config_path: Path, path: Path) -> None:
    fuel_values = [float(row["total_fuel_kg"]) for row in rows]
    start_values = [int(row["total_starts"]) for row in rows]
    min_soc_values = [float(row["min_soc_pct"]) for row in rows]
    throughput_values = [float(row["battery_throughput_kwh"]) for row in rows]

    lines = [
        f"Battery-efficiency sensitivity summary for {config_path.relative_to(REPO_ROOT)}",
        "",
        "Cases [-]: " + ", ".join(f"{float(row['battery_efficiency']):.2f}" for row in rows),
        "",
        f"Fuel range [kg]: {min(fuel_values):.3f} to {max(fuel_values):.3f}",
        f"Starts range: {min(start_values)} to {max(start_values)}",
        f"Minimum-SOC range [%]: {min(min_soc_values):.2f} to {max(min_soc_values):.2f}",
        f"Battery throughput range [kWh]: {min(throughput_values):.1f} to {max(throughput_values):.1f}",
        "",
        f"Manifest: {OUTPUT_DIR / 'run_manifest.csv'}",
        f"Summary: {OUTPUT_DIR / 'summary.csv'}",
        f"Overview plot: {OUTPUT_DIR / 'overview.png'}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_summary(rows: list[dict[str, object]], path: Path) -> None:
    labels = [f"{float(row['battery_efficiency']):.2f}" for row in rows]
    x = list(range(len(rows)))
    total_fuel = [float(row["total_fuel_kg"]) for row in rows]
    starts = [int(row["total_starts"]) for row in rows]
    min_soc = [float(row["min_soc_pct"]) for row in rows]
    throughput = [float(row["battery_throughput_kwh"]) for row in rows]

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)

    panels = [
        (total_fuel, "Total fuel [kg]", "Fuel response", "#0f766e"),
        (starts, "count", "Generator starts", "#7c2d12"),
        (min_soc, "SOC [%]", "Minimum SOC", "#1d4ed8"),
        (throughput, "kWh", "Battery throughput", "#b45309"),
    ]

    for ax, (values, ylabel, title, color) in zip(axes.flatten(), panels):
        ax.plot(x, values, marker="o", linewidth=2.4, markersize=7, color=color)
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=15)
        ax.set_xticks(x, labels)
        ax.tick_params(axis="both", labelsize=11)
        ax.set_xlabel("Battery charge/discharge efficiency [-]", fontsize=12)

    fig.suptitle("Battery-efficiency sensitivity sweep", fontsize=18, fontweight="bold")
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

    rows: list[dict[str, object]] = []
    manifest_rows: list[dict[str, object]] = []

    for efficiency in args.efficiencies:
        print(f"Running battery efficiency = {efficiency:.2f}")
        case_config = build_case_config(base_config, efficiency)
        efficiency_stub = f"{int(round(float(efficiency) * 100)):02d}"
        case_config_path = GENERATED_CONFIGS_DIR / f"battery_efficiency_{efficiency_stub}pct.toml"
        write_config(case_config, case_config_path)

        metadata, run_dir = run_case(case_config_path)
        metrics = compute_run_metrics(run_dir, metadata)

        row = {
            "battery_efficiency": float(efficiency),
            "config_path": str(case_config_path),
            "run_dir": str(run_dir),
            "total_fuel_kg": float(metrics["total_fuel_kg"]),
            "total_starts": int(metrics["total_starts"]),
            "time_two_gensets_online_h": float(metrics["time_two_gensets_online_h"]),
            "min_soc_pct": float(metrics["min_soc_pct"]),
            "terminal_soc_pct": float(metrics["terminal_soc_pct"]),
            "battery_throughput_kwh": float(metrics["battery_throughput_kwh"]),
            "solve_time_s": float(metadata["solver"]["solve_time_s"]),
        }
        rows.append(row)
        manifest_rows.append(
            {
                "battery_efficiency": row["battery_efficiency"],
                "config_path": row["config_path"],
                "run_dir": row["run_dir"],
            }
        )

    rows.sort(key=lambda row: float(row["battery_efficiency"]))
    manifest_rows.sort(key=lambda row: float(row["battery_efficiency"]))

    summary_csv = OUTPUT_DIR / "summary.csv"
    manifest_csv = OUTPUT_DIR / "run_manifest.csv"
    summary_txt = OUTPUT_DIR / "summary.txt"
    summary_png = OUTPUT_DIR / "overview.png"

    write_csv(
        rows,
        [
            "battery_efficiency",
            "config_path",
            "run_dir",
            "total_fuel_kg",
            "total_starts",
            "time_two_gensets_online_h",
            "min_soc_pct",
            "terminal_soc_pct",
            "battery_throughput_kwh",
            "solve_time_s",
        ],
        summary_csv,
    )
    write_csv(
        manifest_rows,
        ["battery_efficiency", "config_path", "run_dir"],
        manifest_csv,
    )
    write_summary_text(rows, config_path, summary_txt)
    plot_summary(rows, summary_png)

    print(f"Saved {manifest_csv}")
    print(f"Saved {summary_csv}")
    print(f"Saved {summary_txt}")
    print(f"Saved {summary_png}")


if __name__ == "__main__":
    main()
