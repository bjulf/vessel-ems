from __future__ import annotations

import argparse
import csv
import subprocess
import time
import tomllib
from copy import deepcopy
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from sensitivity_common import REPO_ROOT, format_toml_array, format_toml_scalar, resolve_repo_path


DEFAULT_CONFIG = "config/rolling_horizon_terminal_reserve_operational.toml"
DEFAULT_TERMINAL_SOC_TARGETS = [0.20, 0.30, 0.40, 0.50, 0.60]
DEFAULT_C_TERM_VALUES = [350.0, 600.0, 1000.0, 1500.0]
OUTPUT_DIR = REPO_ROOT / "analysis" / "output" / "rolling_horizon" / "operational_reserve_tuning"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run operational rolling-horizon reserve-target and terminal-slack-penalty sweeps."
    )
    parser.add_argument(
        "config",
        nargs="?",
        default=DEFAULT_CONFIG,
        help="Base rolling-horizon config path, relative to repo root or absolute.",
    )
    parser.add_argument(
        "--terminal-soc-targets",
        type=float,
        nargs="+",
        default=DEFAULT_TERMINAL_SOC_TARGETS,
        help="Terminal SOC targets as fractions, e.g. 0.40 0.50 0.60.",
    )
    parser.add_argument(
        "--c-term-values",
        type=float,
        nargs="+",
        default=DEFAULT_C_TERM_VALUES,
        help="Terminal slack penalties in g/kWh.",
    )
    parser.add_argument(
        "--skip-reference-panel",
        action="store_true",
        help="Do not regenerate full_horizon_milp_reference_panel.png.",
    )
    return parser.parse_args()


def pct_label(target: float) -> str:
    return f"{int(round(target * 100.0))}pct"


def cterm_label(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value).replace(".", "p")


