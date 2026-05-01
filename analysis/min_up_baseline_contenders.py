from __future__ import annotations

import csv
import subprocess
import time
import tomllib
from copy import deepcopy
from pathlib import Path

from oracle_operational_tuning_screen import write_rolling_config
from sensitivity_common import REPO_ROOT


BASE_CONFIG = REPO_ROOT / "config" / "rolling_horizon_soft_soc_min_up6_operational.toml"
OUTPUT_DIR = REPO_ROOT / "analysis" / "output" / "rolling_horizon" / "min_up_baseline_contenders"
GENERATED_CONFIG_DIR = OUTPUT_DIR / "generated_configs"

CASES = [
    {"case_id": "h12_startup500_softsoc10000_minup6", "horizon": 12, "startup": 500.0, "soft_soc": 10000.0},
    {"case_id": "h12_startup0_softsoc10000_minup6", "horizon": 12, "startup": 0.0, "soft_soc": 10000.0},
    {"case_id": "h12_startup0_softsoc1000_minup6", "horizon": 12, "startup": 0.0, "soft_soc": 1000.0},
    {"case_id": "h16_startup0_softsoc1000_minup6", "horizon": 16, "startup": 0.0, "soft_soc": 1000.0},
    {"case_id": "h12_startup1000_softsoc10000_minup6", "horizon": 12, "startup": 1000.0, "soft_soc": 10000.0},
]


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


def contender_config(base: dict, case: dict[str, object]) -> dict:
    config = deepcopy(base)
    case_id = str(case["case_id"])
    horizon = int(case["horizon"])
    startup = float(case["startup"])
    soft_soc = float(case["soft_soc"])

    config["run"]["label"] = f"rolling_horizon_{case_id}"
    config["run"]["description"] = (
        "Operational 15-minute average-load forecast rolling-horizon MILP contender: "
        f"H={horizon}, startup={startup:g} g/start, mean soft-SOC penalty={soft_soc:g} g/kWh, "
        "6-step minimum up-time"
    )
    config["run"]["show_solver_log"] = False
    config["load_profile"]["path"] = "data/operational_profiles/operational_load_profile_15min_avg.csv"
    config["rolling_horizon"]["horizon_steps"] = horizon
    config["rolling_horizon"]["forecast_method"] = "moving_average"
    config["rolling_horizon"]["moving_average_window_steps"] = 4
    config["rolling_horizon"]["soc_strategy"] = "soft_band"
    config["rolling_horizon"]["tail_forecast_policy"] = "repeat_final_load"
    config["rolling_horizon"]["min_up_time_steps"] = 6
    config["rolling_horizon"]["soft_band_terminal_reserve_enabled"] = False
    config["rolling_horizon"].pop("terminal_soc_target", None)
    config["rolling_horizon"].pop("terminal_slack_penalty_g_per_kwh", None)

    config.setdefault("solver", {})
    config["solver"]["progress_log_enabled"] = False
    config["solver"]["slow_solve_log_threshold_sec"] = 999.0
    config["solver"]["rolling_local_time_limit_sec"] = 30.0

    config.setdefault("soft_soc", {})
    config["soft_soc"]["preferred_soc_min"] = 0.20
    config["soft_soc"]["preferred_soc_max"] = 0.80
    config["soft_soc"]["soc_min_penalty_g_per_kwh"] = soft_soc
    config["soft_soc"]["soc_max_penalty_g_per_kwh"] = soft_soc
    config["soft_soc"]["soft_soc_penalty_scaling"] = "mean"

    for generator in config["generators"]:
        generator["startup_cost"] = startup
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


