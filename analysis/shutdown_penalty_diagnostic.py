from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import time
import tomllib
from copy import deepcopy
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from oracle_operational_tuning_screen import write_rolling_config
from sensitivity_common import REPO_ROOT


BASE_CONFIG = REPO_ROOT / "config" / "rolling_horizon_soft_soc_min_up6_operational.toml"
OUTPUT_DIR = (
    REPO_ROOT
    / "analysis"
    / "output"
    / "rolling_horizon"
    / "shutdown_penalty_diagnostic"
)
GENERATED_CONFIG_DIR = OUTPUT_DIR / "generated_configs"
PLOTS_DIR = OUTPUT_DIR / "plots"
DISPATCH_PLOTS_DIR = PLOTS_DIR / "dispatch_panels"

LOAD_PROFILE = "data/operational_profiles/operational_load_profile_15min_avg.csv"
SHUTDOWN_COSTS = [0.0, 250.0, 500.0, 1000.0]
HORIZON_STEPS = 16
MOVING_AVERAGE_WINDOW_STEPS = 4
STARTUP_COST = 500.0
SOFT_SOC_PENALTY = 10000.0
MIN_UP_STEPS = 6
LOCAL_TIME_LIMIT_S = 30.0
INITIAL_BATTERY_KWH = 564.0
INITIAL_COMMITMENT = [0, 0]

MARCH3_WINDOW = ("2026-03-03 13:30", "2026-03-03 17:45")

BASELINE_EXPECTED = {
    "rolling_fuel_kg": 688.44,
    "fuel_delta_vs_full_pct": 2.54,
    "rolling_starts": 5,
    "minimum_soc_pct": 20.09,
    "final_soc_pct": 27.44,
    "run_lengths_steps": "18 13 14 6 19",
}
BASELINE_TOLERANCES = {
    "rolling_fuel_kg": 0.08,
    "fuel_delta_vs_full_pct": 0.08,
    "minimum_soc_pct": 0.08,
    "final_soc_pct": 0.08,
}

SUMMARY_FIELDS = [
    "case_id",
    "shutdown_cost_g_per_shutdown",
    "horizon_steps",
    "moving_average_window_steps",
    "startup_cost_g_per_start",
    "soft_soc_penalty_g_per_kwh",
    "min_up_time_steps",
    "rolling_fuel_kg",
    "fuel_delta_vs_full_pct",
    "rolling_starts",
    "rolling_shutdowns",
    "full_starts",
    "full_shutdowns",
    "minimum_soc_pct",
    "maximum_soc_pct",
    "final_soc_pct",
    "realized_low_soc_slack_kwh",
    "realized_high_soc_slack_kwh",
    "local_low_soc_slack_kwh",
    "local_high_soc_slack_kwh",
    "run_count",
    "run_lengths_steps",
    "shorter_than_min_up_runs",
    "minimum_length_runs",
    "median_solve_s",
    "p95_solve_s",
    "max_solve_s",
    "nonoptimal_timeout_infeasible_local_solve_count",
    "physical_soc_violation",
    "march3_high_load_online_fraction",
    "march3_continuous_genset_online",
    "march3_online_at_1745",
    "wall_clock_s",
    "config_path",
    "run_dir",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a small shutdown-penalty diagnostic for the H16 MA4 rolling-horizon baseline."
    )
    parser.add_argument(
        "--plots-only",
        action="store_true",
        help="Regenerate plots and assessment from existing summary.csv without running cases.",
    )
    parser.add_argument(
        "--rerun-existing",
        action="store_true",
        help="Rerun cases even if they already appear in summary.csv, replacing their summary rows.",
    )
    return parser.parse_args()


def load_existing_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def case_specs() -> list[dict[str, object]]:
    return [
        {
            "case_id": f"shutdown_cost_{int(cost):04d}g",
            "shutdown_cost": cost,
        }
        for cost in SHUTDOWN_COSTS
    ]


