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


DEFAULT_STARTUP_COSTS_G = [350, 500, 550, 600, 650, 700, 1000, 1500]
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a startup-cost sensitivity sweep from a baseline model config."
    )
    parser.add_argument(
        "config",
        nargs="?",
        default="config/baseline_model.toml",
        help="Config path relative to repo root or absolute path.",
    )
    parser.add_argument(
        "--startup-costs",
        type=float,
        nargs="+",
        default=DEFAULT_STARTUP_COSTS_G,
        help="Startup-cost values in g/start to apply to every generator.",
    )
    return parser.parse_args()


def build_case_config(base_config: dict, startup_cost_g: float) -> dict:
    startup_cost_label = str(int(startup_cost_g)) if float(startup_cost_g).is_integer() else str(startup_cost_g)
    case_config = clone_case_config(
        base_config,
        label_suffix=f"cstart_{startup_cost_label}g",
        description_suffix=f"startup-cost sensitivity case: {startup_cost_label} g/start",
    )
    for generator in case_config["generators"]:
        generator["startup_cost"] = float(startup_cost_g)
    return case_config


def write_summary_text(rows: list[dict[str, object]], config_path: Path, output_dir: Path, path: Path) -> None:
    fuel_values = [float(row["total_fuel_kg"]) for row in rows]
    start_values = [int(row["total_starts"]) for row in rows]
    online_values = [float(row["time_two_gensets_online_h"]) for row in rows]

    min_fuel_row = min(rows, key=lambda row: float(row["total_fuel_kg"]))
    min_starts_row = min(rows, key=lambda row: int(row["total_starts"]))
    max_starts_row = max(rows, key=lambda row: int(row["total_starts"]))

    lines = [
        f"Startup-cost sensitivity summary for {config_path.relative_to(REPO_ROOT)}",
        "",
        "Cases [g/start]: " + ", ".join(str(int(row["startup_cost_g_per_start"])) for row in rows),
        "",
        f"Fuel range [kg]: {min(fuel_values):.3f} to {max(fuel_values):.3f}",
        f"Starts range: {min(start_values)} to {max(start_values)}",
        f"Time with 2 gensets online [h]: {min(online_values):.2f} to {max(online_values):.2f}",
        "",
        (
            "Lowest-fuel case: "
            f"{int(min_fuel_row['startup_cost_g_per_start'])} g/start "
            f"with {min_fuel_row['total_fuel_kg']:.3f} kg fuel, "
            f"{min_fuel_row['total_starts']} starts, and "
            f"{min_fuel_row['time_two_gensets_online_h']:.2f} h with 2 gensets online"
        ),
        (
            "Fewest-starts case: "
            f"{int(min_starts_row['startup_cost_g_per_start'])} g/start "
            f"with {min_starts_row['total_starts']} starts"
        ),
        (
            "Most-starts case: "
            f"{int(max_starts_row['startup_cost_g_per_start'])} g/start "
            f"with {max_starts_row['total_starts']} starts"
        ),
        "",
        f"Manifest: {output_dir / 'run_manifest.csv'}",
        f"Summary: {output_dir / 'summary.csv'}",
        f"Overview plot: {output_dir / 'overview.png'}",
        f"Tradeoff plot: {output_dir / 'fuel_vs_starts.png'}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary_markdown(
    rows: list[dict[str, object]],
    config_path: Path,
    output_dir: Path,
    path: Path,
    *,
    baseline_startup_cost_g: float,
) -> None:
    baseline_row = next(
        (row for row in rows if float(row["startup_cost_g_per_start"]) == float(baseline_startup_cost_g)),
        None,
    )
    baseline_startup_cost_label = (
        str(int(baseline_startup_cost_g))
        if float(baseline_startup_cost_g).is_integer()
        else str(baseline_startup_cost_g)
    )
    intro_lines = [
        f"Config: `{config_path.relative_to(REPO_ROOT).as_posix()}`",
        f"Cases run: {len(rows)}",
        (
            f"Baseline case at {baseline_startup_cost_label} g/start: "
            f"{baseline_row['total_fuel_kg']:.3f} kg fuel, {baseline_row['total_starts']} starts, "
            f"terminal SOC {baseline_row['terminal_soc_pct']:.2f}%."
            if baseline_row
            else f"Baseline case at {baseline_startup_cost_label} g/start was not present in this sweep."
        ),
    ]
    write_markdown_summary(
        path,
        title="Startup-Cost Sensitivity Summary",
        intro_lines=intro_lines,
        columns=[
            ("Startup Cost [g/start]", "startup_cost_g_per_start"),
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
    labels = [str(int(row["startup_cost_g_per_start"])) for row in rows]
    x = list(range(len(rows)))
    total_fuel = [float(row["total_fuel_kg"]) for row in rows]
    starts = [int(row["total_starts"]) for row in rows]
    time_two_online = [float(row["time_two_gensets_online_h"]) for row in rows]

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(3, 1, figsize=(11, 13), constrained_layout=True)

    panels = [
        (total_fuel, "Total fuel [kg]", "Fuel response", "#0f766e"),
        (starts, "count", "Generator starts", "#7c2d12"),
        (time_two_online, "h", "Time with 2 gensets online", "#1d4ed8"),
    ]

    for ax, (values, ylabel, title, color) in zip(axes, panels):
        ax.plot(x, values, marker="o", linewidth=2.4, markersize=7, color=color)
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=15)
        for idx, value in enumerate(values):
            ax.annotate(
                f"{value:.2f}" if isinstance(value, float) and not float(value).is_integer() else f"{int(value)}",
                (x[idx], value),
                textcoords="offset points",
                xytext=(0, 8),
                ha="center",
                fontsize=10,
            )

    for ax in axes:
        ax.set_xticks(x, labels)
        ax.tick_params(axis="both", labelsize=11)
        ax.set_xlabel("Startup cost [g/start]", fontsize=12)

    fig.suptitle("Startup-cost sensitivity sweep", fontsize=18, fontweight="bold")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_tradeoff(rows: list[dict[str, object]], path: Path) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(8.5, 6.5), constrained_layout=True)

    fuel = [float(row["total_fuel_kg"]) for row in rows]
    starts = [int(row["total_starts"]) for row in rows]
    labels = [str(int(row["startup_cost_g_per_start"])) for row in rows]

    ax.scatter(fuel, starts, s=80, color="#7c2d12")
    for fuel_value, start_value, label in zip(fuel, starts, labels):
        ax.annotate(f"{label} g", (fuel_value, start_value), textcoords="offset points", xytext=(8, 6), fontsize=10)

    ax.set_xlabel("Total fuel [kg]", fontsize=12)
    ax.set_ylabel("Total starts [count]", fontsize=12)
    ax.set_title("Startup-cost tradeoff: fuel vs starts", fontsize=16)
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
    baseline_startup_cost_g = float(base_config["generators"][0]["startup_cost"])
    output_dir, generated_configs_dir = create_output_dirs("startup_cost", sensitivity_output_root(base_config))

    rows: list[dict[str, object]] = []
    manifest_rows: list[dict[str, object]] = []

    for startup_cost_g in args.startup_costs:
        print(f"Running startup_cost = {startup_cost_g:.0f} g/start")
        case_config = build_case_config(base_config, startup_cost_g)
        config_stub = str(int(startup_cost_g)) if float(startup_cost_g).is_integer() else str(startup_cost_g).replace(".", "p")
        case_config_path = generated_configs_dir / f"startup_cost_{config_stub}g.toml"
        write_config(case_config, case_config_path)

        metadata, run_dir, wall_clock_runtime_s = run_case(case_config_path)
        metrics = compute_run_metrics(run_dir, metadata)
        terminal_reference_soc_pct = float(
            metadata["validation"]["battery_energy"].get("terminal_target_min_soc_pct", 0.0)
        )
        configured_soc_min_pct = float(case_config["battery"]["SOC_min"]) * 100.0

        row = {
            "startup_cost_g_per_start": int(startup_cost_g) if float(startup_cost_g).is_integer() else float(startup_cost_g),
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
        rows.append(row)
        manifest_rows.append(
            {
                "startup_cost_g_per_start": row["startup_cost_g_per_start"],
                "config_path": row["config_path"],
                "run_dir": row["run_dir"],
            }
        )

    rows.sort(key=lambda row: float(row["startup_cost_g_per_start"]))
    manifest_rows.sort(key=lambda row: float(row["startup_cost_g_per_start"]))

    summary_csv = output_dir / "summary.csv"
    manifest_csv = output_dir / "run_manifest.csv"
    summary_txt = output_dir / "summary.txt"
    summary_md = output_dir / "summary.md"
    summary_png = output_dir / "overview.png"
    tradeoff_png = output_dir / "fuel_vs_starts.png"

    write_csv(
        rows,
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
        summary_csv,
    )
    write_csv(
        manifest_rows,
        ["startup_cost_g_per_start", "config_path", "run_dir"],
        manifest_csv,
    )
    write_summary_text(rows, config_path, output_dir, summary_txt)
    write_summary_markdown(
        rows,
        config_path,
        output_dir,
        summary_md,
        baseline_startup_cost_g=baseline_startup_cost_g,
    )
    plot_summary(rows, summary_png)
    plot_tradeoff(rows, tradeoff_png)

    print(f"Saved {manifest_csv}")
    print(f"Saved {summary_csv}")
    print(f"Saved {summary_txt}")
    print(f"Saved {summary_md}")
    print(f"Saved {summary_png}")
    print(f"Saved {tradeoff_png}")


if __name__ == "__main__":
    main()
