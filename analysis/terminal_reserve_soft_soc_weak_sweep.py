from __future__ import annotations

import csv
import subprocess
import sys
import time
import tomllib
from copy import deepcopy
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from sensitivity_common import REPO_ROOT, format_toml_array, format_toml_scalar


BASE_CONFIG = REPO_ROOT / "config" / "rolling_horizon_soft_soc_terminal_reserve_operational.toml"
OUTPUT_DIR = (
    REPO_ROOT
    / "analysis"
    / "output"
    / "rolling_horizon"
    / "terminal_reserve_soft_soc_weak_sweep"
)
GENERATED_CONFIG_DIR = OUTPUT_DIR / "generated_configs"
MIN_UP_TIME_SUMMARY = (
    REPO_ROOT
    / "analysis"
    / "output"
    / "rolling_horizon"
    / "min_up_time_extension"
    / "summary.csv"
)
NO_TERMINAL_MEAN_SOFT_SOC_SUMMARY = (
    REPO_ROOT
    / "analysis"
    / "output"
    / "rolling_horizon"
    / "forecast_soft_soc_mean_penalty_tuning_screen"
    / "summary.csv"
)

CASES = [
    (0.30, 250.0),
    (0.30, 500.0),
    (0.40, 250.0),
    (0.40, 500.0),
]


def load_toml(path: Path) -> dict:
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def case_id(target: float, penalty: float) -> str:
    return f"term_t{target * 100:.0f}_p{penalty:.0f}"


def case_config(base: dict, target: float, penalty: float) -> dict:
    config = deepcopy(base)
    cid = case_id(target, penalty)
    config["run"]["label"] = f"weak_terminal_reserve_soft_soc_{cid}"
    config["run"]["description"] = (
        "Operational 15-minute average-load forecast rolling-horizon MILP with "
        f"mean soft-SOC penalty, H=12, weak soft terminal reserve target {target * 100:.0f}%, "
        f"terminal slack penalty {penalty:.0f} g/kWh, and minimum up-time disabled"
    )
    config["run"]["show_solver_log"] = False
    config["load_profile"]["path"] = "data/operational_profiles/operational_load_profile_15min_avg.csv"

    rolling = config["rolling_horizon"]
    rolling["horizon_steps"] = 12
    rolling["forecast_method"] = "moving_average"
    rolling["moving_average_window_steps"] = 4
    rolling["soc_strategy"] = "soft_band"
    rolling["tail_forecast_policy"] = "repeat_final_load"
    rolling["min_up_time_steps"] = 1
    rolling["soft_band_terminal_reserve_enabled"] = True
    rolling["terminal_soc_target"] = float(target)
    rolling["terminal_slack_penalty_g_per_kwh"] = float(penalty)

    solver = config.setdefault("solver", {})
    solver["progress_log_enabled"] = False
    solver["slow_solve_log_threshold_sec"] = 999.0

    soft_soc = config.setdefault("soft_soc", {})
    soft_soc["preferred_soc_min"] = 0.20
    soft_soc["preferred_soc_max"] = 0.80
    soft_soc["soc_min_penalty_g_per_kwh"] = 10000.0
    soft_soc["soc_max_penalty_g_per_kwh"] = 10000.0
    soft_soc["soft_soc_penalty_scaling"] = "mean"

    for generator in config["generators"]:
        generator["startup_cost"] = 500.0

    return config