def build_config(base: dict, case: dict[str, object]) -> dict:
    config = deepcopy(base)
    shutdown_cost = float(case["shutdown_cost"])
    case_id = str(case["case_id"])

    config["run"]["label"] = f"rolling_shutdown_penalty_{case_id}"
    config["run"]["description"] = (
        "Shutdown-penalty diagnostic for the selected H16 MA4 rolling-horizon "
        f"baseline candidate: shutdown_cost={shutdown_cost:g} g/shutdown"
    )
    config["run"]["show_solver_log"] = False
    config["load_profile"]["path"] = LOAD_PROFILE
    config["scheduling"]["dt_minutes"] = 15
    config["initial_conditions"]["battery_energy_kwh"] = INITIAL_BATTERY_KWH
    config["initial_conditions"]["generator_commitment"] = list(INITIAL_COMMITMENT)
    config.pop("terminal_conditions", None)

    rolling = config["rolling_horizon"]
    rolling["horizon_steps"] = HORIZON_STEPS
    rolling["forecast_method"] = "moving_average"
    rolling["moving_average_window_steps"] = MOVING_AVERAGE_WINDOW_STEPS
    rolling["soc_strategy"] = "soft_band"
    rolling["tail_forecast_policy"] = "repeat_final_load"
    rolling["min_up_time_steps"] = MIN_UP_STEPS
    rolling["soft_band_terminal_reserve_enabled"] = False
    rolling.pop("terminal_soc_target", None)
    rolling.pop("terminal_slack_penalty_g_per_kwh", None)

    solver = config.setdefault("solver", {})
    solver["rolling_local_time_limit_sec"] = LOCAL_TIME_LIMIT_S
    solver["progress_log_enabled"] = False
    solver["progress_log_every_steps"] = 25
    solver["slow_solve_log_threshold_sec"] = 999.0

    soft = config.setdefault("soft_soc", {})
    soft["preferred_soc_min"] = 0.20
    soft["preferred_soc_max"] = 0.80
    soft["soc_min_penalty_g_per_kwh"] = SOFT_SOC_PENALTY
    soft["soc_max_penalty_g_per_kwh"] = SOFT_SOC_PENALTY
    soft["soft_soc_penalty_scaling"] = "mean"

    for generator in config["generators"]:
        generator["startup_cost"] = STARTUP_COST
        generator["shutdown_cost"] = shutdown_cost

    return config


def verify_generated_config(path: Path, case: dict[str, object]) -> None:
    with open(path, "rb") as fh:
        config = tomllib.load(fh)

    rolling = config["rolling_horizon"]
    solver = config["solver"]
    soft = config["soft_soc"]
    initial = config["initial_conditions"]
    shutdown_cost = float(case["shutdown_cost"])

    checks = {
        "load profile": config["load_profile"]["path"] == LOAD_PROFILE,
        "forecast method": rolling["forecast_method"] == "moving_average",
        "MA4": rolling["moving_average_window_steps"] == MOVING_AVERAGE_WINDOW_STEPS,
        "horizon": rolling["horizon_steps"] == HORIZON_STEPS,
        "soft band": rolling["soc_strategy"] == "soft_band",
        "preferred low": abs(float(soft["preferred_soc_min"]) - 0.20) < 1e-12,
        "preferred high": abs(float(soft["preferred_soc_max"]) - 0.80) < 1e-12,
        "mean scaling": soft["soft_soc_penalty_scaling"] == "mean",
        "soft SOC penalty low": abs(float(soft["soc_min_penalty_g_per_kwh"]) - SOFT_SOC_PENALTY) < 1e-9,
        "soft SOC penalty high": abs(float(soft["soc_max_penalty_g_per_kwh"]) - SOFT_SOC_PENALTY) < 1e-9,
        "min up": rolling["min_up_time_steps"] == MIN_UP_STEPS,
        "soft terminal reserve disabled": rolling["soft_band_terminal_reserve_enabled"] is False,
        "local time limit": abs(float(solver["rolling_local_time_limit_sec"]) - LOCAL_TIME_LIMIT_S) < 1e-9,
        "initial energy": abs(float(initial["battery_energy_kwh"]) - INITIAL_BATTERY_KWH) < 1e-9,
        "initial commitment": list(initial["generator_commitment"]) == INITIAL_COMMITMENT,
        "startup cost": all(abs(float(g["startup_cost"]) - STARTUP_COST) < 1e-9 for g in config["generators"]),
        "shutdown cost": all(abs(float(g.get("shutdown_cost", 0.0)) - shutdown_cost) < 1e-9 for g in config["generators"]),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"{path} failed generated-config verification: {', '.join(failed)}")


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
            f"Case failed: {config_path}\nSTDOUT:\n{completed.stdout[-5000:]}\nSTDERR:\n{completed.stderr[-5000:]}"
        )
    run_dir = Path((REPO_ROOT / ".current_run").read_text(encoding="utf-8").strip())
    with open(run_dir / "params.toml", "rb") as fh:
        metadata = tomllib.load(fh)
    return metadata, run_dir, wall_clock_s


