from __future__ import annotations

import csv
import subprocess
import time
import tomllib
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SENSITIVITY_OUTPUT_ROOT = REPO_ROOT / "analysis" / "output" / "sensitivity"
NO_TERMINAL_SENSITIVITY_OUTPUT_ROOT = REPO_ROOT / "analysis" / "output" / "sensitivity_no_terminal_soc"


def resolve_repo_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else (REPO_ROOT / path).resolve()


def format_toml_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".") if value % 1 else f"{value:.1f}"
    raise TypeError(f"Unsupported TOML scalar type: {type(value)!r}")


def format_toml_array(values: list[object]) -> str:
    return "[" + ", ".join(format_toml_scalar(value) for value in values) + "]"


def sensitivity_output_root_name(config: dict) -> str:
    entry_point = Path(str(config.get("run", {}).get("entry_point", "main.jl"))).name
    return "sensitivity_no_terminal_soc" if entry_point == "main_baseline_no_terminal_soc.jl" else "sensitivity"


def sensitivity_output_root(config: dict) -> Path:
    configured_output_root = config.get("run", {}).get("output_root")
    if configured_output_root:
        output_root = resolve_repo_path(str(configured_output_root))
        if not output_root.is_relative_to(REPO_ROOT):
            raise ValueError(f"Configured output_root must be inside the repository: {output_root}")
        return output_root
    root_name = sensitivity_output_root_name(config)
    return NO_TERMINAL_SENSITIVITY_OUTPUT_ROOT if root_name == "sensitivity_no_terminal_soc" else SENSITIVITY_OUTPUT_ROOT