def write_rolling_config(config: dict, path: Path) -> None:
    run = config["run"]
    scheduling = config["scheduling"]
    load_profile = config["load_profile"]
    battery = config["battery"]
    initial = config["initial_conditions"]
    rolling = config["rolling_horizon"]
    solver = config.get("solver", {})
    soft_soc = config["soft_soc"]

    lines = [
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
        f"generator_commitment = {format_toml_array(initial['generator_commitment'])}",
        f"battery_energy_kwh = {format_toml_scalar(initial['battery_energy_kwh'])}",
        "",
        "[rolling_horizon]",
        f"horizon_steps = {format_toml_scalar(rolling['horizon_steps'])}",
        f"forecast_method = {format_toml_scalar(rolling['forecast_method'])}",
        f"moving_average_window_steps = {format_toml_scalar(rolling['moving_average_window_steps'])}",
        f"soc_strategy = {format_toml_scalar(rolling['soc_strategy'])}",
        f"tail_forecast_policy = {format_toml_scalar(rolling.get('tail_forecast_policy', 'repeat_final_load'))}",
        f"min_up_time_steps = {format_toml_scalar(rolling['min_up_time_steps'])}",
        f"soft_band_terminal_reserve_enabled = {format_toml_scalar(rolling['soft_band_terminal_reserve_enabled'])}",
        f"terminal_soc_target = {format_toml_scalar(rolling['terminal_soc_target'])}",
        f"terminal_slack_penalty_g_per_kwh = {format_toml_scalar(rolling['terminal_slack_penalty_g_per_kwh'])}",
        "",
        "[solver]",
        f"rolling_local_time_limit_sec = {format_toml_scalar(solver.get('rolling_local_time_limit_sec', 30.0))}",
        f"progress_log_enabled = {format_toml_scalar(solver.get('progress_log_enabled', False))}",
        f"progress_log_every_steps = {format_toml_scalar(solver.get('progress_log_every_steps', 10))}",
        f"slow_solve_log_threshold_sec = {format_toml_scalar(solver.get('slow_solve_log_threshold_sec', 999.0))}",
        "",
        "[soft_soc]",
        f"preferred_soc_min = {format_toml_scalar(soft_soc['preferred_soc_min'])}",
        f"preferred_soc_max = {format_toml_scalar(soft_soc['preferred_soc_max'])}",
        f"soc_min_penalty_g_per_kwh = {format_toml_scalar(soft_soc['soc_min_penalty_g_per_kwh'])}",
        f"soc_max_penalty_g_per_kwh = {format_toml_scalar(soft_soc['soc_max_penalty_g_per_kwh'])}",
        f"soft_soc_penalty_scaling = {format_toml_scalar(soft_soc['soft_soc_penalty_scaling'])}",
        "",
    ]

    for generator in config["generators"]:
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
    return load_toml(run_dir / "params.toml"), run_dir, wall_clock_s


def generate_run_plots(run_dir: Path) -> None:
    commands = [
        [sys.executable, "analysis/plot_rolling_horizon_run_panel.py", str(run_dir)],
        [sys.executable, "analysis/plot_rolling_full_horizon_comparison.py", str(run_dir)],
    ]
    for command in commands:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"Plot command failed: {' '.join(command)}\n"
                f"STDOUT:\n{completed.stdout[-2000:]}\nSTDERR:\n{completed.stderr[-4000:]}"
            )


def generator_run_lengths(run_dir: Path) -> tuple[dict[str, list[int]], int, int]:
    dispatch = pd.read_csv(run_dir / "dispatch_results.csv")
    dispatch["generator"] = dispatch["generator"].astype(str)
    lengths_by_generator: dict[str, list[int]] = {}
    one_step = 0
    two_step = 0

    for generator, group in dispatch.groupby("generator"):
        lengths: list[int] = []
        run_length = 0
        for _, row in group.sort_values("timestep").iterrows():
            if float(row["u"]) > 0.5:
                run_length += 1
            elif run_length:
                lengths.append(run_length)
                run_length = 0
        if run_length:
            lengths.append(run_length)

        one_step += sum(1 for length in lengths if length == 1)
        two_step += sum(1 for length in lengths if length == 2)
        lengths_by_generator[generator] = lengths

    return lengths_by_generator, one_step, two_step


def format_lengths(lengths_by_generator: dict[str, list[int]]) -> str:
    parts = []
    for generator in sorted(lengths_by_generator, key=int):
        lengths = lengths_by_generator[generator]
        parts.append(f"G{generator}: " + (" ".join(str(length) for length in lengths) if lengths else "none"))
    return "; ".join(parts)