def dispatch_path(run_dir: Path, *, full_horizon: bool = False) -> Path:
    filename = "full_horizon_benchmark_dispatch_results.csv" if full_horizon else "dispatch_results.csv"
    return run_dir / filename


def load_dispatch(run_dir: Path, *, full_horizon: bool = False) -> pd.DataFrame:
    df = pd.read_csv(dispatch_path(run_dir, full_horizon=full_horizon))
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def shutdown_count(run_dir: Path, *, full_horizon: bool = False) -> int:
    dispatch = load_dispatch(run_dir, full_horizon=full_horizon)
    total = 0
    for generator, grp in dispatch.groupby("generator"):
        prev = INITIAL_COMMITMENT[int(generator) - 1]
        for value in (grp.sort_values("timestep")["u"] > 0.5).astype(int):
            if prev == 1 and int(value) == 0:
                total += 1
            prev = int(value)
    return total


def generator_run_lengths(run_dir: Path) -> list[int]:
    dispatch = load_dispatch(run_dir)
    lengths: list[int] = []
    for _, grp in dispatch.groupby("generator"):
        run_length = 0
        for is_on in (grp.sort_values("timestep")["u"] > 0.5):
            if is_on:
                run_length += 1
            elif run_length:
                lengths.append(run_length)
                run_length = 0
        if run_length:
            lengths.append(run_length)
    return lengths


def window_online_metrics(run_dir: Path, start: str, end: str) -> tuple[float, bool, bool]:
    dispatch = load_dispatch(run_dir)
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    window = dispatch[(dispatch["datetime"] >= start_ts) & (dispatch["datetime"] <= end_ts)]
    if window.empty:
        return 0.0, False, False

    fractions = []
    continuous = False
    for _, grp in window.groupby("generator"):
        values = (grp.sort_values("datetime")["u"] > 0.5).to_numpy()
        fractions.append(float(values.mean()))
        continuous = continuous or bool(values.all())

    exact_end = dispatch[dispatch["datetime"] == end_ts]
    online_at_end = bool((exact_end["u"] > 0.5).any()) if not exact_end.empty else False
    return max(fractions) if fractions else 0.0, continuous, online_at_end


def physical_soc_violation(metadata: dict) -> bool:
    rolling = metadata["kpis"]["rolling_horizon"]
    return bool(
        float(rolling["minimum_soc_pct"]) < -1e-6
        or float(rolling["maximum_soc_pct"]) > 100.0 + 1e-6
    )


