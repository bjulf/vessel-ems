from __future__ import annotations

import argparse
import csv
import statistics
import subprocess
import time
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "analysis" / "output" / "timing"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repeat a model run and summarize solver/wall-clock timing."
    )
    parser.add_argument(
        "config",
        nargs="?",
        default="config/baseline_model.toml",
        help="Config path relative to repo root or absolute path.",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=5,
        help="Number of timed repeats to record.",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=1,
        help="Number of untimed warmup runs before timed repeats.",
    )
    return parser.parse_args()


def resolve_repo_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else (REPO_ROOT / path).resolve()


def load_run_metadata(run_dir: Path) -> dict:
    with open(run_dir / "params.toml", "rb") as fh:
        return tomllib.load(fh)


def load_dispatch_rows(run_dir: Path) -> list[dict[str, str]]:
    with open(run_dir / "dispatch_results.csv", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def slugify(text: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in text)


def run_case(config_path: Path) -> tuple[float, dict, Path]:
    rel_config = config_path.relative_to(REPO_ROOT)
    command = ["julia", "--project=.", "main.jl", str(rel_config)]
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    wall_clock_s = time.perf_counter() - started
    current_run = Path((REPO_ROOT / ".current_run").read_text(encoding="utf-8").strip())
    metadata = load_run_metadata(current_run)
    return wall_clock_s, metadata, current_run


def compute_run_metrics(run_dir: Path, metadata: dict) -> dict[str, float | int]:
    rows = load_dispatch_rows(run_dir)
    if not rows:
        raise RuntimeError(f"Run {run_dir} has an empty dispatch_results.csv")

    battery = metadata["battery"]
    dt = float(battery["dt"])
    eta_ch = float(battery["eta_ch"])
    eta_dis = float(battery["eta_dis"])
    e_cap = float(battery["E_cap"])

    timestep_rows: dict[int, dict[str, float]] = {}
    starts_by_generator: dict[str, int] = {}
    stops_by_generator: dict[str, int] = {}

    for row in rows:
        timestep = int(row["timestep"])
        timestep_rows.setdefault(
            timestep,
            {
                "fuel_gph": 0.0,
                "soc_pct": float(row["soc_pct"]),
                "E_kwh": float(row["E_kwh"]),
                "P_ch_kw": float(row["P_ch_kw"]),
                "P_dis_kw": float(row["P_dis_kw"]),
            },
        )
        timestep_rows[timestep]["fuel_gph"] += float(row["fuel_gph"])

    rows_by_generator: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        rows_by_generator.setdefault(row["generator"], []).append(row)

    for generator, generator_rows in rows_by_generator.items():
        generator_rows.sort(key=lambda r: int(r["timestep"]))
        starts_by_generator[generator] = sum(int(row["startup"]) for row in generator_rows)

        u_values = [int(row["u"]) for row in generator_rows]
        stops = 0
        for previous, current in zip(u_values[:-1], u_values[1:]):
            if previous == 1 and current == 0:
                stops += 1
        stops_by_generator[generator] = stops

    ordered_timesteps = [timestep_rows[idx] for idx in sorted(timestep_rows)]
    total_fuel_kg = sum(row["fuel_gph"] for row in ordered_timesteps) * dt / 1000.0
    min_soc_pct = min(row["soc_pct"] for row in ordered_timesteps)
    final_soc_pct = ordered_timesteps[-1]["soc_pct"]

    final_row = ordered_timesteps[-1]
    terminal_e_kwh = final_row["E_kwh"] + dt * (
        eta_ch * final_row["P_ch_kw"] - (1.0 / eta_dis) * final_row["P_dis_kw"]
    )
    terminal_soc_pct = terminal_e_kwh / e_cap * 100.0

    simultaneous_charge_discharge_steps = sum(
        int(row["P_ch_kw"] > 1e-9 and row["P_dis_kw"] > 1e-9) for row in ordered_timesteps
    )

    return {
        "total_fuel_kg": total_fuel_kg,
        "min_soc_pct": min_soc_pct,
        "final_soc_pct": final_soc_pct,
        "terminal_soc_pct": terminal_soc_pct,
        "terminal_e_kwh": terminal_e_kwh,
        "total_starts": sum(starts_by_generator.values()),
        "total_stops": sum(stops_by_generator.values()),
        "simultaneous_charge_discharge_steps": simultaneous_charge_discharge_steps,
        **{f"gen_{generator}_starts": count for generator, count in starts_by_generator.items()},
        **{f"gen_{generator}_stops": count for generator, count in stops_by_generator.items()},
    }


def summarize(values: list[float]) -> dict[str, float]:
    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def extract_validation_summary(metadata: dict) -> dict[str, float | bool] | None:
    validation = metadata.get("validation")
    if not validation:
        return None

    tolerances = validation["solver_tolerances"]
    power = validation["power_balance"]
    battery = validation["battery_energy"]
    return {
        "primal_feasibility_tolerance": float(tolerances["primal_feasibility"]),
        "power_balance_max_abs_residual_kw": float(power["max_abs_residual_kw"]),
        "power_balance_within_tolerance": bool(power["within_primal_feasibility_tolerance"]),
        "battery_energy_max_abs_dynamic_residual_kwh": float(
            battery["max_abs_dynamic_residual_kwh"]
        ),
        "battery_energy_initial_residual_kwh": float(battery["initial_residual_kwh"]),
        "battery_energy_within_tolerance": bool(battery["within_primal_feasibility_tolerance"]),
    }


def write_outputs(config_path: Path, rows: list[dict[str, object]], summary: dict[str, object]) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = slugify(config_path.stem)
    csv_path = OUTPUT_DIR / f"{stem}_timing_runs.csv"
    summary_path = OUTPUT_DIR / f"{stem}_timing_summary.txt"

    fieldnames = [
        "phase",
        "run_index",
        "run_dir",
        "objective_g",
        "solver_time_s",
        "wall_clock_s",
        "solve_status",
        "e_init_kwh",
        "timesteps",
        "dt_minutes",
        "total_fuel_kg",
        "min_soc_pct",
        "final_soc_pct",
        "terminal_soc_pct",
        "terminal_e_kwh",
        "total_starts",
        "total_stops",
        "simultaneous_charge_discharge_steps",
        "gen_1_starts",
        "gen_1_stops",
        "gen_2_starts",
        "gen_2_stops",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        f"Timing summary for {config_path}",
        "",
        f"Timed repeats: {summary['timed_repeats']}",
        f"Warmup runs: {summary['warmup_runs']}",
        f"Run label: {summary['run_label']}",
        f"Load profile: {summary['load_profile']}",
        f"Timesteps: {summary['timesteps']}",
        f"Timestep length: {summary['dt_minutes']} min",
        f"Initial battery energy: {summary['e_init_kwh']:.1f} kWh",
        "",
        "Solver time [s]:",
        (
            f"  median={summary['solver']['median']:.3f}, mean={summary['solver']['mean']:.3f}, "
            f"min={summary['solver']['min']:.3f}, max={summary['solver']['max']:.3f}, "
            f"stdev={summary['solver']['stdev']:.3f}"
        ),
        "Wall-clock time [s]:",
        (
            f"  median={summary['wall']['median']:.3f}, mean={summary['wall']['mean']:.3f}, "
            f"min={summary['wall']['min']:.3f}, max={summary['wall']['max']:.3f}, "
            f"stdev={summary['wall']['stdev']:.3f}"
        ),
        "",
        f"Objective value [g fuel]: {summary['objective_g']:.3f}",
        f"Total fuel [kg]: {summary['total_fuel_kg']:.3f}",
        f"Min SOC [%]: {summary['min_soc_pct']:.3f}",
        f"Final exported SOC [%]: {summary['final_soc_pct']:.3f}",
        f"Terminal SOC [%]: {summary['terminal_soc_pct']:.3f}",
        f"Total starts: {summary['total_starts']}",
        f"Total stops: {summary['total_stops']}",
        f"Simultaneous charge/discharge steps: {summary['simultaneous_charge_discharge_steps']}",
        f"Status: {summary['status']}",
    ]
    validation = summary.get("validation")
    if validation:
        lines.extend(
            [
                "",
                "Constraint residual checks:",
                f"  Primal feasibility tolerance: {validation['primal_feasibility_tolerance']:.1e}",
                (
                    "  Max power balance residual [kW]: "
                    f"{validation['power_balance_max_abs_residual_kw']:.3e} "
                    f"(within tolerance: {validation['power_balance_within_tolerance']})"
                ),
                (
                    "  Max battery energy dynamic residual [kWh]: "
                    f"{validation['battery_energy_max_abs_dynamic_residual_kwh']:.3e} "
                    f"(within tolerance: {validation['battery_energy_within_tolerance']})"
                ),
                (
                    "  Initial battery energy residual [kWh]: "
                    f"{validation['battery_energy_initial_residual_kwh']:.3e}"
                ),
            ]
        )
    lines.extend(
        [
            "",
            "Stability across timed repeats:",
            f"  objective constant: {summary['objective_constant']}",
            f"  total fuel constant: {summary['total_fuel_constant']}",
            f"  terminal SOC constant: {summary['terminal_soc_constant']}",
            f"  starts constant: {summary['starts_constant']}",
            "",
            f"CSV: {csv_path}",
        ]
    )
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return csv_path, summary_path


def main() -> None:
    args = parse_args()
    config_path = resolve_repo_path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config file: {config_path}")
    if not config_path.is_relative_to(REPO_ROOT):
        raise ValueError("Config path must be inside the repository.")
    if args.repeats < 1:
        raise ValueError("--repeats must be at least 1.")
    if args.warmup < 0:
        raise ValueError("--warmup cannot be negative.")

    print(f"Config: {config_path.relative_to(REPO_ROOT)}")
    if args.warmup:
        print(f"Warmup runs: {args.warmup}")

    rows: list[dict[str, object]] = []
    solver_times: list[float] = []
    wall_times: list[float] = []
    objectives: list[float] = []
    statuses: set[str] = set()
    total_fuels: list[float] = []
    terminal_socs: list[float] = []
    total_starts_list: list[int] = []
    last_metadata: dict | None = None

    for warmup_idx in range(1, args.warmup + 1):
        if args.warmup:
            wall_clock_s, metadata, run_dir = run_case(config_path)
            metrics = compute_run_metrics(run_dir, metadata)
            rows.append(
                {
                    "phase": "warmup",
                    "run_index": warmup_idx,
                    "run_dir": str(run_dir),
                    "objective_g": float(metadata["solver"]["objective"]),
                    "solver_time_s": float(metadata["solver"]["solve_time_s"]),
                    "wall_clock_s": wall_clock_s,
                    "solve_status": str(metadata["solver"]["status"]),
                    "e_init_kwh": float(metadata["battery"]["E_init"]),
                    "timesteps": int(metadata["load_profile"]["timesteps"]),
                    "dt_minutes": int(metadata["load_profile"]["dt_minutes"]),
                    **metrics,
                }
            )
            last_metadata = metadata

    for repeat_idx in range(1, args.repeats + 1):
        print(f"Timed run {repeat_idx}/{args.repeats}...")
        wall_clock_s, metadata, run_dir = run_case(config_path)
        metrics = compute_run_metrics(run_dir, metadata)
        solver = metadata["solver"]
        battery = metadata["battery"]
        load_profile = metadata["load_profile"]

        solver_time_s = float(solver["solve_time_s"])
        objective_g = float(solver["objective"])
        status = str(solver["status"])

        rows.append(
            {
                "phase": "timed",
                "run_index": repeat_idx,
                "run_dir": str(run_dir),
                "objective_g": objective_g,
                "solver_time_s": solver_time_s,
                "wall_clock_s": wall_clock_s,
                "solve_status": status,
                "e_init_kwh": float(battery["E_init"]),
                "timesteps": int(load_profile["timesteps"]),
                "dt_minutes": int(load_profile["dt_minutes"]),
                **metrics,
            }
        )

        solver_times.append(solver_time_s)
        wall_times.append(wall_clock_s)
        objectives.append(objective_g)
        total_fuels.append(float(metrics["total_fuel_kg"]))
        terminal_socs.append(float(metrics["terminal_soc_pct"]))
        total_starts_list.append(int(metrics["total_starts"]))
        statuses.add(status)
        last_metadata = metadata

    assert last_metadata is not None
    objective_constant = len(set(round(value, 6) for value in objectives)) == 1
    total_fuel_constant = len(set(round(value, 6) for value in total_fuels)) == 1
    terminal_soc_constant = len(set(round(value, 6) for value in terminal_socs)) == 1
    starts_constant = len(set(total_starts_list)) == 1
    status_constant = len(statuses) == 1
    if not status_constant:
        raise RuntimeError(f"Solve status changed across repeated runs: {sorted(statuses)}")

    summary = {
        "timed_repeats": args.repeats,
        "warmup_runs": args.warmup,
        "run_label": last_metadata["run"]["label"],
        "load_profile": last_metadata["load_profile"]["source_file"],
        "timesteps": int(last_metadata["load_profile"]["timesteps"]),
        "dt_minutes": int(last_metadata["load_profile"]["dt_minutes"]),
        "e_init_kwh": float(last_metadata["battery"]["E_init"]),
        "solver": summarize(solver_times),
        "wall": summarize(wall_times),
        "objective_g": objectives[0],
        "total_fuel_kg": total_fuels[0],
        "min_soc_pct": rows[-1]["min_soc_pct"],
        "final_soc_pct": rows[-1]["final_soc_pct"],
        "terminal_soc_pct": rows[-1]["terminal_soc_pct"],
        "total_starts": total_starts_list[0],
        "total_stops": rows[-1]["total_stops"],
        "simultaneous_charge_discharge_steps": rows[-1]["simultaneous_charge_discharge_steps"],
        "status": next(iter(statuses)),
        "validation": extract_validation_summary(last_metadata),
        "objective_constant": objective_constant,
        "total_fuel_constant": total_fuel_constant,
        "terminal_soc_constant": terminal_soc_constant,
        "starts_constant": starts_constant,
    }

    csv_path, summary_path = write_outputs(config_path, rows, summary)
    print(f"Saved {csv_path}")
    print(f"Saved {summary_path}")
    print(
        "Median solver time = "
        f"{summary['solver']['median']:.3f} s; "
        f"median wall-clock time = {summary['wall']['median']:.3f} s"
    )


if __name__ == "__main__":
    main()
