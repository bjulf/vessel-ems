from __future__ import annotations

import argparse
import csv
import subprocess
import time
import tomllib
from copy import deepcopy
from pathlib import Path

from oracle_operational_tuning_screen import write_rolling_config
from sensitivity_common import REPO_ROOT


BASE_CONFIG = REPO_ROOT / "config" / "rolling_horizon_operational.toml"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "analysis" / "output" / "rolling_horizon" / "forecast_soft_soc_horizon_sweep"
DEFAULT_HORIZONS = [4, 8, 12, 16, 24, 32, 48, 72]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a soft-SOC-only horizon sweep for the operational forecast rolling MILP."
    )
    parser.add_argument(
        "--horizons",
        type=int,
        nargs="+",
        default=DEFAULT_HORIZONS,
        help="Rolling horizon lengths in 15-minute steps.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated configs, summary files, and downstream plots.",
    )
    parser.add_argument(
        "--soft-soc-penalty-scaling",
        choices=["sum", "mean"],
        default="sum",
        help="Whether local soft-SOC slack penalties use summed or horizon-mean violation.",
    )
    return parser.parse_args()


def load_existing_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def horizon_config(base: dict, horizon_steps: int, soft_soc_penalty_scaling: str) -> dict:
    config = deepcopy(base)
    suffix = "" if soft_soc_penalty_scaling == "sum" else "_mean_penalty"
    config["run"]["label"] = f"forecast_soft_soc_operational_h{horizon_steps}{suffix}"
    config["run"]["description"] = (
        f"{base['run']['description']} | soft-SOC horizon sweep: H={horizon_steps} "
        f"({horizon_steps * int(base['scheduling']['dt_minutes']) / 60:g} h), "
        f"soft SOC penalty scaling={soft_soc_penalty_scaling}"
    )
    config["run"]["show_solver_log"] = False
    config["load_profile"]["path"] = "data/operational_profiles/operational_load_profile_15min_avg.csv"
    config["rolling_horizon"]["horizon_steps"] = int(horizon_steps)
    config["rolling_horizon"]["forecast_method"] = "moving_average"
    config["rolling_horizon"]["moving_average_window_steps"] = 4
    config["rolling_horizon"]["soc_strategy"] = "soft_band"
    config["rolling_horizon"].pop("terminal_soc_target", None)
    config["rolling_horizon"].pop("terminal_slack_penalty_g_per_kwh", None)
    config.setdefault("soft_soc", {})
    config["soft_soc"]["preferred_soc_min"] = 0.20
    config["soft_soc"]["preferred_soc_max"] = 0.80
    config["soft_soc"]["soc_min_penalty_g_per_kwh"] = 1000.0
    config["soft_soc"]["soc_max_penalty_g_per_kwh"] = 1000.0
    config["soft_soc"]["soft_soc_penalty_scaling"] = soft_soc_penalty_scaling
    config.setdefault("solver", {})
    config["solver"]["progress_log_enabled"] = False
    config["solver"]["slow_solve_log_threshold_sec"] = 999.0
    for generator in config["generators"]:
        generator["startup_cost"] = 1000.0
    return config