def summary_row(
    case: dict[str, object],
    config_path: Path,
    metadata: dict,
    run_dir: Path,
    wall_clock_s: float,
) -> dict[str, object]:
    rolling = metadata["kpis"]["rolling_horizon"]
    full = metadata["kpis"]["full_horizon_benchmark"]
    comparison = metadata["kpis"]["comparison"]
    recorded = metadata["rolling_horizon"]
    min_up = int(recorded["min_up_time_steps"])
    lengths = generator_run_lengths(run_dir)
    march3_fraction, march3_continuous, march3_online_at_1745 = window_online_metrics(run_dir, *MARCH3_WINDOW)

    return {
        "case_id": case["case_id"],
        "shutdown_cost_g_per_shutdown": float(case["shutdown_cost"]),
        "horizon_steps": HORIZON_STEPS,
        "moving_average_window_steps": MOVING_AVERAGE_WINDOW_STEPS,
        "startup_cost_g_per_start": STARTUP_COST,
        "soft_soc_penalty_g_per_kwh": SOFT_SOC_PENALTY,
        "min_up_time_steps": min_up,
        "rolling_fuel_kg": rolling["total_fuel_kg"],
        "fuel_delta_vs_full_pct": comparison["fuel_delta_pct"],
        "rolling_starts": rolling["generator_starts"],
        "rolling_shutdowns": shutdown_count(run_dir),
        "full_starts": full["generator_starts"],
        "full_shutdowns": shutdown_count(run_dir, full_horizon=True),
        "minimum_soc_pct": rolling["minimum_soc_pct"],
        "maximum_soc_pct": rolling["maximum_soc_pct"],
        "final_soc_pct": rolling["final_soc_pct"],
        "realized_low_soc_slack_kwh": rolling["realized_total_soc_min_slack_kwh"],
        "realized_high_soc_slack_kwh": rolling["realized_total_soc_max_slack_kwh"],
        "local_low_soc_slack_kwh": rolling["local_total_soc_min_slack_kwh"],
        "local_high_soc_slack_kwh": rolling["local_total_soc_max_slack_kwh"],
        "run_count": len(lengths),
        "run_lengths_steps": " ".join(str(value) for value in lengths),
        "shorter_than_min_up_runs": sum(value < min_up for value in lengths),
        "minimum_length_runs": sum(value == min_up for value in lengths),
        "median_solve_s": rolling["median_solve_time_s"],
        "p95_solve_s": rolling["p95_solve_time_s"],
        "max_solve_s": rolling["maximum_solve_time_s"],
        "nonoptimal_timeout_infeasible_local_solve_count": rolling[
            "nonoptimal_timeout_or_infeasible_solves"
        ],
        "physical_soc_violation": physical_soc_violation(metadata),
        "march3_high_load_online_fraction": march3_fraction,
        "march3_continuous_genset_online": march3_continuous,
        "march3_online_at_1745": march3_online_at_1745,
        "wall_clock_s": wall_clock_s,
        "config_path": str(config_path),
        "run_dir": str(run_dir),
    }


def as_float(row: dict[str, object], key: str) -> float:
    return float(row[key])


def as_int(row: dict[str, object], key: str) -> int:
    return int(float(row[key]))


def as_bool(row: dict[str, object], key: str) -> bool:
    value = row[key]
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def is_clean(row: dict[str, object]) -> bool:
    return (
        not as_bool(row, "physical_soc_violation")
        and as_int(row, "nonoptimal_timeout_infeasible_local_solve_count") == 0
    )


def normalize_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(rows, key=lambda row: as_float(row, "shutdown_cost_g_per_shutdown"))


