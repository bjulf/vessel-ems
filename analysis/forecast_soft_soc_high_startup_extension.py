from __future__ import annotations

import csv
import subprocess
import time
import tomllib
from copy import deepcopy
from pathlib import Path

from oracle_operational_tuning_screen import write_rolling_config
from sensitivity_common import REPO_ROOT


BASE_CONFIG = REPO_ROOT / "config" / "rolling_horizon_operational.toml"
OUTPUT_DIR = (
    REPO_ROOT
    / "analysis"
    / "output"
    / "rolling_horizon"
    / "forecast_soft_soc_high_startup_extension"
)
GENERATED_CONFIG_DIR = OUTPUT_DIR / "generated_configs"

STARTUP_COSTS = [5000.0, 10000.0, 20000.0, 50000.0]
CASE_SPECS = [
    {"horizon_steps": 12, "soft_soc_penalty": 10000.0},
    {"horizon_steps": 16, "soft_soc_penalty": 1000.0},
]


def case_id(horizon_steps: int, soft_soc_penalty: float, startup_cost: float) -> str:
    return (
        f"h{horizon_steps}_softsoc{soft_soc_penalty:g}_startup{startup_cost:g}"
        .replace(".", "p")
        .replace("-", "m")
    )


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
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_config(base: dict, horizon_steps: int, soft_soc_penalty: float, startup_cost: float) -> dict:
    config = deepcopy(base)
    cid = case_id(horizon_steps, soft_soc_penalty, startup_cost)
    config["run"]["label"] = f"forecast_soft_soc_high_startup_{cid}"
    config["run"]["description"] = (
        f"{base['run']['description']} | high-startup extension: H={horizon_steps}, "
        f"mean soft SOC penalty={soft_soc_penalty:g} g/kWh, startup={startup_cost:g} g/start"
    )
    config["run"]["show_solver_log"] = False
    config["load_profile"]["path"] = "data/operational_profiles/operational_load_profile_15min_avg.csv"
    config["rolling_horizon"]["horizon_steps"] = int(horizon_steps)
    config["rolling_horizon"]["forecast_method"] = "moving_average"
    config["rolling_horizon"]["moving_average_window_steps"] = 4
    config["rolling_horizon"]["soc_strategy"] = "soft_band"
    config["rolling_horizon"].pop("terminal_soc_target", None)
    config["rolling_horizon"].pop("terminal_slack_penalty_g_per_kwh", None)
    config.setdefault("solver", {})
    config["solver"]["progress_log_enabled"] = False
    config["solver"]["slow_solve_log_threshold_sec"] = 999.0
    config.setdefault("soft_soc", {})
    config["soft_soc"]["preferred_soc_min"] = 0.20
    config["soft_soc"]["preferred_soc_max"] = 0.80
    config["soft_soc"]["soc_min_penalty_g_per_kwh"] = float(soft_soc_penalty)
    config["soft_soc"]["soc_max_penalty_g_per_kwh"] = float(soft_soc_penalty)
    config["soft_soc"]["soft_soc_penalty_scaling"] = "mean"
    for generator in config["generators"]:
        generator["startup_cost"] = float(startup_cost)
    return config


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
            elif run_length:
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


def summary_row(
    horizon_steps: int,
    soft_soc_penalty: float,
    startup_cost: float,
    config_path: Path,
    metadata: dict,
    run_dir: Path,
    wall_clock_s: float,
) -> dict[str, object]:
    rolling = metadata["kpis"]["rolling_horizon"]
    comparison = metadata["kpis"]["comparison"]
    full = metadata["kpis"]["full_horizon_benchmark"]
    short_runs, one_step_runs, two_step_runs = count_short_generator_runs(run_dir)
    return {
        "case_id": case_id(horizon_steps, soft_soc_penalty, startup_cost),
        "horizon_steps": horizon_steps,
        "horizon_hours": horizon_steps * metadata["rolling_horizon"]["dt_h"],
        "soft_soc_penalty_g_per_kwh": soft_soc_penalty,
        "startup_cost_g_per_start": startup_cost,
        "soft_soc_penalty_scaling": metadata["rolling_horizon"].get("soft_soc_penalty_scaling", "mean"),
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
        "local_low_soc_slack_kwh": rolling["local_total_soc_min_slack_kwh"],
        "median_solve_s": rolling["median_solve_time_s"],
        "p95_solve_s": rolling["p95_solve_time_s"],
        "max_solve_s": rolling["maximum_solve_time_s"],
        "nonoptimal_solves": rolling["nonoptimal_timeout_or_infeasible_solves"],
        "wall_clock_s": wall_clock_s,
        "config_path": str(config_path),
        "run_dir": str(run_dir),
    }