def run_case(config_path: Path) -> tuple[dict, Path, float]:
    started_at = time.perf_counter()
    completed = subprocess.run(
        ["julia", "--project=.", "main_rolling_horizon.jl", str(config_path.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    wall_clock_s = time.perf_counter() - started_at
    if completed.returncode != 0:
        raise RuntimeError(
            f"Case failed: {config_path}\nSTDOUT:\n{completed.stdout[-4000:]}\nSTDERR:\n{completed.stderr[-4000:]}"
        )
    run_dir = Path((REPO_ROOT / ".current_run").read_text(encoding="utf-8").strip())
    with open(run_dir / "params.toml", "rb") as fh:
        metadata = tomllib.load(fh)
    return metadata, run_dir, wall_clock_s


def count_short_generator_runs(run_dir: Path) -> tuple[int, int, int]:
    by_generator: dict[str, list[tuple[int, int]]] = {}
    with open(run_dir / "dispatch_results.csv", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            by_generator.setdefault(row["generator"], []).append(
                (int(row["timestep"]), 1 if float(row["u"]) > 0.5 else 0)
            )

    one_step = 0
    two_step = 0
    for rows in by_generator.values():
        run_length = 0
        for _, is_on in sorted(rows):
            if is_on:
                run_length += 1
            elif run_length > 0:
                if run_length == 1:
                    one_step += 1
                elif run_length == 2:
                    two_step += 1
                run_length = 0
        if run_length == 1:
            one_step += 1
        elif run_length == 2:
            two_step += 1
    return one_step + two_step, one_step, two_step


def summary_row(horizon_steps: int, config_path: Path, metadata: dict, run_dir: Path, wall_clock_s: float) -> dict[str, object]:
    rolling = metadata["kpis"]["rolling_horizon"]
    full = metadata["kpis"]["full_horizon_benchmark"]
    comparison = metadata["kpis"]["comparison"]
    short_runs, one_step_runs, two_step_runs = count_short_generator_runs(run_dir)
    return {
        "horizon_steps": horizon_steps,
        "horizon_hours": horizon_steps * metadata["rolling_horizon"]["dt_h"],
        "forecast_method": metadata["rolling_horizon"]["forecast_method"],
        "moving_average_window_steps": metadata["rolling_horizon"]["moving_average_window_steps"],
        "soft_soc_penalty_scaling": metadata["rolling_horizon"].get("soft_soc_penalty_scaling", "sum"),
        "rolling_fuel_kg": rolling["total_fuel_kg"],
        "rolling_starts": rolling["generator_starts"],
        "short_1_2_step_generator_runs": short_runs,
        "one_step_generator_runs": one_step_runs,
        "two_step_generator_runs": two_step_runs,
        "rolling_min_soc_pct": rolling["minimum_soc_pct"],
        "rolling_max_soc_pct": rolling["maximum_soc_pct"],
        "rolling_final_soc_pct": rolling["final_soc_pct"],
        "fuel_delta_vs_full_kg": comparison["fuel_delta_g"] / 1000.0,
        "fuel_delta_vs_full_pct": comparison["fuel_delta_pct"],
        "starts_delta_vs_full": comparison["generator_starts_delta"],
        "full_fuel_kg": full["total_fuel_kg"],
        "full_starts": full["generator_starts"],
        "realized_low_soc_slack_kwh": rolling["realized_total_soc_min_slack_kwh"],
        "realized_high_soc_slack_kwh": rolling["realized_total_soc_max_slack_kwh"],
        "local_low_soc_slack_kwh": rolling["local_total_soc_min_slack_kwh"],
        "local_high_soc_slack_kwh": rolling["local_total_soc_max_slack_kwh"],
        "median_solve_s": rolling["median_solve_time_s"],
        "p95_solve_s": rolling["p95_solve_time_s"],
        "max_solve_s": rolling["maximum_solve_time_s"],
        "nonoptimal_solves": rolling["nonoptimal_timeout_or_infeasible_solves"],
        "tail_padded_solves": metadata["rolling_horizon"]["tail_forecast_padded_solves"],
        "wall_clock_s": wall_clock_s,
        "config_path": str(config_path),
        "run_dir": str(run_dir),
    }


def write_markdown(path: Path, rows: list[dict[str, object]], soft_soc_penalty_scaling: str) -> None:
    rows = sorted(rows, key=lambda row: int(float(row["horizon_steps"])))
    ranked = sorted(rows, key=lambda row: (float(row["fuel_delta_vs_full_pct"]), int(float(row["rolling_starts"]))))
    lines = [
        "# Forecast Soft-SOC Horizon Sweep",
        "",
        "Operational 15-minute average profile, moving-average forecast, soft 20-80% SOC band.",
        f"Soft SOC penalty scaling: `{soft_soc_penalty_scaling}`.",
        "",
        "## By Horizon",
        "",
        "| H steps | Horizon h | Fuel kg | Delta % | Starts | Short runs | Min SOC % | Final SOC % | P95 solve s | Non-opt |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| "
            f"{int(float(row['horizon_steps']))} | {float(row['horizon_hours']):.2f} | "
            f"{float(row['rolling_fuel_kg']):.3f} | {float(row['fuel_delta_vs_full_pct']):.2f} | "
            f"{int(float(row['rolling_starts']))} | {int(float(row.get('short_1_2_step_generator_runs', 0)))} | "
            f"{float(row['rolling_min_soc_pct']):.2f} | "
            f"{float(row['rolling_final_soc_pct']):.2f} | {float(row['p95_solve_s']):.3f} | "
            f"{int(float(row['nonoptimal_solves']))} |"
        )
    lines.extend(
        [
            "",
            "## Ranked By Fuel Delta",
            "",
            "| Rank | H steps | Horizon h | Fuel kg | Delta % | Starts | Final SOC % |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for idx, row in enumerate(ranked, start=1):
        lines.append(
            "| "
            f"{idx} | {int(float(row['horizon_steps']))} | {float(row['horizon_hours']):.2f} | "
            f"{float(row['rolling_fuel_kg']):.3f} | {float(row['fuel_delta_vs_full_pct']):.2f} | "
            f"{int(float(row['rolling_starts']))} | {float(row['rolling_final_soc_pct']):.2f} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else REPO_ROOT / args.output_dir
    generated_config_dir = output_dir / "generated_configs"
    with open(BASE_CONFIG, "rb") as fh:
        base_config = tomllib.load(fh)

    output_dir.mkdir(parents=True, exist_ok=True)
    generated_config_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.csv"
    rows: list[dict[str, object]] = [dict(row) for row in load_existing_rows(summary_path)]
    completed_horizons = {int(float(row["horizon_steps"])) for row in rows}

    for horizon in args.horizons:
        if horizon in completed_horizons:
            print(f"Skipping existing H={horizon}", flush=True)
            continue
        print(f"Running H={horizon} ({horizon * int(base_config['scheduling']['dt_minutes']) / 60:g} h)", flush=True)
        config = horizon_config(base_config, horizon, args.soft_soc_penalty_scaling)
        suffix = "" if args.soft_soc_penalty_scaling == "sum" else f"_{args.soft_soc_penalty_scaling}_penalty"
        config_path = generated_config_dir / f"forecast_soft_soc_h{horizon}{suffix}.toml"
        write_rolling_config(config, config_path)
        metadata, run_dir, wall_clock_s = run_case(config_path)
        row = summary_row(horizon, config_path, metadata, run_dir, wall_clock_s)
        rows.append(row)
        rows = sorted(rows, key=lambda item: int(float(item["horizon_steps"])))
        write_csv(summary_path, rows)
        write_markdown(output_dir / "summary.md", rows, args.soft_soc_penalty_scaling)
        print(
            f"  fuel={float(row['rolling_fuel_kg']):.3f} kg, "
            f"delta={float(row['fuel_delta_vs_full_pct']):.2f}%, "
            f"starts={int(float(row['rolling_starts']))}, "
            f"short_runs={int(float(row['short_1_2_step_generator_runs']))}, "
            f"final SOC={float(row['rolling_final_soc_pct']):.2f}%, "
            f"run={run_dir}",
            flush=True,
        )

    write_csv(summary_path, rows)
    write_markdown(output_dir / "summary.md", rows, args.soft_soc_penalty_scaling)
    print(f"Saved {summary_path}")
    print(f"Saved {output_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