def refresh_derived_metrics(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    refreshed: list[dict[str, object]] = []
    for row in rows:
        updated = dict(row)
        run_dir = Path(str(updated["run_dir"]))
        lengths = generator_run_lengths(run_dir)
        min_up = as_int(updated, "min_up_time_steps")
        march3_fraction, march3_continuous, online_at_1745 = window_online_metrics(run_dir, *MARCH3_WINDOW)
        updated["rolling_shutdowns"] = shutdown_count(run_dir)
        updated["full_shutdowns"] = shutdown_count(run_dir, full_horizon=True)
        updated["run_count"] = len(lengths)
        updated["run_lengths_steps"] = " ".join(str(value) for value in lengths)
        updated["shorter_than_min_up_runs"] = sum(value < min_up for value in lengths)
        updated["minimum_length_runs"] = sum(value == min_up for value in lengths)
        updated["march3_high_load_online_fraction"] = march3_fraction
        updated["march3_continuous_genset_online"] = march3_continuous
        updated["march3_online_at_1745"] = online_at_1745
        refreshed.append(updated)
    return refreshed


def check_zero_case(rows: list[dict[str, object]]) -> None:
    zero = next((row for row in rows if abs(as_float(row, "shutdown_cost_g_per_shutdown")) < 1e-9), None)
    if zero is None:
        return

    failures: list[str] = []
    for key, expected in BASELINE_EXPECTED.items():
        if key in BASELINE_TOLERANCES:
            actual = as_float(zero, key)
            if abs(actual - float(expected)) > BASELINE_TOLERANCES[key]:
                failures.append(f"{key}: expected {expected}, got {actual:.4f}")
        elif key == "rolling_starts":
            actual = as_int(zero, key)
            if actual != int(expected):
                failures.append(f"{key}: expected {expected}, got {actual}")
        elif key == "run_lengths_steps":
            actual = str(zero[key]).strip()
            if actual != str(expected):
                failures.append(f"{key}: expected `{expected}`, got `{actual}`")

    if failures:
        raise RuntimeError(
            "The 0 g/shutdown case did not reproduce the current H16 MA4 baseline. "
            "Stop and diagnose before interpreting nonzero shutdown penalties.\n"
            + "\n".join(f"- {failure}" for failure in failures)
        )


def plot_metric(df: pd.DataFrame, y: str, ylabel: str, title: str, output_name: str) -> Path:
    fig, ax = plt.subplots(figsize=(7.8, 4.8), constrained_layout=True)
    ax.plot(
        df["shutdown_cost_g_per_shutdown"],
        df[y],
        marker="o",
        linewidth=2.2,
        color="#2563EB",
    )
    ax.set_xlabel("Shutdown penalty [g/shutdown]")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_xticks(SHUTDOWN_COSTS)
    ax.grid(True, alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    path = PLOTS_DIR / output_name
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def plot_starts_shutdowns(df: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(7.8, 4.8), constrained_layout=True)
    x = df["shutdown_cost_g_per_shutdown"]
    ax.plot(x, df["rolling_starts"], marker="o", linewidth=2.2, color="#2563EB", label="Starts")
    ax.plot(x, df["rolling_shutdowns"], marker="s", linewidth=2.2, color="#B45309", label="Shutdowns")
    ax.set_xlabel("Shutdown penalty [g/shutdown]")
    ax.set_ylabel("Count")
    ax.set_title("Starts and Shutdowns vs Shutdown Penalty")
    ax.set_xticks(SHUTDOWN_COSTS)
    ax.grid(True, alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=True)
    path = PLOTS_DIR / "starts_shutdowns_vs_shutdown_cost.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def plot_march3(df: pd.DataFrame) -> Path:
    plot_df = df.copy()
    plot_df["continuous"] = plot_df["march3_continuous_genset_online"].map(
        lambda value: 1.0 if str(value).lower() == "true" else 0.0
    )
    plot_df["online_at_1745"] = plot_df["march3_online_at_1745"].map(
        lambda value: 1.0 if str(value).lower() == "true" else 0.0
    )

    fig, ax = plt.subplots(figsize=(7.8, 4.8), constrained_layout=True)
    x = plot_df["shutdown_cost_g_per_shutdown"]
    ax.plot(
        x,
        plot_df["march3_high_load_online_fraction"],
        marker="o",
        linewidth=2.2,
        color="#2563EB",
        label="Best online fraction",
    )
    ax.scatter(
        x[plot_df["continuous"] > 0.5],
        plot_df.loc[plot_df["continuous"] > 0.5, "march3_high_load_online_fraction"],
        marker="s",
        s=85,
        color="#059669",
        edgecolor="black",
        linewidth=0.8,
        label="Continuous through window",
        zorder=5,
    )
    ax.scatter(
        x[plot_df["online_at_1745"] > 0.5],
        [0.08] * int((plot_df["online_at_1745"] > 0.5).sum()),
        marker="^",
        s=70,
        color="#B45309",
        label="Online at 17:45",
        zorder=5,
    )
    ax.set_xlabel("Shutdown penalty [g/shutdown]")
    ax.set_ylabel("March 3 online indicator")
    ax.set_title("March 3 High-Load Window Continuity")
    ax.set_xticks(SHUTDOWN_COSTS)
    ax.set_ylim(-0.04, 1.04)
    ax.grid(True, alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=True)
    path = PLOTS_DIR / "march3_online_fraction_continuity.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def run_dispatch_plot(run_dir: Path) -> Path:
    completed = subprocess.run(
        ["python", "analysis/plot_rolling_horizon_run_panel.py", str(run_dir)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Dispatch plot failed for {run_dir}\n"
            f"STDOUT:\n{completed.stdout[-3000:]}\nSTDERR:\n{completed.stderr[-3000:]}"
        )
    for line in reversed(completed.stdout.splitlines()):
        if line.startswith("Saved "):
            return Path(line.replace("Saved ", "", 1).strip())
    raise RuntimeError(f"Could not parse plot output path:\n{completed.stdout}")


def generate_dispatch_plots(rows: list[dict[str, object]]) -> list[Path]:
    DISPATCH_PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for row in normalize_rows(rows):
        source = run_dispatch_plot(Path(str(row["run_dir"])))
        target = DISPATCH_PLOTS_DIR / f"{row['case_id']}_dispatch_panel{source.suffix}"
        shutil.copy2(source, target)
        copied.append(target)
    return copied


def generate_plots(rows: list[dict[str, object]]) -> tuple[list[Path], list[Path]]:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    numeric_cols = [
        "shutdown_cost_g_per_shutdown",
        "fuel_delta_vs_full_pct",
        "rolling_starts",
        "rolling_shutdowns",
        "final_soc_pct",
        "march3_high_load_online_fraction",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col])
    df = df.sort_values("shutdown_cost_g_per_shutdown")

    plot_paths = [
        plot_metric(
            df,
            "fuel_delta_vs_full_pct",
            "Fuel penalty vs full horizon [%]",
            "Fuel Penalty vs Shutdown Penalty",
            "fuel_penalty_vs_shutdown_cost.png",
        ),
        plot_starts_shutdowns(df),
        plot_metric(
            df,
            "final_soc_pct",
            "Final SOC [%]",
            "Final SOC vs Shutdown Penalty",
            "final_soc_vs_shutdown_cost.png",
        ),
        plot_march3(df),
    ]
    dispatch_paths = generate_dispatch_plots(rows)
    return plot_paths, dispatch_paths


def recommendation(rows: list[dict[str, object]]) -> tuple[str, dict[str, object] | None]:
    clean = [row for row in rows if is_clean(row)]
    baseline = next((row for row in clean if abs(as_float(row, "shutdown_cost_g_per_shutdown")) < 1e-9), None)
    if baseline is None:
        return "No clean zero-cost baseline exists, so the diagnostic is not interpretable.", None

    candidates = [
        row
        for row in clean
        if as_float(row, "shutdown_cost_g_per_shutdown") > 0.0
        and as_bool(row, "march3_continuous_genset_online")
        and as_bool(row, "march3_online_at_1745")
        and as_int(row, "rolling_starts") <= as_int(baseline, "rolling_starts")
        and as_float(row, "fuel_delta_vs_full_pct") <= as_float(baseline, "fuel_delta_vs_full_pct") + 0.25
    ]
    if not candidates:
        return (
            "Shutdown penalty did not produce a clearly better clean case under the diagnostic criteria. "
            "Keep it as a diagnostic only and do not change the H16 MA4 C500 P10k min_up6 baseline recommendation.",
            None,
        )

    selected = min(candidates, key=lambda row: as_float(row, "shutdown_cost_g_per_shutdown"))
    return (
        f"The smallest clean penalty that changes the March 3 premature-stop behavior is "
        f"{as_float(selected, 'shutdown_cost_g_per_shutdown'):.0f} g/shutdown. Treat this as useful "
        "evidence of shutdown myopia, but keep it diagnostic unless the thesis explicitly adopts a "
        "commitment-hysteresis term.",
        selected,
    )


def format_case(row: dict[str, object]) -> str:
    return (
        f"`{row['case_id']}`: shutdown penalty {as_float(row, 'shutdown_cost_g_per_shutdown'):.0f} g, "
        f"fuel {as_float(row, 'rolling_fuel_kg'):.2f} kg "
        f"({as_float(row, 'fuel_delta_vs_full_pct'):.2f}% vs full), "
        f"starts/shutdowns {as_int(row, 'rolling_starts')}/{as_int(row, 'rolling_shutdowns')}, "
        f"final SOC {as_float(row, 'final_soc_pct'):.2f}%, "
        f"March 3 fraction {as_float(row, 'march3_high_load_online_fraction'):.2f}, "
        f"continuous={as_bool(row, 'march3_continuous_genset_online')}, "
        f"online@17:45={as_bool(row, 'march3_online_at_1745')}"
    )


def write_assessment(rows: list[dict[str, object]], plot_paths: list[Path], dispatch_paths: list[Path]) -> None:
    clean = [row for row in rows if is_clean(row)]
    excluded = [row for row in rows if not is_clean(row)]
    rec_text, selected = recommendation(rows)

    lines = [
        "# Shutdown-Penalty Diagnostic",
        "",
        "Scope: targeted diagnostic only. Fixed setup is the selected H16 MA4 rolling-horizon candidate: operational 15-minute average load profile, moving-average forecast with MA4, startup cost 500 g/start, soft SOC band 20-80%, mean-normalized soft-SOC penalty 10000 g/kWh, min_up_time_steps=6, no terminal reserve, 30 s local solve limit, 564 kWh initial battery energy, and initial commitment [0, 0].",
        "",
        "The March 3 indicator uses the closed interval 2026-03-03 13:30 to 17:45. `continuous` means the same generator is online for every dispatch interval in that window; `online@17:45` means at least one generator is online at the endpoint.",
        "",
        "## Recommendation",
        "",
        rec_text,
        "",
    ]
    if selected is not None:
        lines.append(f"Selected diagnostic case: {format_case(selected)}.")
        lines.append("")

    lines.extend(
        [
            "This does not by itself replace the current H16 MA4 C500 P10k min_up6 baseline recommendation. The result should be described as a commitment-hysteresis / shutdown-myopia check, not as a broad thesis sensitivity sweep.",
            "",
            "## Case Table",
            "",
            "| Shutdown g | Clean | Fuel kg | Delta % | Starts | Shutdowns | Full starts | Full shutdowns | Min SOC % | Final SOC % | Run lengths | March 3 frac | Continuous | Online@17:45 | P95 solve s | Nonopt/time/infeas |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | --- | ---: | ---: |",
        ]
    )
    for row in normalize_rows(rows):
        lines.append(
            f"| {as_float(row, 'shutdown_cost_g_per_shutdown'):.0f} | {'yes' if is_clean(row) else 'no'} | "
            f"{as_float(row, 'rolling_fuel_kg'):.2f} | {as_float(row, 'fuel_delta_vs_full_pct'):.2f} | "
            f"{as_int(row, 'rolling_starts')} | {as_int(row, 'rolling_shutdowns')} | "
            f"{as_int(row, 'full_starts')} | {as_int(row, 'full_shutdowns')} | "
            f"{as_float(row, 'minimum_soc_pct'):.2f} | {as_float(row, 'final_soc_pct'):.2f} | "
            f"{row['run_lengths_steps']} | {as_float(row, 'march3_high_load_online_fraction'):.2f} | "
            f"{as_bool(row, 'march3_continuous_genset_online')} | {as_bool(row, 'march3_online_at_1745')} | "
            f"{as_float(row, 'p95_solve_s'):.3f} | "
            f"{as_int(row, 'nonoptimal_timeout_infeasible_local_solve_count')} |"
        )

    if excluded:
        lines.extend(["", "## Exclusions", ""])
        for row in excluded:
            reasons = []
            if as_bool(row, "physical_soc_violation"):
                reasons.append("physical SOC violation")
            if as_int(row, "nonoptimal_timeout_infeasible_local_solve_count") > 0:
                reasons.append(
                    f"{as_int(row, 'nonoptimal_timeout_infeasible_local_solve_count')} nonoptimal/time-limit/infeasible local solve(s)"
                )
            lines.append(f"- `{row['case_id']}`: {', '.join(reasons)}.")

    lines.extend(["", "## Generated Artifacts", ""])
    lines.append("- `summary.csv`")
    for path in plot_paths + dispatch_paths:
        lines.append(f"- `{path.relative_to(OUTPUT_DIR).as_posix()}`")
    lines.append("")

    (OUTPUT_DIR / "assessment.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    summary_path = OUTPUT_DIR / "summary.csv"
    rows: list[dict[str, object]] = [dict(row) for row in load_existing_rows(summary_path)]
    completed_cases = {str(row["case_id"]) for row in rows}

    if not args.plots_only:
        with open(BASE_CONFIG, "rb") as fh:
            base_config = tomllib.load(fh)

        for case in case_specs():
            case_id = str(case["case_id"])
            if case_id in completed_cases and not args.rerun_existing:
                print(f"Skipping existing {case_id}", flush=True)
                continue
            if args.rerun_existing:
                rows = [row for row in rows if str(row["case_id"]) != case_id]

            config = build_config(base_config, case)
            config_path = GENERATED_CONFIG_DIR / f"{case_id}.toml"
            write_rolling_config(config, config_path)
            verify_generated_config(config_path, case)

            print(f"Running {case_id}", flush=True)
            metadata, run_dir, wall_clock_s = run_case(config_path)
            row = summary_row(case, config_path, metadata, run_dir, wall_clock_s)
            rows.append(row)
            rows = normalize_rows(rows)
            write_csv(summary_path, rows)
            completed_cases.add(case_id)
            if abs(as_float(row, "shutdown_cost_g_per_shutdown")) < 1e-9:
                check_zero_case(rows)
            print(
                f"  fuel={as_float(row, 'rolling_fuel_kg'):.2f} kg, "
                f"delta={as_float(row, 'fuel_delta_vs_full_pct'):.2f}%, "
                f"starts/stops={as_int(row, 'rolling_starts')}/{as_int(row, 'rolling_shutdowns')}, "
                f"final SOC={as_float(row, 'final_soc_pct'):.2f}%, "
                f"march3={as_float(row, 'march3_high_load_online_fraction'):.2f}/"
                f"{as_bool(row, 'march3_continuous_genset_online')}/"
                f"{as_bool(row, 'march3_online_at_1745')}, "
                f"nonopt={as_int(row, 'nonoptimal_timeout_infeasible_local_solve_count')}, "
                f"run={run_dir}",
                flush=True,
            )

    rows = normalize_rows(refresh_derived_metrics(rows))
    check_zero_case(rows)
    write_csv(summary_path, rows)
    plot_paths, dispatch_paths = generate_plots(rows)
    write_assessment(rows, plot_paths, dispatch_paths)

    print(f"Saved {summary_path}", flush=True)
    print(f"Saved {OUTPUT_DIR / 'assessment.md'}", flush=True)
    for path in plot_paths + dispatch_paths:
        print(f"Saved {path}", flush=True)


if __name__ == "__main__":
    main()