def write_markdown(path: Path, rows: list[dict[str, object]]) -> None:
    ordered = sorted(
        rows,
        key=lambda row: (
            int(float(row["horizon_steps"])),
            float(row["soft_soc_penalty_g_per_kwh"]),
            float(row["startup_cost_g_per_start"]),
        ),
    )
    lines = [
        "# Forecast Soft-SOC High Startup Extension",
        "",
        "Paired extension of two candidate mean-normalized soft-SOC controller settings.",
        "",
        "| Case | H | SOC penalty | Startup | Fuel delta % | Fuel kg | Starts | Short runs | Min SOC % | Final SOC % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in ordered:
        lines.append(
            f"| {row['case_id']} | {int(float(row['horizon_steps']))} | "
            f"{float(row['soft_soc_penalty_g_per_kwh']):.0f} | "
            f"{float(row['startup_cost_g_per_start']):.0f} | "
            f"{float(row['fuel_delta_vs_full_pct']):.2f} | {float(row['rolling_fuel_kg']):.3f} | "
            f"{int(float(row['rolling_starts']))} | {int(float(row['short_1_2_step_generator_runs']))} | "
            f"{float(row['rolling_min_soc_pct']):.2f} | {float(row['rolling_final_soc_pct']):.2f} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    with open(BASE_CONFIG, "rb") as fh:
        base_config = tomllib.load(fh)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = OUTPUT_DIR / "summary.csv"
    rows: list[dict[str, object]] = [dict(row) for row in load_existing_rows(summary_path)]
    completed = {str(row["case_id"]) for row in rows}

    for spec in CASE_SPECS:
        for startup_cost in STARTUP_COSTS:
            horizon_steps = int(spec["horizon_steps"])
            soft_soc_penalty = float(spec["soft_soc_penalty"])
            cid = case_id(horizon_steps, soft_soc_penalty, startup_cost)
            if cid in completed:
                print(f"Skipping existing {cid}", flush=True)
                continue
            print(f"Running {cid}", flush=True)
            config = build_config(base_config, horizon_steps, soft_soc_penalty, startup_cost)
            config_path = GENERATED_CONFIG_DIR / f"{cid}.toml"
            write_rolling_config(config, config_path)
            metadata, run_dir, wall_clock_s = run_case(config_path)
            row = summary_row(
                horizon_steps,
                soft_soc_penalty,
                startup_cost,
                config_path,
                metadata,
                run_dir,
                wall_clock_s,
            )
            rows.append(row)
            rows = sorted(
                rows,
                key=lambda item: (
                    int(float(item["horizon_steps"])),
                    float(item["soft_soc_penalty_g_per_kwh"]),
                    float(item["startup_cost_g_per_start"]),
                ),
            )
            write_csv(summary_path, rows)
            write_markdown(OUTPUT_DIR / "summary.md", rows)
            print(
                f"  fuel={float(row['rolling_fuel_kg']):.3f} kg, "
                f"delta={float(row['fuel_delta_vs_full_pct']):.2f}%, "
                f"starts={int(float(row['rolling_starts']))}, "
                f"short_runs={int(float(row['short_1_2_step_generator_runs']))}, "
                f"min SOC={float(row['rolling_min_soc_pct']):.2f}%, "
                f"final SOC={float(row['rolling_final_soc_pct']):.2f}%, "
                f"run={run_dir}",
                flush=True,
            )

    write_csv(summary_path, rows)
    write_markdown(OUTPUT_DIR / "summary.md", rows)
    print(f"Saved {summary_path}")
    print(f"Saved {OUTPUT_DIR / 'summary.md'}")


if __name__ == "__main__":
    main()