def generator_run_lengths(run_dir: Path) -> list[int]:
    by_generator: dict[str, list[tuple[int, int]]] = {}
    with open(run_dir / "dispatch_results.csv", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            by_generator.setdefault(row["generator"], []).append(
                (int(row["timestep"]), 1 if float(row["u"]) > 0.5 else 0)
            )

    lengths: list[int] = []
    for rows in by_generator.values():
        run_length = 0
        for _, is_on in sorted(rows):
            if is_on:
                run_length += 1
            elif run_length:
                lengths.append(run_length)
                run_length = 0
        if run_length:
            lengths.append(run_length)
    return lengths


def summary_row(case: dict[str, object], config_path: Path, metadata: dict, run_dir: Path, wall_clock_s: float) -> dict[str, object]:
    rolling = metadata["kpis"]["rolling_horizon"]
    full = metadata["kpis"]["full_horizon_benchmark"]
    comparison = metadata["kpis"]["comparison"]
    lengths = generator_run_lengths(run_dir)
    return {
        "case_id": case["case_id"],
        "horizon_steps": case["horizon"],
        "horizon_hours": float(case["horizon"]) * metadata["rolling_horizon"]["dt_h"],
        "startup_cost_g_per_start": case["startup"],
        "soft_soc_penalty_g_per_kwh": case["soft_soc"],
        "min_up_time_steps": metadata["rolling_horizon"]["min_up_time_steps"],
        "min_up_time_hours": metadata["rolling_horizon"]["min_up_time_steps"] * metadata["rolling_horizon"]["dt_h"],
        "rolling_fuel_kg": rolling["total_fuel_kg"],
        "fuel_delta_vs_full_pct": comparison["fuel_delta_pct"],
        "fuel_delta_vs_full_kg": comparison["fuel_delta_g"] / 1000.0,
        "full_fuel_kg": full["total_fuel_kg"],
        "rolling_starts": rolling["generator_starts"],
        "full_starts": full["generator_starts"],
        "starts_delta_vs_full": comparison["generator_starts_delta"],
        "minimum_soc_pct": rolling["minimum_soc_pct"],
        "maximum_soc_pct": rolling["maximum_soc_pct"],
        "final_soc_pct": rolling["final_soc_pct"],
        "realized_soc_min_slack_kwh": rolling["realized_total_soc_min_slack_kwh"],
        "local_soc_min_slack_kwh": rolling["local_total_soc_min_slack_kwh"],
        "local_soc_min_slack_max_kwh": rolling["local_maximum_soc_min_slack_kwh"],
        "run_count": len(lengths),
        "run_lengths_steps": " ".join(str(value) for value in lengths),
        "shorter_than_min_up_runs": sum(value < metadata["rolling_horizon"]["min_up_time_steps"] for value in lengths),
        "minimum_length_runs": sum(value == metadata["rolling_horizon"]["min_up_time_steps"] for value in lengths),
        "median_solve_s": rolling["median_solve_time_s"],
        "p95_solve_s": rolling["p95_solve_time_s"],
        "max_solve_s": rolling["maximum_solve_time_s"],
        "nonoptimal_solves": rolling["nonoptimal_timeout_or_infeasible_solves"],
        "wall_clock_s": wall_clock_s,
        "config_path": str(config_path),
        "run_dir": str(run_dir),
    }


def write_markdown(path: Path, rows: list[dict[str, object]]) -> None:
    ranked = sorted(
        rows,
        key=lambda row: (
            float(row["fuel_delta_vs_full_pct"]),
            int(float(row["rolling_starts"])),
            float(row["final_soc_pct"]),
        ),
    )
    lines = [
        "# Minimum Up-Time Baseline Contenders",
        "",
        "Operational 15-minute average profile, moving-average forecast, mean soft-SOC penalty, and 6-step minimum up-time.",
        "",
        "| Rank | Case | H | Startup | SOC penalty | Fuel kg | Delta % | Starts | Min SOC % | Final SOC % | Runs | Run lengths | P95 solve s |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    for idx, row in enumerate(ranked, start=1):
        lines.append(
            "| "
            f"{idx} | {row['case_id']} | {int(float(row['horizon_steps']))} | "
            f"{float(row['startup_cost_g_per_start']):.0f} | {float(row['soft_soc_penalty_g_per_kwh']):.0f} | "
            f"{float(row['rolling_fuel_kg']):.3f} | {float(row['fuel_delta_vs_full_pct']):.2f} | "
            f"{int(float(row['rolling_starts']))} | {float(row['minimum_soc_pct']):.2f} | "
            f"{float(row['final_soc_pct']):.2f} | {int(float(row['run_count']))} | "
            f"`{row['run_lengths_steps']}` | {float(row['p95_solve_s']):.3f} |"
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

    for case in CASES:
        case_id = str(case["case_id"])
        if case_id in completed:
            print(f"Skipping existing {case_id}", flush=True)
            continue
        print(f"Running {case_id}", flush=True)
        config = contender_config(base_config, case)
        config_path = GENERATED_CONFIG_DIR / f"{case_id}.toml"
        write_rolling_config(config, config_path)
        metadata, run_dir, wall_clock_s = run_case(config_path)
        row = summary_row(case, config_path, metadata, run_dir, wall_clock_s)
        rows.append(row)
        write_csv(summary_path, rows)
        write_markdown(OUTPUT_DIR / "summary.md", rows)
        print(
            f"  fuel={float(row['rolling_fuel_kg']):.3f} kg, "
            f"delta={float(row['fuel_delta_vs_full_pct']):.2f}%, "
            f"starts={int(float(row['rolling_starts']))}, "
            f"min SOC={float(row['minimum_soc_pct']):.2f}%, "
            f"final SOC={float(row['final_soc_pct']):.2f}%, "
            f"runs={row['run_lengths_steps']}, "
            f"run={run_dir}",
            flush=True,
        )

    rows = sorted(
        rows,
        key=lambda row: (
            int(float(row["horizon_steps"])),
            float(row["startup_cost_g_per_start"]),
            float(row["soft_soc_penalty_g_per_kwh"]),
        ),
    )
    write_csv(summary_path, rows)
    write_markdown(OUTPUT_DIR / "summary.md", rows)
    print(f"Saved {summary_path}", flush=True)
    print(f"Saved {OUTPUT_DIR / 'summary.md'}", flush=True)


if __name__ == "__main__":
    main()