def write_rolling_config(config: dict, path: Path) -> None:
    lines: list[str] = []

    run = config["run"]
    scheduling = config["scheduling"]
    load_profile = config["load_profile"]
    battery = config["battery"]
    initial_conditions = config["initial_conditions"]
    terminal_conditions = config.get("terminal_conditions", {})
    rolling = config["rolling_horizon"]
    generators = config["generators"]

    lines.extend(
        [
            "[run]",
            f"label = {format_toml_scalar(run['label'])}",
            f"description = {format_toml_scalar(run['description'])}",
            f"show_solver_log = {format_toml_scalar(run['show_solver_log'])}",
            f"entry_point = {format_toml_scalar(run.get('entry_point', 'main_rolling_horizon.jl'))}",
            *(
                [f"benchmark_entry_point = {format_toml_scalar(run['benchmark_entry_point'])}"]
                if "benchmark_entry_point" in run
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
        ]
    )

    if "battery_energy_min_kwh" in terminal_conditions:
        lines.extend(
            [
                "[terminal_conditions]",
                f"battery_energy_min_kwh = {format_toml_scalar(terminal_conditions['battery_energy_min_kwh'])}",
                "",
            ]
        )

    lines.extend(
        [
            "[rolling_horizon]",
            f"horizon_steps = {format_toml_scalar(rolling['horizon_steps'])}",
            f"forecast_method = {format_toml_scalar(rolling.get('forecast_method', 'persistence'))}",
            f"moving_average_window_steps = {format_toml_scalar(rolling.get('moving_average_window_steps', 4))}",
            f"soc_strategy = {format_toml_scalar(rolling.get('soc_strategy', 'terminal_reserve'))}",
            f"terminal_soc_target = {format_toml_scalar(rolling['terminal_soc_target'])}",
            f"terminal_slack_penalty_g_per_kwh = {format_toml_scalar(rolling['terminal_slack_penalty_g_per_kwh'])}",
            f"tail_forecast_policy = {format_toml_scalar(rolling['tail_forecast_policy'])}",
            "",
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


def build_case_config(base_config: dict, terminal_soc_target: float, c_term: float) -> dict:
    case_config = deepcopy(base_config)
    target_label = pct_label(terminal_soc_target)
    c_label = cterm_label(c_term)
    case_config["run"]["label"] = (
        f"{base_config['run']['label']}_term_{target_label}_cterm_{c_label}"
    )
    case_config["run"]["description"] = (
        f"{base_config['run']['description']} | rolling reserve sensitivity: "
        f"terminal SOC target {terminal_soc_target:.0%}, C_term {c_term:g} g/kWh"
    )
    case_config["run"]["show_solver_log"] = False
    case_config["rolling_horizon"]["terminal_soc_target"] = float(terminal_soc_target)
    case_config["rolling_horizon"]["terminal_slack_penalty_g_per_kwh"] = float(c_term)
    return case_config


def run_case(config_path: Path) -> tuple[dict, Path, float]:
    rel_config = config_path.relative_to(REPO_ROOT)
    started_at = time.perf_counter()
    completed = subprocess.run(
        ["julia", "--project=.", "main_rolling_horizon.jl", str(rel_config)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    wall_clock_runtime_s = time.perf_counter() - started_at
    current_run = Path((REPO_ROOT / ".current_run").read_text(encoding="utf-8").strip())
    with open(current_run / "params.toml", "rb") as fh:
        metadata = tomllib.load(fh)

    nonoptimal = int(
        metadata["kpis"]["rolling_horizon"]["nonoptimal_timeout_or_infeasible_solves"]
    )
    if nonoptimal != 0:
        raise RuntimeError(
            f"Case {rel_config} had {nonoptimal} non-optimal local solves.\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return metadata, current_run, wall_clock_runtime_s


def case_summary_row(
    terminal_soc_target: float,
    c_term: float,
    config_path: Path,
    run_dir: Path,
    metadata: dict,
    wall_clock_runtime_s: float,
) -> dict[str, object]:
    rolling = metadata["kpis"]["rolling_horizon"]
    full = metadata["kpis"]["full_horizon_benchmark"]
    comparison = metadata["kpis"]["comparison"]
    return {
        "terminal_soc_target": terminal_soc_target,
        "terminal_soc_target_pct": terminal_soc_target * 100.0,
        "c_term_g_per_kwh": c_term,
        "config_path": str(config_path),
        "run_dir": str(run_dir),
        "rolling_total_fuel_kg": rolling["total_fuel_kg"],
        "rolling_generator_starts": rolling["generator_starts"],
        "rolling_minimum_soc_pct": rolling["minimum_soc_pct"],
        "rolling_final_soc_pct": rolling["final_soc_pct"],
        "rolling_total_terminal_slack_kwh": rolling["total_terminal_slack_kwh"],
        "rolling_maximum_terminal_slack_kwh": rolling["maximum_terminal_slack_kwh"],
        "rolling_median_solve_time_s": rolling["median_solve_time_s"],
        "rolling_p95_solve_time_s": rolling["p95_solve_time_s"],
        "rolling_maximum_solve_time_s": rolling["maximum_solve_time_s"],
        "rolling_nonoptimal_solves": rolling["nonoptimal_timeout_or_infeasible_solves"],
        "full_horizon_total_fuel_kg": full["total_fuel_kg"],
        "full_horizon_generator_starts": full["generator_starts"],
        "full_horizon_minimum_soc_pct": full["minimum_soc_pct"],
        "full_horizon_final_soc_pct": full["final_soc_pct"],
        "fuel_delta_vs_full_kg": comparison["fuel_delta_g"] / 1000.0,
        "fuel_delta_vs_full_pct": comparison["fuel_delta_pct"],
        "generator_starts_delta_vs_full": comparison["generator_starts_delta"],
        "wall_clock_runtime_s": wall_clock_runtime_s,
    }


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_existing_rows(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def case_key(row: dict[str, object]) -> tuple[float, float]:
    return (float(row["terminal_soc_target"]), float(row["c_term_g_per_kwh"]))


def write_summary_markdown(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        "# Rolling-Horizon Operational Reserve Sensitivity",
        "",
        "Operational 15-minute average-load case. Each case uses H = 24, first-step implementation, and the same full-horizon no-terminal MILP benchmark comparison.",
        "",
        "Figures: `overview.png` shows the rolling-horizon sweep with full-horizon MILP reference lines. `full_horizon_milp_reference_panel.png` shows the full-horizon MILP dispatch trajectory used as the benchmark.",
        "",
        "## Full Grid",
        "",
        "| Terminal target [%] | C_term [g/kWh] | Fuel [kg] | Starts | Min SOC [%] | Final SOC [%] | Total slack [kWh] | P95 solve [s] |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for row in rows:
        lines.append(
            "| "
            f"{float(row['terminal_soc_target_pct']):.0f} | "
            f"{float(row['c_term_g_per_kwh']):.0f} | "
            f"{float(row['rolling_total_fuel_kg']):.3f} | "
            f"{int(row['rolling_generator_starts'])} | "
            f"{float(row['rolling_minimum_soc_pct']):.2f} | "
            f"{float(row['rolling_final_soc_pct']):.2f} | "
            f"{float(row['rolling_total_terminal_slack_kwh']):.3f} | "
            f"{float(row['rolling_p95_solve_time_s']):.3f} |"
        )

    fixed_50 = [row for row in rows if abs(float(row["terminal_soc_target"]) - 0.50) < 1e-9]
    lines.extend(
        [
            "",
            "## C_term Sweep at 50% Terminal Target",
            "",
            "| C_term [g/kWh] | Fuel [kg] | Starts | Min SOC [%] | Final SOC [%] | Total slack [kWh] |",
            "| ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in fixed_50:
        lines.append(
            "| "
            f"{float(row['c_term_g_per_kwh']):.0f} | "
            f"{float(row['rolling_total_fuel_kg']):.3f} | "
            f"{int(row['rolling_generator_starts'])} | "
            f"{float(row['rolling_minimum_soc_pct']):.2f} | "
            f"{float(row['rolling_final_soc_pct']):.2f} | "
            f"{float(row['rolling_total_terminal_slack_kwh']):.3f} |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_overview(rows: list[dict[str, object]], path: Path) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)

    grouped: dict[float, list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(float(row["terminal_soc_target"]), []).append(row)
    for target_rows in grouped.values():
        target_rows.sort(key=lambda row: float(row["c_term_g_per_kwh"]))

    panels = [
        ("rolling_total_fuel_kg", "full_horizon_total_fuel_kg", "Fuel [kg]", "Total fuel"),
        ("rolling_generator_starts", "full_horizon_generator_starts", "starts", "Generator starts"),
        ("rolling_minimum_soc_pct", "full_horizon_minimum_soc_pct", "SOC [%]", "Minimum SOC"),
        ("rolling_total_terminal_slack_kwh", None, "kWh", "Terminal slack"),
    ]
    colors = {
        0.20: "#64748B",
        0.30: "#9333EA",
        0.40: "#0f766e",
        0.50: "#1d4ed8",
        0.60: "#b45309",
    }

    for ax, (column, reference_column, ylabel, title) in zip(axes.flatten(), panels):
        for target, target_rows in sorted(grouped.items()):
            x = [float(row["c_term_g_per_kwh"]) for row in target_rows]
            y = [float(row[column]) for row in target_rows]
            ax.plot(
                x,
                y,
                marker="o",
                linewidth=2.2,
                markersize=6,
                label=f"{target:.0%}",
                color=colors.get(target),
            )
        if reference_column is not None:
            reference_value = float(rows[0][reference_column])
            ax.axhline(
                reference_value,
                color="#111827",
                linestyle="--",
                linewidth=1.4,
                alpha=0.75,
                label="Full-horizon MILP" if column == "rolling_total_fuel_kg" else None,
            )
        ax.set_xscale("linear")
        ax.set_xlabel("C_term [g/kWh]", fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(title, fontsize=15)
        ax.tick_params(axis="both", labelsize=11)

    axes[0, 0].legend(title="Terminal target", fontsize=10, title_fontsize=10)
    fig.suptitle("Operational rolling-horizon reserve tuning", fontsize=18, fontweight="bold")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def load_dispatch(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    dispatch = pd.read_csv(path)
    dispatch["datetime"] = pd.to_datetime(dispatch["datetime"])
    dispatch["generator"] = dispatch["generator"].astype(str)
    wide = (
        dispatch.groupby("timestep")
        .agg(
            datetime=("datetime", "first"),
            load_kw=("load_kw", "first"),
            P_ch_kw=("P_ch_kw", "first"),
            P_dis_kw=("P_dis_kw", "first"),
            E_kwh=("E_kwh", "first"),
            soc_pct=("soc_pct", "first"),
            total_gen_kw=("Pg_kw", "sum"),
        )
        .reset_index()
    )
    wide["battery_net_kw"] = wide["P_dis_kw"] - wide["P_ch_kw"]
    return dispatch, wide


def plot_full_horizon_reference_panel(rows: list[dict[str, object]], output_dir: Path) -> None:
    reference_run_dir = Path(str(rows[0]["run_dir"]))
    dispatch_path = reference_run_dir / "full_horizon_benchmark_dispatch_results.csv"
    if not dispatch_path.exists():
        raise FileNotFoundError(f"Missing full-horizon benchmark dispatch file: {dispatch_path}")

    dispatch, wide = load_dispatch(dispatch_path)
    full = rows[0]
    times = wide["datetime"]
    fig, axes = plt.subplots(
        3,
        1,
        figsize=(16, 10.5),
        sharex=True,
        constrained_layout=True,
        gridspec_kw={"height_ratios": [3.0, 0.8, 1.1]},
    )

    axes[0].step(times, wide["load_kw"], where="post", color="black", linewidth=2.0, label="Load")
    for generator, grp in dispatch.groupby("generator"):
        grp = grp.sort_values("timestep")
        axes[0].step(
            times,
            grp["Pg_kw"].to_numpy(),
            where="post",
            linewidth=1.7,
            label=f"Gen {generator}",
        )
    axes[0].fill_between(
        times,
        0,
        wide["battery_net_kw"].clip(lower=0.0),
        step="post",
        color="#D62728",
        alpha=0.32,
        label="Battery discharge",
    )
    axes[0].fill_between(
        times,
        0,
        wide["battery_net_kw"].clip(upper=0.0),
        step="post",
        color="#2CA02C",
        alpha=0.32,
        label="Battery charge",
    )
    axes[0].set_ylabel("Power [kW]", fontsize=13)
    axes[0].legend(loc="upper left", ncol=3, fontsize=10)
    axes[0].grid(axis="y", alpha=0.25)

    for idx, (generator, grp) in enumerate(dispatch.groupby("generator"), start=1):
        grp = grp.sort_values("timestep")
        on = grp["u"].to_numpy() > 0.5
        axes[1].fill_between(
            times,
            idx - 0.32,
            idx + 0.32,
            where=on,
            step="post",
            alpha=0.55,
            label=f"Gen {generator}",
        )
        starts = grp[grp["startup"] > 0.5]["datetime"]
        if not starts.empty:
            axes[1].scatter(starts, [idx + 0.42] * len(starts), marker="^", s=42, color="#111827")
    axes[1].set_yticks([1, 2], labels=["Gen 1", "Gen 2"])
    axes[1].set_ylim(0.4, 2.75)
    axes[1].set_ylabel("Unit", fontsize=13)
    axes[1].grid(axis="y", alpha=0.2)

    axes[2].plot(times, wide["soc_pct"], color="#2F6DB3", linewidth=2.1)
    axes[2].axhline(20.0, color="#64748B", linestyle="--", linewidth=1.1, label="SOC min")
    axes[2].axhline(80.0, color="#64748B", linestyle=":", linewidth=1.1, label="SOC max")
    axes[2].set_ylabel("SOC [%]", fontsize=13)
    axes[2].set_xlabel("Time", fontsize=13)
    axes[2].set_ylim(0, 100)
    axes[2].grid(axis="y", alpha=0.25)
    axes[2].legend(loc="upper left", fontsize=10)

    fig.suptitle(
        "Full-horizon MILP reference for operational rolling-horizon sweep\n"
        f"Fuel {float(full['full_horizon_total_fuel_kg']):.1f} kg, "
        f"starts {int(full['full_horizon_generator_starts'])}, "
        f"min SOC {float(full['full_horizon_minimum_soc_pct']):.1f}%, "
        f"final SOC {float(full['full_horizon_final_soc_pct']):.1f}%",
        fontsize=16,
        fontweight="bold",
    )
    out_path = output_dir / "full_horizon_milp_reference_panel.png"
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
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

    output_dir = OUTPUT_DIR
    generated_configs_dir = output_dir / "generated_configs"
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_configs_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = read_existing_rows(output_dir / "summary.csv")
    manifest_rows: list[dict[str, object]] = read_existing_rows(output_dir / "run_manifest.csv")
    existing_keys = {case_key(row) for row in rows}

    total_cases = len(args.terminal_soc_targets) * len(args.c_term_values)
    case_idx = 0
    for terminal_soc_target in args.terminal_soc_targets:
        for c_term in args.c_term_values:
            case_idx += 1
            key = (float(terminal_soc_target), float(c_term))
            if key in existing_keys:
                print(
                    f"[{case_idx}/{total_cases}] Skipping existing terminal_soc_target={terminal_soc_target:.0%}, "
                    f"C_term={c_term:g} g/kWh",
                    flush=True,
                )
                continue
            target_stub = pct_label(terminal_soc_target)
            c_stub = cterm_label(c_term)
            print(
                f"[{case_idx}/{total_cases}] Running terminal_soc_target={terminal_soc_target:.0%}, "
                f"C_term={c_term:g} g/kWh",
                flush=True,
            )
            existing_keys.add(key)
            case_config = build_case_config(base_config, terminal_soc_target, c_term)
            case_config_path = generated_configs_dir / f"rolling_term_{target_stub}_cterm_{c_stub}.toml"
            write_rolling_config(case_config, case_config_path)

            metadata, run_dir, wall_clock_runtime_s = run_case(case_config_path)
            row = case_summary_row(
                terminal_soc_target,
                c_term,
                case_config_path,
                run_dir,
                metadata,
                wall_clock_runtime_s,
            )
            rows.append(row)
            manifest_rows.append(
                {
                    "terminal_soc_target": terminal_soc_target,
                    "terminal_soc_target_pct": terminal_soc_target * 100.0,
                    "c_term_g_per_kwh": c_term,
                    "config_path": str(case_config_path),
                    "run_dir": str(run_dir),
                }
            )

    rows.sort(key=lambda row: (float(row["terminal_soc_target"]), float(row["c_term_g_per_kwh"])))
    manifest_rows.sort(key=lambda row: (float(row["terminal_soc_target"]), float(row["c_term_g_per_kwh"])))
    fixed_50_rows = [row for row in rows if abs(float(row["terminal_soc_target"]) - 0.50) < 1e-9]

    fieldnames = list(rows[0].keys())
    manifest_fieldnames = list(manifest_rows[0].keys())
    write_csv(output_dir / "summary.csv", rows, fieldnames)
    write_csv(output_dir / "cterm_sweep_terminal50.csv", fixed_50_rows, fieldnames)
    write_csv(output_dir / "run_manifest.csv", manifest_rows, manifest_fieldnames)
    write_summary_markdown(output_dir / "summary.md", rows)
    plot_overview(rows, output_dir / "overview.png")
    if not args.skip_reference_panel:
        plot_full_horizon_reference_panel(rows, output_dir)

    print(f"Saved {output_dir / 'summary.csv'}")
    print(f"Saved {output_dir / 'cterm_sweep_terminal50.csv'}")
    print(f"Saved {output_dir / 'run_manifest.csv'}")
    print(f"Saved {output_dir / 'summary.md'}")
    print(f"Saved {output_dir / 'overview.png'}")
    if not args.skip_reference_panel:
        print(f"Saved {output_dir / 'full_horizon_milp_reference_panel.png'}")


if __name__ == "__main__":
    main()
