from __future__ import annotations

import argparse
import csv
import subprocess
import time
import tomllib
from copy import deepcopy
from pathlib import Path

from sensitivity_common import REPO_ROOT, format_toml_array, format_toml_scalar


BASE_CONFIG = REPO_ROOT / "config" / "rolling_horizon_oracle_operational.toml"
OUTPUT_DIR = REPO_ROOT / "analysis" / "output" / "rolling_horizon" / "oracle_operational_tuning_screen"
GENERATED_CONFIG_DIR = OUTPUT_DIR / "generated_configs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a coarse oracle rolling-horizon tuning screen on the operational profile."
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=None,
        help="Optional cap for continuing a long screen in batches.",
    )
    return parser.parse_args()


def write_rolling_config(config: dict, path: Path) -> None:
    lines: list[str] = []

    run = config["run"]
    scheduling = config["scheduling"]
    load_profile = config["load_profile"]
    battery = config["battery"]
    initial_conditions = config["initial_conditions"]
    rolling = config["rolling_horizon"]
    solver = config.get("solver", {})
    soft_soc = config.get("soft_soc")

    lines.extend(
        [
            "[run]",
            f"label = {format_toml_scalar(run['label'])}",
            f"description = {format_toml_scalar(run['description'])}",
            f"show_solver_log = {format_toml_scalar(run.get('show_solver_log', False))}",
            f"entry_point = {format_toml_scalar(run.get('entry_point', 'main_rolling_horizon.jl'))}",
            f"benchmark_entry_point = {format_toml_scalar(run.get('benchmark_entry_point', 'main_baseline.jl'))}",
            "",
            "[scheduling]",
            f"dt_minutes = {format_toml_scalar(scheduling['dt_minutes'])}",
            "",
            "[load_profile]",
            f"path = {format_toml_scalar(load_profile['path'])}",
            "",
            "[battery]",
            f"E_max = {format_toml_scalar(battery['E_max'])}",
            f"SOC_min = {format_toml_scalar(battery['SOC_min'])}",
            f"SOC_max = {format_toml_scalar(battery['SOC_max'])}",
            f"P_ch_max = {format_toml_scalar(battery['P_ch_max'])}",
            f"P_dis_max = {format_toml_scalar(battery['P_dis_max'])}",
            f"eta_ch = {format_toml_scalar(battery['eta_ch'])}",
            f"eta_dis = {format_toml_scalar(battery['eta_dis'])}",
            "",
            "[initial_conditions]",
            f"generator_commitment = {format_toml_array(initial_conditions['generator_commitment'])}",
            f"battery_energy_kwh = {format_toml_scalar(initial_conditions['battery_energy_kwh'])}",
            "",
            "[rolling_horizon]",
            f"horizon_steps = {format_toml_scalar(rolling['horizon_steps'])}",
            f"forecast_method = {format_toml_scalar(rolling['forecast_method'])}",
            f"moving_average_window_steps = {format_toml_scalar(rolling.get('moving_average_window_steps', 4))}",
            f"soc_strategy = {format_toml_scalar(rolling['soc_strategy'])}",
        ]
    )
    if rolling["soc_strategy"] == "terminal_reserve":
        lines.extend(
            [
                f"terminal_soc_target = {format_toml_scalar(rolling['terminal_soc_target'])}",
                f"terminal_slack_penalty_g_per_kwh = {format_toml_scalar(rolling['terminal_slack_penalty_g_per_kwh'])}",
            ]
        )
    lines.extend(
        [
            f"tail_forecast_policy = {format_toml_scalar(rolling.get('tail_forecast_policy', 'repeat_final_load'))}",
            f"min_up_time_steps = {format_toml_scalar(rolling.get('min_up_time_steps', 1))}",
            f"soft_band_terminal_reserve_enabled = {format_toml_scalar(rolling.get('soft_band_terminal_reserve_enabled', False))}",
            "",
            "[solver]",
            f"rolling_local_time_limit_sec = {format_toml_scalar(solver.get('rolling_local_time_limit_sec', 30.0))}",
            f"progress_log_enabled = {format_toml_scalar(solver.get('progress_log_enabled', False))}",
            f"progress_log_every_steps = {format_toml_scalar(solver.get('progress_log_every_steps', 25))}",
            f"slow_solve_log_threshold_sec = {format_toml_scalar(solver.get('slow_solve_log_threshold_sec', 999.0))}",
            "",
        ]
    )

    if rolling["soc_strategy"] == "soft_band":
        if soft_soc is None:
            raise ValueError("soft_band case requires [soft_soc].")
        lines.extend(
            [
                "[soft_soc]",
                f"preferred_soc_min = {format_toml_scalar(soft_soc['preferred_soc_min'])}",
                f"preferred_soc_max = {format_toml_scalar(soft_soc['preferred_soc_max'])}",
                f"soc_min_penalty_g_per_kwh = {format_toml_scalar(soft_soc['soc_min_penalty_g_per_kwh'])}",
                f"soc_max_penalty_g_per_kwh = {format_toml_scalar(soft_soc['soc_max_penalty_g_per_kwh'])}",
                f"soft_soc_penalty_scaling = {format_toml_scalar(soft_soc.get('soft_soc_penalty_scaling', 'sum'))}",
                "",
            ]
        )

    for generator in config["generators"]:
        lines.extend(
            [
                "[[generators]]",
                f"P_max = {format_toml_scalar(generator['P_max'])}",
                f"P_min = {format_toml_scalar(generator['P_min'])}",
                f"P = {format_toml_array(generator['P'])}",
                f"SFOC = {format_toml_array(generator['SFOC'])}",
                f"startup_cost = {format_toml_scalar(generator['startup_cost'])}",
                f"shutdown_cost = {format_toml_scalar(generator.get('shutdown_cost', 0.0))}",
                "",
            ]
        )

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def load_existing_summary(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_summary(rows: list[dict[str, object]], path: Path) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def case_config(base: dict, *, case_id: str, description: str, horizon: int, strategy: str,
                startup_cost: float, soft_min: float = 0.20, soft_penalty: float = 1000.0,
                terminal_target: float = 0.20, terminal_penalty: float = 1000.0) -> dict:
    config = deepcopy(base)
    config["run"]["label"] = f"oracle_operational_screen_{case_id}"
    config["run"]["description"] = f"{base['run']['description']} | {description}"
    config["run"]["show_solver_log"] = False
    config["rolling_horizon"]["horizon_steps"] = horizon
    config["rolling_horizon"]["forecast_method"] = "oracle_realized_local_load"
    config["rolling_horizon"]["soc_strategy"] = strategy
    config.setdefault("solver", {})
    config["solver"]["progress_log_enabled"] = False
    config["solver"]["slow_solve_log_threshold_sec"] = 999.0

    for generator in config["generators"]:
        generator["startup_cost"] = float(startup_cost)

    if strategy == "soft_band":
        config["rolling_horizon"].pop("terminal_soc_target", None)
        config["rolling_horizon"].pop("terminal_slack_penalty_g_per_kwh", None)
        config["soft_soc"] = {
            "preferred_soc_min": float(soft_min),
            "preferred_soc_max": 0.80,
            "soc_min_penalty_g_per_kwh": float(soft_penalty),
            "soc_max_penalty_g_per_kwh": float(soft_penalty),
        }
    elif strategy == "terminal_reserve":
        config.pop("soft_soc", None)
        config["rolling_horizon"]["terminal_soc_target"] = float(terminal_target)
        config["rolling_horizon"]["terminal_slack_penalty_g_per_kwh"] = float(terminal_penalty)
    else:
        raise ValueError(f"Unsupported strategy: {strategy}")

    return config


def case_specs() -> list[dict[str, object]]:
    specs: list[dict[str, object]] = [
        {
            "case_id": "soft_h24_soc20_p1000_c1000",
            "description": "baseline soft SOC, H=24, preferred min 20%, penalty 1000, startup 1000",
            "horizon": 24,
            "strategy": "soft_band",
            "startup_cost": 1000.0,
            "soft_min": 0.20,
            "soft_penalty": 1000.0,
        },
        {
            "case_id": "soft_h48_soc20_p1000_c1000",
            "description": "longer horizon screen, H=48",
            "horizon": 48,
            "strategy": "soft_band",
            "startup_cost": 1000.0,
            "soft_min": 0.20,
            "soft_penalty": 1000.0,
        },
        {
            "case_id": "soft_h72_soc20_p1000_c1000",
            "description": "longer horizon screen, H=72",
            "horizon": 72,
            "strategy": "soft_band",
            "startup_cost": 1000.0,
            "soft_min": 0.20,
            "soft_penalty": 1000.0,
        },
        {
            "case_id": "soft_h24_soc30_p1000_c1000",
            "description": "higher preferred SOC minimum, 30%",
            "horizon": 24,
            "strategy": "soft_band",
            "startup_cost": 1000.0,
            "soft_min": 0.30,
            "soft_penalty": 1000.0,
        },
        {
            "case_id": "soft_h24_soc40_p1000_c1000",
            "description": "higher preferred SOC minimum, 40%",
            "horizon": 24,
            "strategy": "soft_band",
            "startup_cost": 1000.0,
            "soft_min": 0.40,
            "soft_penalty": 1000.0,
        },
        {
            "case_id": "soft_h24_soc20_p1000_c2500",
            "description": "higher startup penalty, 2500 g/start",
            "horizon": 24,
            "strategy": "soft_band",
            "startup_cost": 2500.0,
            "soft_min": 0.20,
            "soft_penalty": 1000.0,
        },
        {
            "case_id": "soft_h24_soc20_p1000_c5000",
            "description": "higher startup penalty, 5000 g/start",
            "horizon": 24,
            "strategy": "soft_band",
            "startup_cost": 5000.0,
            "soft_min": 0.20,
            "soft_penalty": 1000.0,
        },
        {
            "case_id": "soft_h24_soc20_p350_c1000",
            "description": "lower soft SOC slack penalty, 350 g/kWh",
            "horizon": 24,
            "strategy": "soft_band",
            "startup_cost": 1000.0,
            "soft_min": 0.20,
            "soft_penalty": 350.0,
        },
        {
            "case_id": "soft_h24_soc20_p1500_c1000",
            "description": "higher soft SOC slack penalty, 1500 g/kWh",
            "horizon": 24,
            "strategy": "soft_band",
            "startup_cost": 1000.0,
            "soft_min": 0.20,
            "soft_penalty": 1500.0,
        },
        {
            "case_id": "term_h24_t20_p350_c1000",
            "description": "terminal reserve, target 20%, slack penalty 350",
            "horizon": 24,
            "strategy": "terminal_reserve",
            "startup_cost": 1000.0,
            "terminal_target": 0.20,
            "terminal_penalty": 350.0,
        },
        {
            "case_id": "term_h24_t20_p1000_c1000",
            "description": "terminal reserve, target 20%, slack penalty 1000",
            "horizon": 24,
            "strategy": "terminal_reserve",
            "startup_cost": 1000.0,
            "terminal_target": 0.20,
            "terminal_penalty": 1000.0,
        },
        {
            "case_id": "term_h24_t30_p350_c1000",
            "description": "terminal reserve, target 30%, slack penalty 350",
            "horizon": 24,
            "strategy": "terminal_reserve",
            "startup_cost": 1000.0,
            "terminal_target": 0.30,
            "terminal_penalty": 350.0,
        },
        {
            "case_id": "term_h24_t30_p1000_c1000",
            "description": "terminal reserve, target 30%, slack penalty 1000",
            "horizon": 24,
            "strategy": "terminal_reserve",
            "startup_cost": 1000.0,
            "terminal_target": 0.30,
            "terminal_penalty": 1000.0,
        },
    ]
    return specs


def run_case(config_path: Path) -> tuple[dict, Path, float]:
    started_at = time.perf_counter()
    completed = subprocess.run(
        ["julia", "--project=.", "main_rolling_horizon.jl", str(config_path.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
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


def summary_row(spec: dict[str, object], config_path: Path, metadata: dict, run_dir: Path, wall_clock_s: float) -> dict[str, object]:
    rolling = metadata["kpis"]["rolling_horizon"]
    full = metadata["kpis"]["full_horizon_benchmark"]
    comparison = metadata["kpis"]["comparison"]
    settings = metadata["rolling_horizon"]
    strategy = str(spec["strategy"])
    row: dict[str, object] = {
        "case_id": spec["case_id"],
        "strategy": strategy,
        "horizon_steps": spec["horizon"],
        "startup_cost_g": spec["startup_cost"],
        "preferred_soc_min": spec.get("soft_min", ""),
        "soft_soc_penalty_g_per_kwh": spec.get("soft_penalty", ""),
        "terminal_soc_target": spec.get("terminal_target", ""),
        "terminal_slack_penalty_g_per_kwh": spec.get("terminal_penalty", ""),
        "rolling_fuel_kg": rolling["total_fuel_kg"],
        "rolling_starts": rolling["generator_starts"],
        "rolling_min_soc_pct": rolling["minimum_soc_pct"],
        "rolling_final_soc_pct": rolling["final_soc_pct"],
        "fuel_delta_vs_full_kg": comparison["fuel_delta_g"] / 1000.0,
        "fuel_delta_vs_full_pct": comparison["fuel_delta_pct"],
        "starts_delta_vs_full": comparison["generator_starts_delta"],
        "full_fuel_kg": full["total_fuel_kg"],
        "full_starts": full["generator_starts"],
        "median_solve_s": rolling["median_solve_time_s"],
        "p95_solve_s": rolling["p95_solve_time_s"],
        "max_solve_s": rolling["maximum_solve_time_s"],
        "nonoptimal_solves": rolling["nonoptimal_timeout_or_infeasible_solves"],
        "tail_padded_solves": settings["tail_forecast_padded_solves"],
        "wall_clock_s": wall_clock_s,
        "config_path": str(config_path),
        "run_dir": str(run_dir),
    }
    if strategy == "soft_band":
        row["realized_low_soc_slack_kwh"] = rolling["realized_total_soc_min_slack_kwh"]
        row["local_low_soc_slack_kwh"] = rolling["local_total_soc_min_slack_kwh"]
        row["terminal_slack_kwh"] = ""
    else:
        row["realized_low_soc_slack_kwh"] = ""
        row["local_low_soc_slack_kwh"] = ""
        row["terminal_slack_kwh"] = rolling["total_terminal_slack_kwh"]
    return row


def write_markdown(rows: list[dict[str, object]], path: Path) -> None:
    sorted_rows = sorted(rows, key=lambda row: (float(row["fuel_delta_vs_full_pct"]), int(float(row["rolling_starts"]))))
    lines = [
        "# Oracle Operational Rolling-Horizon Tuning Screen",
        "",
        "Coarse one-factor / small-candidate screen using oracle realized local load on the operational 15-minute average profile.",
        "",
        "| Rank | Case | Strategy | H | Fuel kg | Delta % | Starts | Final SOC % | P95 solve s | Non-opt |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for idx, row in enumerate(sorted_rows, start=1):
        lines.append(
            "| "
            f"{idx} | {row['case_id']} | {row['strategy']} | {row['horizon_steps']} | "
            f"{float(row['rolling_fuel_kg']):.3f} | {float(row['fuel_delta_vs_full_pct']):.2f} | "
            f"{int(float(row['rolling_starts']))} | {float(row['rolling_final_soc_pct']):.2f} | "
            f"{float(row['p95_solve_s']):.3f} | {int(float(row['nonoptimal_solves']))} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    with open(BASE_CONFIG, "rb") as fh:
        base_config = tomllib.load(fh)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = OUTPUT_DIR / "summary.csv"
    rows: list[dict[str, object]] = [dict(row) for row in load_existing_summary(summary_path)]
    existing = {str(row["case_id"]) for row in rows}

    completed_this_run = 0
    for spec in case_specs():
        case_id = str(spec["case_id"])
        if case_id in existing:
            print(f"Skipping existing {case_id}", flush=True)
            continue
        if args.max_cases is not None and completed_this_run >= args.max_cases:
            break

        print(f"Running {case_id}", flush=True)
        config = case_config(base_config, **spec)
        config_path = GENERATED_CONFIG_DIR / f"{case_id}.toml"
        write_rolling_config(config, config_path)
        metadata, run_dir, wall_clock_s = run_case(config_path)
        row = summary_row(spec, config_path, metadata, run_dir, wall_clock_s)
        rows.append(row)
        write_summary(rows, summary_path)
        write_markdown(rows, OUTPUT_DIR / "summary.md")
        completed_this_run += 1
        print(
            f"  fuel={float(row['rolling_fuel_kg']):.3f} kg, "
            f"delta={float(row['fuel_delta_vs_full_pct']):.2f}%, "
            f"starts={int(float(row['rolling_starts']))}, "
            f"run={run_dir}",
            flush=True,
        )

    write_summary(rows, summary_path)
    write_markdown(rows, OUTPUT_DIR / "summary.md")
    print(f"Saved {summary_path}")
    print(f"Saved {OUTPUT_DIR / 'summary.md'}")


if __name__ == "__main__":
    main()