def write_config(config: dict, path: Path) -> None:
    lines: list[str] = []

    run = config["run"]
    scheduling = config["scheduling"]
    load_profile = config["load_profile"]
    battery = config["battery"]
    initial_conditions = config["initial_conditions"]
    terminal_conditions = config.get("terminal_conditions", {})
    generators = config["generators"]

    lines.extend(
        [
            "[run]",
            f"label = {format_toml_scalar(run['label'])}",
            f"description = {format_toml_scalar(run['description'])}",
            f"show_solver_log = {format_toml_scalar(run['show_solver_log'])}",
            *(
                [f"entry_point = {format_toml_scalar(run['entry_point'])}"]
                if "entry_point" in run
                else []
            ),
            *(
                [f"output_root = {format_toml_scalar(run['output_root'])}"]
                if "output_root" in run
                else []
            ),
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
            *(
                [
                    "[terminal_conditions]",
                    f"battery_energy_min_kwh = {format_toml_scalar(terminal_conditions['battery_energy_min_kwh'])}",
                    "",
                ]
                if "battery_energy_min_kwh" in terminal_conditions
                else []
            ),
        ]
    )

    for generator in generators:
        lines.extend(
            [
                "[[generators]]",
                f"P_max = {format_toml_scalar(generator['P_max'])}",
                f"P_min = {format_toml_scalar(generator['P_min'])}",
                f"P = {format_toml_array(generator['P'])}",
                f"SFOC = {format_toml_array(generator['SFOC'])}",
                f"startup_cost = {format_toml_scalar(generator['startup_cost'])}",
                "",
            ]
        )

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def load_dispatch_rows(run_dir: Path) -> list[dict[str, str]]:
    with open(run_dir / "dispatch_results.csv", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_run_metadata(run_dir: Path) -> dict:
    with open(run_dir / "params.toml", "rb") as fh:
        return tomllib.load(fh)


def run_case(config_path: Path) -> tuple[dict, Path, float]:
    rel_config = config_path.relative_to(REPO_ROOT)
    with open(config_path, "rb") as fh:
        case_config = tomllib.load(fh)
    entry_point = resolve_repo_path(str(case_config.get("run", {}).get("entry_point", "main.jl")))
    if not entry_point.is_relative_to(REPO_ROOT):
        raise ValueError(f"Entry point must be inside the repository: {entry_point}")
    rel_entry_point = entry_point.relative_to(REPO_ROOT)
    started_at = time.perf_counter()
    completed = subprocess.run(
        ["julia", "--project=.", str(rel_entry_point), str(rel_config)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    wall_clock_runtime_s = time.perf_counter() - started_at
    current_run = Path((REPO_ROOT / ".current_run").read_text(encoding="utf-8").strip())
    metadata = load_run_metadata(current_run)
    if str(metadata["solver"]["status"]) != "OPTIMAL":
        raise RuntimeError(
            f"Case {rel_config} did not solve to OPTIMAL.\n{completed.stdout}\n{completed.stderr}"
        )
    return metadata, current_run, wall_clock_runtime_s


def clone_case_config(base_config: dict, label_suffix: str, description_suffix: str) -> dict:
    case_config = deepcopy(base_config)
    case_config["run"]["label"] = f"{base_config['run']['label']}_{label_suffix}"
    case_config["run"]["description"] = f"{base_config['run']['description']} | {description_suffix}"
    case_config["run"]["show_solver_log"] = False
    return case_config


def create_output_dirs(sweep_name: str, output_root: Path | None = None) -> tuple[Path, Path]:
    root = SENSITIVITY_OUTPUT_ROOT if output_root is None else output_root
    output_dir = root / sweep_name
    generated_configs_dir = output_dir / "generated_configs"
    generated_configs_dir.mkdir(parents=True, exist_ok=True)
    return output_dir, generated_configs_dir


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
                "online_units": 0.0,
            },
        )
        timestep_rows[timestep]["fuel_gph"] += float(row["fuel_gph"])
        timestep_rows[timestep]["online_units"] += float(row["u"])

    rows_by_generator: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        rows_by_generator.setdefault(row["generator"], []).append(row)

    for generator, generator_rows in rows_by_generator.items():
        generator_rows.sort(key=lambda item: int(item["timestep"]))
        starts_by_generator[generator] = sum(int(item["startup"]) for item in generator_rows)

        u_values = [int(item["u"]) for item in generator_rows]
        stops = 0
        for previous, current in zip(u_values[:-1], u_values[1:]):
            if previous == 1 and current == 0:
                stops += 1
        stops_by_generator[generator] = stops

    ordered_timesteps = [timestep_rows[idx] for idx in sorted(timestep_rows)]
    horizon_h = len(ordered_timesteps) * dt
    total_fuel_kg = sum(row["fuel_gph"] for row in ordered_timesteps) * dt / 1000.0
    min_soc_pct = min(row["soc_pct"] for row in ordered_timesteps)
    final_soc_pct = ordered_timesteps[-1]["soc_pct"]
    battery_throughput_kwh = sum((row["P_ch_kw"] + row["P_dis_kw"]) * dt for row in ordered_timesteps)
    total_online_genset_hours = sum(row["online_units"] for row in ordered_timesteps) * dt
    time_two_gensets_online_h = sum(1 for row in ordered_timesteps if row["online_units"] >= 1.5) * dt
    share_two_gensets_online_pct = (time_two_gensets_online_h / horizon_h * 100.0) if horizon_h > 0.0 else 0.0

    final_row = ordered_timesteps[-1]
    terminal_e_kwh = final_row["E_kwh"] + dt * (
        eta_ch * final_row["P_ch_kw"] - (1.0 / eta_dis) * final_row["P_dis_kw"]
    )
    terminal_soc_pct = terminal_e_kwh / e_cap * 100.0

    return {
        "horizon_h": horizon_h,
        "total_fuel_kg": total_fuel_kg,
        "total_starts": sum(starts_by_generator.values()),
        "total_stops": sum(stops_by_generator.values()),
        "time_two_gensets_online_h": time_two_gensets_online_h,
        "share_two_gensets_online_pct": share_two_gensets_online_pct,
        "total_online_genset_hours": total_online_genset_hours,
        "min_soc_pct": min_soc_pct,
        "final_soc_pct": final_soc_pct,
        "terminal_soc_pct": terminal_soc_pct,
        "terminal_e_kwh": terminal_e_kwh,
        "battery_throughput_kwh": battery_throughput_kwh,
        **{f"gen_{generator}_starts": count for generator, count in starts_by_generator.items()},
        **{f"gen_{generator}_stops": count for generator, count in stops_by_generator.items()},
    }


def write_csv(rows: list[dict[str, object]], fieldnames: list[str], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def repo_relative_str(path: str | Path) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        return candidate.as_posix()
    try:
        return candidate.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return candidate.as_posix()


def format_markdown_value(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if abs(value) >= 100:
            return f"{value:.1f}".rstrip("0").rstrip(".")
        if abs(value) >= 10:
            return f"{value:.2f}".rstrip("0").rstrip(".")
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def infer_case_warning(
    *,
    terminal_soc_pct: float | None,
    terminal_reference_soc_pct: float | None,
    min_soc_pct: float | None,
    configured_soc_min_pct: float | None,
    solve_time_s: float | None,
) -> str:
    warnings: list[str] = []
    if (
        terminal_soc_pct is not None
        and terminal_reference_soc_pct is not None
        and terminal_soc_pct + 1e-6 < terminal_reference_soc_pct
    ):
        warnings.append(
            f"ends {terminal_reference_soc_pct - terminal_soc_pct:.1f} pp below the old terminal reserve"
        )
    if (
        min_soc_pct is not None
        and configured_soc_min_pct is not None
        and abs(min_soc_pct - configured_soc_min_pct) <= 0.05
    ):
        warnings.append("hits the configured minimum SOC")
    if solve_time_s is not None and solve_time_s >= 10.0:
        warnings.append("longer solve time")
    return "; ".join(warnings) if warnings else "none obvious"


def write_markdown_summary(
    path: Path,
    *,
    title: str,
    intro_lines: list[str],
    columns: list[tuple[str, str | Callable[[dict[str, object]], object]]],
    rows: list[dict[str, object]],
) -> None:
    lines = [f"# {title}", ""]
    lines.extend(intro_lines)
    if intro_lines and intro_lines[-1] != "":
        lines.append("")

    headers = [header for header, _ in columns]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")

    for row in rows:
        values: list[str] = []
        for _, accessor in columns:
            value = accessor(row) if callable(accessor) else row.get(accessor)
            values.append(format_markdown_value(value))
        lines.append("| " + " | ".join(values) + " |")

    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