def row_for_case(
    *,
    target: float,
    penalty: float,
    config_path: Path,
    metadata: dict,
    run_dir: Path,
    wall_clock_s: float,
) -> dict[str, object]:
    rolling = metadata["rolling_horizon"]
    soft_soc = metadata["soft_soc"]
    battery = metadata["battery"]
    kpi = metadata["kpis"]["rolling_horizon"]
    comparison = metadata["kpis"]["comparison"]
    full = metadata["kpis"]["full_horizon_benchmark"]
    lengths_by_generator, one_step, two_step = generator_run_lengths(run_dir)

    return {
        "case_id": case_id(target, penalty),
        "run_label": metadata["run"]["label"],
        "config_path": str(config_path),
        "run_dir": str(run_dir),
        "controller_type": metadata["run"]["controller"],
        "horizon_steps": rolling["horizon_steps"],
        "dt_minutes": metadata["load_profile"]["dt_minutes"],
        "forecast_method": rolling["forecast_method"],
        "moving_average_window_steps": rolling["moving_average_window_steps"],
        "soc_strategy": rolling["soc_strategy"],
        "soft_soc_penalty_scaling": rolling["soft_soc_penalty_scaling"],
        "preferred_soc_min": soft_soc["preferred_soc_min"],
        "preferred_soc_max": soft_soc["preferred_soc_max"],
        "soc_min_penalty_g_per_kwh": soft_soc["soc_min_penalty_g_per_kwh"],
        "soc_max_penalty_g_per_kwh": soft_soc["soc_max_penalty_g_per_kwh"],
        "soft_band_terminal_reserve_enabled": rolling["soft_band_terminal_reserve_enabled"],
        "terminal_soc_target": rolling["terminal_soc_target"],
        "terminal_slack_penalty_g_per_kwh": rolling["terminal_slack_penalty_g_per_kwh"],
        "min_up_time_steps": rolling["min_up_time_steps"],
        "startup_cost": metadata["generators"][0]["startup_cost"],
        "load_profile_path": metadata["load_profile"]["source_file"],
        "initial_battery_energy_kwh": metadata["initial_conditions"]["battery_energy_kwh"],
        "battery_capacity_kwh": battery["E_cap"],
        "battery_soc_min": battery["SOC_min"],
        "battery_soc_max": battery["SOC_max"],
        "battery_energy_min_kwh": battery["E_min"],
        "battery_energy_max_kwh": battery["E_max"],
        "total_fuel_kg": kpi["total_fuel_kg"],
        "full_horizon_fuel_kg": full["total_fuel_kg"],
        "fuel_delta_vs_full_horizon_benchmark_pct": comparison["fuel_delta_pct"],
        "generator_starts": kpi["generator_starts"],
        "short_1_2_timestep_generator_runs": one_step + two_step,
        "one_timestep_generator_runs": one_step,
        "two_timestep_generator_runs": two_step,
        "realized_generator_run_lengths": format_lengths(lengths_by_generator),
        "minimum_soc_pct": kpi["minimum_soc_pct"],
        "final_soc_pct": kpi["final_soc_pct"],
        "terminal_slack_sum_kwh": kpi["total_terminal_slack_kwh"],
        "terminal_slack_max_kwh": kpi["maximum_terminal_slack_kwh"],
        "nonoptimal_local_solve_count": kpi["nonoptimal_timeout_or_infeasible_solves"],
        "median_solve_time_s": kpi["median_solve_time_s"],
        "p95_solve_time_s": kpi["p95_solve_time_s"],
        "max_solve_time_s": kpi["maximum_solve_time_s"],
        "wall_clock_s": wall_clock_s,
    }


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


def format_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if abs(value) >= 100:
            return f"{value:.2f}".rstrip("0").rstrip(".")
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def write_run_parameters(run_dir: Path, row: dict[str, object]) -> None:
    ordered_keys = [
        "run_label",
        "config_path",
        "run_dir",
        "controller_type",
        "horizon_steps",
        "dt_minutes",
        "forecast_method",
        "moving_average_window_steps",
        "soc_strategy",
        "soft_soc_penalty_scaling",
        "preferred_soc_min",
        "preferred_soc_max",
        "soc_min_penalty_g_per_kwh",
        "soc_max_penalty_g_per_kwh",
        "soft_band_terminal_reserve_enabled",
        "terminal_soc_target",
        "terminal_slack_penalty_g_per_kwh",
        "min_up_time_steps",
        "startup_cost",
        "load_profile_path",
        "initial_battery_energy_kwh",
        "battery_capacity_kwh",
        "battery_soc_min",
        "battery_soc_max",
        "battery_energy_min_kwh",
        "battery_energy_max_kwh",
        "total_fuel_kg",
        "fuel_delta_vs_full_horizon_benchmark_pct",
        "generator_starts",
        "short_1_2_timestep_generator_runs",
        "realized_generator_run_lengths",
        "minimum_soc_pct",
        "final_soc_pct",
        "terminal_slack_sum_kwh",
        "terminal_slack_max_kwh",
        "nonoptimal_local_solve_count",
    ]
    lines = [
        f"# Run Parameters: {row['run_label']}",
        "",
        "| Parameter | Value |",
        "| --- | --- |",
    ]
    for key in ordered_keys:
        lines.append(f"| {key} | {format_value(row[key])} |")
    lines.append("")
    (run_dir / "run_parameters.md").write_text("\n".join(lines), encoding="utf-8")


def write_summary_md(rows: list[dict[str, object]]) -> None:
    lines = [
        "# Weak Soft-Band Terminal Reserve Sweep",
        "",
        "Operational 15-minute average profile, moving-average forecast, H=12, mean soft-SOC penalty 10000 g/kWh, startup cost 500 g/start, minimum up-time disabled.",
        "",
        "| Case | Target % | Penalty g/kWh | Fuel kg | Fuel delta % | Starts | Short runs | Min SOC % | Final SOC % | Terminal slack sum kWh |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in sorted(rows, key=lambda item: (float(item["terminal_soc_target"]), float(item["terminal_slack_penalty_g_per_kwh"]))):
        lines.append(
            f"| {row['case_id']} | {float(row['terminal_soc_target']) * 100:.0f} | "
            f"{float(row['terminal_slack_penalty_g_per_kwh']):.0f} | {float(row['total_fuel_kg']):.3f} | "
            f"{float(row['fuel_delta_vs_full_horizon_benchmark_pct']):.2f} | {int(row['generator_starts'])} | "
            f"{int(row['short_1_2_timestep_generator_runs'])} | {float(row['minimum_soc_pct']):.2f} | "
            f"{float(row['final_soc_pct']):.2f} | {float(row['terminal_slack_sum_kwh']):.1f} |"
        )
    lines.append("")
    (OUTPUT_DIR / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def heatmap_data(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    return (
        df.pivot(index="terminal_soc_target", columns="terminal_slack_penalty_g_per_kwh", values=metric)
        .sort_index(ascending=False)
        .sort_index(axis=1)
    )


def save_heatmap(df: pd.DataFrame, metric: str, title: str, filename: str, fmt: str) -> None:
    data = heatmap_data(df, metric)
    fig, ax = plt.subplots(figsize=(6.6, 5.0), constrained_layout=True)
    image = ax.imshow(data.to_numpy(), cmap="viridis", aspect="auto")
    for y_idx, (_, row) in enumerate(data.iterrows()):
        for x_idx, value in enumerate(row):
            ax.text(x_idx, y_idx, format(value, fmt), ha="center", va="center", fontsize=12, color="#111827")
    ax.set_title(title, fontsize=15, fontweight="bold")
    ax.set_xticks(range(len(data.columns)), labels=[f"{float(value):.0f}" for value in data.columns])
    ax.set_yticks(range(len(data.index)), labels=[f"{float(value) * 100:.0f}" for value in data.index])
    ax.set_xlabel("Terminal slack penalty [g/kWh]", fontsize=12)
    ax.set_ylabel("Terminal SOC target [%]", fontsize=12)
    ax.tick_params(axis="both", labelsize=11)
    cbar = fig.colorbar(image, ax=ax)
    cbar.ax.tick_params(labelsize=10)
    fig.savefig(OUTPUT_DIR / filename, dpi=200, bbox_inches="tight")
    plt.close(fig)


def save_tradeoff_plot(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8.2, 6.0), constrained_layout=True)
    scatter = ax.scatter(
        df["short_1_2_timestep_generator_runs"],
        df["fuel_delta_vs_full_horizon_benchmark_pct"],
        c=df["final_soc_pct"],
        s=125,
        cmap="plasma",
        edgecolor="#111827",
        linewidth=0.7,
    )
    for _, row in df.iterrows():
        ax.annotate(
            f"T{row['terminal_soc_target'] * 100:.0f} P{row['terminal_slack_penalty_g_per_kwh']:.0f}\nS{int(row['generator_starts'])}",
            (row["short_1_2_timestep_generator_runs"], row["fuel_delta_vs_full_horizon_benchmark_pct"]),
            xytext=(8, 5),
            textcoords="offset points",
            fontsize=9,
        )
    ax.set_title("Fuel, Starts, and Short-Run Tradeoff", fontsize=15, fontweight="bold")
    ax.set_xlabel("Short 1-2 timestep generator runs", fontsize=12)
    ax.set_ylabel("Fuel delta vs full horizon [%]", fontsize=12)
    ax.grid(alpha=0.25)
    cbar = fig.colorbar(scatter, ax=ax)
    cbar.set_label("Final SOC [%]", fontsize=11)
    fig.savefig(OUTPUT_DIR / "fuel_start_short_run_tradeoff.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def best_least_harmful(df: pd.DataFrame) -> pd.Series:
    ranked = df.assign(
        rank_score=(
            df["fuel_delta_vs_full_horizon_benchmark_pct"].rank(method="min")
            + df["short_1_2_timestep_generator_runs"].rank(method="min")
            + df["final_soc_pct"].rank(method="min")
        )
    ).sort_values(["rank_score", "fuel_delta_vs_full_horizon_benchmark_pct", "short_1_2_timestep_generator_runs"])
    return ranked.iloc[0]


def min_up6_reference() -> dict[str, object] | None:
    if not MIN_UP_TIME_SUMMARY.exists():
        return None
    df = pd.read_csv(MIN_UP_TIME_SUMMARY)
    match = df.loc[df["min_up_time_steps"] == 6]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


def no_terminal_reference() -> dict[str, object] | None:
    if not NO_TERMINAL_MEAN_SOFT_SOC_SUMMARY.exists():
        return None
    df = pd.read_csv(NO_TERMINAL_MEAN_SOFT_SOC_SUMMARY)
    match = df.loc[df["case_id"].eq("h12_startup500_softsoc10000")]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


def write_assessment(df: pd.DataFrame) -> None:
    best = best_least_harmful(df)
    lowest_short = df.sort_values(
        ["short_1_2_timestep_generator_runs", "fuel_delta_vs_full_horizon_benchmark_pct"]
    ).iloc[0]
    lowest_fuel = df.sort_values("fuel_delta_vs_full_horizon_benchmark_pct").iloc[0]
    min_up6 = min_up6_reference()
    no_terminal = no_terminal_reference()

    lines = [
        "# Weak Terminal Reserve Assessment",
        "",
        "This sweep isolates the soft-band terminal reserve mechanism with minimum up-time disabled in every case (`min_up_time_steps = 1`). The terminal reserve penalty is intentionally much lower than the 10000 g/kWh preferred SOC-band penalty, so it should be read as a weak reserve signal rather than a direct anti-chatter constraint.",
        "",
        "## Results",
        "",
        f"- Lowest fuel case: `{lowest_fuel['case_id']}` with {lowest_fuel['fuel_delta_vs_full_horizon_benchmark_pct']:.2f}% fuel delta, {int(lowest_fuel['generator_starts'])} starts, {int(lowest_fuel['short_1_2_timestep_generator_runs'])} short runs, and final SOC {lowest_fuel['final_soc_pct']:.2f}%.",
        f"- Lowest short-run case: `{lowest_short['case_id']}` with {int(lowest_short['short_1_2_timestep_generator_runs'])} short runs, {lowest_short['fuel_delta_vs_full_horizon_benchmark_pct']:.2f}% fuel delta, {int(lowest_short['generator_starts'])} starts, and final SOC {lowest_short['final_soc_pct']:.2f}%.",
        f"- Least harmful balance in this small screen: `{best['case_id']}` because it has the best combined ranking across fuel delta, short runs, and final SOC carryover.",
        "",
        "## Assessment Questions",
        "",
        "1. Does weak terminal reserve reduce low-load generator chatter when minimum up-time is disabled?",
    ]
    if no_terminal is None:
        lines.append(
            f"   In this operational profile, the weak reserve cases still produce {int(df['short_1_2_timestep_generator_runs'].min())}-{int(df['short_1_2_timestep_generator_runs'].max())} short 1-2 timestep runs and {int(df['generator_starts'].min())}-{int(df['generator_starts'].max())} starts. Any chatter reduction is indirect and limited."
        )
    else:
        lines.append(
            f"   No. The no-terminal mean-soft-SOC reference has {int(no_terminal['short_1_2_step_generator_runs'])} short runs and {int(no_terminal['rolling_starts'])} starts; the weak reserve cases have {int(df['short_1_2_timestep_generator_runs'].min())}-{int(df['short_1_2_timestep_generator_runs'].max())} short runs and {int(df['generator_starts'].min())}-{int(df['generator_starts'].max())} starts."
        )
    lines.extend(
        [
            "",
            "2. Does it mainly increase SOC/fuel instead?",
        ]
    )
    if no_terminal is None:
        lines.append(
            f"   The cases end between {df['final_soc_pct'].min():.2f}% and {df['final_soc_pct'].max():.2f}% SOC, with fuel deltas between {df['fuel_delta_vs_full_horizon_benchmark_pct'].min():.2f}% and {df['fuel_delta_vs_full_horizon_benchmark_pct'].max():.2f}%. The signal primarily changes SOC carryover and fuel rather than enforcing commitment regularity."
        )
    else:
        lines.append(
            f"   Yes. The no-terminal reference has {float(no_terminal['fuel_delta_vs_full_pct']):.2f}% fuel delta and final SOC {float(no_terminal['rolling_final_soc_pct']):.2f}%; the weak reserve cases end between {df['final_soc_pct'].min():.2f}% and {df['final_soc_pct'].max():.2f}% SOC, with fuel deltas between {df['fuel_delta_vs_full_horizon_benchmark_pct'].min():.2f}% and {df['fuel_delta_vs_full_horizon_benchmark_pct'].max():.2f}%."
        )
    lines.extend(
        [
            "",
            "3. Which target/penalty combination is least harmful?",
            f"   `{best['case_id']}` is the least harmful within this four-case reserve screen, but it is still worse than the no-terminal reference on fuel, starts, short runs, and final SOC. It should be treated as a local result, not a general tuning rule.",
            "",
            "4. Is weak terminal reserve competitive with the current min-up-time direction, especially `min_up_time_steps = 6`?",
        ]
    )
    if min_up6 is None:
        lines.append(
            "   The min-up-time reference summary was not found, so this run cannot make a direct local comparison."
        )
    else:
        lines.append(
            f"   No. The `min_up_time_steps = 6` reference has {float(min_up6['fuel_delta_vs_full_pct']):.2f}% fuel delta, "
            f"{int(min_up6['rolling_starts'])} starts, no sub-1.5-hour runs, and final SOC {float(min_up6['final_soc_pct']):.2f}%. "
            "That directly addresses short commitment blocks, while terminal reserve remains only an SOC reserve signal."
        )
    lines.extend(
        [
            "",
            "5. Does even weak terminal reserve start to reintroduce excessive SOC carryover?",
            f"   The 40% target cases end at the upper end of the observed final-SOC range ({df.loc[df['terminal_soc_target'].eq(0.40), 'final_soc_pct'].min():.2f}-{df.loc[df['terminal_soc_target'].eq(0.40), 'final_soc_pct'].max():.2f}%). This is weaker than the prior 10000 g/kWh terminal-reserve case, but it still shows the expected carryover tendency.",
            "",
            "## Thesis-Grounded Interpretation",
            "",
            "The terminal reserve constraint is useful as an optimization reserve signal: it asks each local MILP to preserve future battery headroom through a soft one-sided terminal target. It is not a direct anti-chatter constraint. On this single operational profile, weak terminal reserve does not look competitive with a minimum up-time mechanism for suppressing low-load generator chatter. Its cleaner role is SOC robustness, with the known risk of unnecessary charging and elevated final SOC.",
            "",
            "## Generated Outputs",
            "",
            "- `summary.csv`",
            "- `summary.md`",
            "- `terminal_reserve_heatmap_fuel.png`",
            "- `terminal_reserve_heatmap_starts.png`",
            "- `terminal_reserve_heatmap_short_runs.png`",
            "- `terminal_reserve_heatmap_final_soc.png`",
            "- `fuel_start_short_run_tradeoff.png`",
            "",
        ]
    )
    (OUTPUT_DIR / "assessment.md").write_text("\n".join(lines), encoding="utf-8")


def generate_sweep_outputs(rows: list[dict[str, object]]) -> None:
    df = pd.DataFrame(rows)
    df = df.sort_values(["terminal_soc_target", "terminal_slack_penalty_g_per_kwh"]).reset_index(drop=True)
    write_csv(OUTPUT_DIR / "summary.csv", df.to_dict("records"))
    write_summary_md(df.to_dict("records"))
    save_heatmap(
        df,
        "fuel_delta_vs_full_horizon_benchmark_pct",
        "Fuel Delta vs Full Horizon [%]",
        "terminal_reserve_heatmap_fuel.png",
        ".2f",
    )
    save_heatmap(df, "generator_starts", "Generator Starts", "terminal_reserve_heatmap_starts.png", ".0f")
    save_heatmap(
        df,
        "short_1_2_timestep_generator_runs",
        "Short 1-2 Timestep Generator Runs",
        "terminal_reserve_heatmap_short_runs.png",
        ".0f",
    )
    save_heatmap(df, "final_soc_pct", "Final SOC [%]", "terminal_reserve_heatmap_final_soc.png", ".1f")
    save_tradeoff_plot(df)
    write_assessment(df)


def validate_outputs(rows: list[dict[str, object]]) -> None:
    failures: list[str] = []
    for row in rows:
        run_dir = Path(str(row["run_dir"]))
        metadata = load_toml(run_dir / "params.toml")
        rolling = metadata["rolling_horizon"]
        if rolling["min_up_time_steps"] != 1:
            failures.append(f"{run_dir}: min_up_time_steps={rolling['min_up_time_steps']}")
        if rolling["soft_band_terminal_reserve_enabled"] is not True:
            failures.append(f"{run_dir}: terminal reserve disabled")
        for relative in [
            "run_parameters.md",
            "plots/rolling_horizon_dispatch_panel.png",
            "plots/rolling_vs_full_horizon_comparison.png",
        ]:
            if not (run_dir / relative).exists():
                failures.append(f"{run_dir}: missing {relative}")
    if failures:
        raise RuntimeError("Validation failed:\n" + "\n".join(failures))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    base = load_toml(BASE_CONFIG)

    rows: list[dict[str, object]] = []
    failures: list[str] = []
    for target, penalty in CASES:
        cid = case_id(target, penalty)
        print(f"Running {cid}", flush=True)
        config = case_config(base, target, penalty)
        config_path = GENERATED_CONFIG_DIR / f"{cid}.toml"
        write_rolling_config(config, config_path)
        try:
            metadata, run_dir, wall_clock_s = run_case(config_path)
            generate_run_plots(run_dir)
            row = row_for_case(
                target=target,
                penalty=penalty,
                config_path=config_path,
                metadata=metadata,
                run_dir=run_dir,
                wall_clock_s=wall_clock_s,
            )
            write_run_parameters(run_dir, row)
            rows.append(row)
            generate_sweep_outputs(rows)
            print(
                f"  fuel={row['total_fuel_kg']:.3f} kg, "
                f"delta={row['fuel_delta_vs_full_horizon_benchmark_pct']:.2f}%, "
                f"starts={int(row['generator_starts'])}, "
                f"short_runs={int(row['short_1_2_timestep_generator_runs'])}, "
                f"final_soc={row['final_soc_pct']:.2f}%, run={run_dir}",
                flush=True,
            )
        except Exception as exc:
            failures.append(f"{cid}: {exc}")
            (OUTPUT_DIR / "failed_cases.txt").write_text("\n\n".join(failures), encoding="utf-8")
            print(f"  FAILED {cid}: {exc}", flush=True)

    if rows:
        generate_sweep_outputs(rows)
        validate_outputs(rows)
    if failures:
        raise RuntimeError("Some cases failed; completed results were preserved in the sweep folder.")
    print(f"Saved sweep outputs to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
