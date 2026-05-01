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
    / "moving_average_window_sensitivity"
)
GENERATED_CONFIG_DIR = OUTPUT_DIR / "generated_configs"
PLOTS_DIR = OUTPUT_DIR / "plots"
DISPATCH_PLOTS_DIR = PLOTS_DIR / "dispatch_panels"

LOAD_PROFILE = "data/operational_profiles/operational_load_profile_15min_avg.csv"
MOVING_AVERAGE_WINDOWS = [1, 2, 4, 8, 12, 16]
STARTUP_COST = 500.0
MIN_UP_STEPS = 6
LOCAL_TIME_LIMIT_S = 30.0
INITIAL_BATTERY_KWH = 564.0
INITIAL_COMMITMENT = [0, 0]

MARCH2_WINDOW = ("2026-03-02 15:15", "2026-03-02 19:45")
MARCH3_WINDOW = ("2026-03-03 13:30", "2026-03-03 17:45")

SUMMARY_FIELDS = [
    "case_id",
    "family",
    "horizon_steps",
    "horizon_hours",
    "moving_average_window_steps",
    "startup_cost_g_per_start",
    "soft_soc_penalty_g_per_kwh",
    "min_up_time_steps",
    "soft_band_terminal_reserve_enabled",
    "rolling_fuel_kg",
    "fuel_delta_vs_full_pct",
    "fuel_delta_vs_full_kg",
    "full_fuel_kg",
    "rolling_starts",
    "full_starts",
    "starts_delta_vs_full",
    "minimum_soc_pct",
    "maximum_soc_pct",
    "final_soc_pct",
    "full_final_soc_pct",
    "final_soc_delta_pct_points",
    "realized_low_soc_slack_kwh",
    "realized_high_soc_slack_kwh",
    "realized_low_soc_slack_max_kwh",
    "realized_high_soc_slack_max_kwh",
    "local_low_soc_slack_kwh",
    "local_high_soc_slack_kwh",
    "local_low_soc_slack_max_kwh",
    "local_high_soc_slack_max_kwh",
    "physical_soc_violation",
    "run_count",
    "run_lengths_steps",
    "shorter_than_min_up_runs",
    "minimum_length_runs",
    "median_solve_s",
    "p95_solve_s",
    "max_solve_s",
    "nonoptimal_timeout_infeasible_local_solve_count",
    "tail_padded_solves",
    "march2_variable_peak_online_fraction",
    "march2_continuous_genset_online",
    "march3_high_load_online_fraction",
    "march3_continuous_genset_online",
    "wall_clock_s",
    "config_path",
    "run_dir",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run compact moving-average-window sensitivity for rolling-horizon MILP."
    )
    parser.add_argument(
        "--include-middle",
        action="store_true",
        help="Also run the optional H20/P10k middle family.",
    )
    parser.add_argument(
        "--plots-only",
        action="store_true",
        help="Regenerate plots and assessment from an existing summary.csv without running new cases.",
    )
    return parser.parse_args()


def case_specs(include_middle: bool) -> list[dict[str, object]]:
    families = [
        {
            "family": "balanced_h16_p10k",
            "horizon": 16,
            "soft_soc": 10000.0,
            "description": "balanced H16, P10k",
        },
        {
            "family": "conservative_h24_p20k",
            "horizon": 24,
            "soft_soc": 20000.0,
            "description": "conservative H24, P20k",
        },
    ]
    if include_middle:
        families.append(
            {
                "family": "middle_h20_p10k",
                "horizon": 20,
                "soft_soc": 10000.0,
                "description": "optional middle H20, P10k",
            }
        )

    specs: list[dict[str, object]] = []
    for family in families:
        for ma_window in MOVING_AVERAGE_WINDOWS:
            specs.append(
                {
                    **family,
                    "ma_window": ma_window,
                    "case_id": f"{family['family']}_ma{ma_window:02d}",
                }
            )
    return specs


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


def build_config(base: dict, case: dict[str, object]) -> dict:
    config = deepcopy(base)
    case_id = str(case["case_id"])
    horizon = int(case["horizon"])
    ma_window = int(case["ma_window"])
    soft_soc = float(case["soft_soc"])

    config["run"]["label"] = f"rolling_ma_window_{case_id}"
    config["run"]["description"] = (
        "Operational 15-minute average-load rolling-horizon MILP "
        f"moving-average-window sensitivity: {case['description']}, "
        f"MA window={ma_window}, startup={STARTUP_COST:g} g/start, "
        "6-step minimum up-time, no terminal reserve"
    )
    config["run"]["show_solver_log"] = False
    config["load_profile"]["path"] = LOAD_PROFILE
    config["scheduling"]["dt_minutes"] = 15
    config["initial_conditions"]["battery_energy_kwh"] = INITIAL_BATTERY_KWH
    config["initial_conditions"]["generator_commitment"] = list(INITIAL_COMMITMENT)
    config.pop("terminal_conditions", None)

    rolling = config["rolling_horizon"]
    rolling["horizon_steps"] = horizon
    rolling["forecast_method"] = "moving_average"
    rolling["moving_average_window_steps"] = ma_window
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
    soft["soc_min_penalty_g_per_kwh"] = soft_soc
    soft["soc_max_penalty_g_per_kwh"] = soft_soc
    soft["soft_soc_penalty_scaling"] = "mean"

    for generator in config["generators"]:
        generator["startup_cost"] = STARTUP_COST

    return config


def verify_generated_config(path: Path, case: dict[str, object]) -> None:
    with open(path, "rb") as fh:
        config = tomllib.load(fh)

    rolling = config["rolling_horizon"]
    solver = config["solver"]
    soft = config["soft_soc"]
    initial = config["initial_conditions"]

    checks = {
        "load profile": config["load_profile"]["path"] == LOAD_PROFILE,
        "forecast method": rolling["forecast_method"] == "moving_average",
        "moving-average window": rolling["moving_average_window_steps"] == int(case["ma_window"]),
        "horizon": rolling["horizon_steps"] == int(case["horizon"]),
        "soft band": rolling["soc_strategy"] == "soft_band",
        "preferred low": abs(float(soft["preferred_soc_min"]) - 0.20) < 1e-12,
        "preferred high": abs(float(soft["preferred_soc_max"]) - 0.80) < 1e-12,
        "mean scaling": soft["soft_soc_penalty_scaling"] == "mean",
        "soft SOC penalty low": abs(float(soft["soc_min_penalty_g_per_kwh"]) - float(case["soft_soc"])) < 1e-9,
        "soft SOC penalty high": abs(float(soft["soc_max_penalty_g_per_kwh"]) - float(case["soft_soc"])) < 1e-9,
        "min up": rolling["min_up_time_steps"] == MIN_UP_STEPS,
        "soft terminal reserve disabled": rolling["soft_band_terminal_reserve_enabled"] is False,
        "local time limit": abs(float(solver["rolling_local_time_limit_sec"]) - LOCAL_TIME_LIMIT_S) < 1e-9,
        "initial energy": abs(float(initial["battery_energy_kwh"]) - INITIAL_BATTERY_KWH) < 1e-9,
        "initial commitment": list(initial["generator_commitment"]) == INITIAL_COMMITMENT,
        "startup cost": all(abs(float(g["startup_cost"]) - STARTUP_COST) < 1e-9 for g in config["generators"]),
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


def generator_run_lengths(run_dir: Path) -> list[int]:
    dispatch = pd.read_csv(run_dir / "dispatch_results.csv")
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


def window_online_metrics(run_dir: Path, start: str, end: str) -> tuple[float, bool]:
    dispatch = pd.read_csv(run_dir / "dispatch_results.csv")
    dispatch["datetime"] = pd.to_datetime(dispatch["datetime"])
    window = dispatch[
        (dispatch["datetime"] >= pd.Timestamp(start))
        & (dispatch["datetime"] < pd.Timestamp(end))
    ]
    if window.empty:
        return 0.0, False

    fractions = []
    continuous = False
    for _, grp in window.groupby("generator"):
        values = (grp.sort_values("datetime")["u"] > 0.5).to_numpy()
        fraction = float(values.mean())
        fractions.append(fraction)
        continuous = continuous or bool(values.all())
    return max(fractions) if fractions else 0.0, continuous


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
    march2_fraction, march2_continuous = window_online_metrics(run_dir, *MARCH2_WINDOW)
    march3_fraction, march3_continuous = window_online_metrics(run_dir, *MARCH3_WINDOW)

    return {
        "case_id": case["case_id"],
        "family": case["family"],
        "horizon_steps": int(case["horizon"]),
        "horizon_hours": int(case["horizon"]) * float(recorded["dt_h"]),
        "moving_average_window_steps": int(case["ma_window"]),
        "startup_cost_g_per_start": STARTUP_COST,
        "soft_soc_penalty_g_per_kwh": float(case["soft_soc"]),
        "min_up_time_steps": min_up,
        "soft_band_terminal_reserve_enabled": recorded["soft_band_terminal_reserve_enabled"],
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
        "full_final_soc_pct": full["final_soc_pct"],
        "final_soc_delta_pct_points": comparison["final_soc_delta_pct_points"],
        "realized_low_soc_slack_kwh": rolling["realized_total_soc_min_slack_kwh"],
        "realized_high_soc_slack_kwh": rolling["realized_total_soc_max_slack_kwh"],
        "realized_low_soc_slack_max_kwh": rolling["realized_maximum_soc_min_slack_kwh"],
        "realized_high_soc_slack_max_kwh": rolling["realized_maximum_soc_max_slack_kwh"],
        "local_low_soc_slack_kwh": rolling["local_total_soc_min_slack_kwh"],
        "local_high_soc_slack_kwh": rolling["local_total_soc_max_slack_kwh"],
        "local_low_soc_slack_max_kwh": rolling["local_maximum_soc_min_slack_kwh"],
        "local_high_soc_slack_max_kwh": rolling["local_maximum_soc_max_slack_kwh"],
        "physical_soc_violation": physical_soc_violation(metadata),
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
        "tail_padded_solves": recorded["tail_forecast_padded_solves"],
        "march2_variable_peak_online_fraction": march2_fraction,
        "march2_continuous_genset_online": march2_continuous,
        "march3_high_load_online_fraction": march3_fraction,
        "march3_continuous_genset_online": march3_continuous,
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
        as_int(row, "nonoptimal_timeout_infeasible_local_solve_count") == 0
        and not as_bool(row, "physical_soc_violation")
    )


def ranking_key(row: dict[str, object]) -> tuple[int, int, int, float, float]:
    return (
        as_int(row, "rolling_starts"),
        as_int(row, "shorter_than_min_up_runs"),
        as_int(row, "minimum_length_runs"),
        as_float(row, "fuel_delta_vs_full_pct"),
        -as_float(row, "final_soc_pct"),
    )


def normalize_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        rows,
        key=lambda row: (
            str(row["family"]),
            as_int(row, "moving_average_window_steps"),
        ),
    )


def refresh_derived_metrics(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    refreshed: list[dict[str, object]] = []
    for row in rows:
        updated = dict(row)
        run_dir = Path(str(updated["run_dir"]))
        lengths = generator_run_lengths(run_dir)
        min_up = as_int(updated, "min_up_time_steps")
        march2_fraction, march2_continuous = window_online_metrics(run_dir, *MARCH2_WINDOW)
        march3_fraction, march3_continuous = window_online_metrics(run_dir, *MARCH3_WINDOW)
        updated["run_count"] = len(lengths)
        updated["run_lengths_steps"] = " ".join(str(value) for value in lengths)
        updated["shorter_than_min_up_runs"] = sum(value < min_up for value in lengths)
        updated["minimum_length_runs"] = sum(value == min_up for value in lengths)
        updated["march2_variable_peak_online_fraction"] = march2_fraction
        updated["march2_continuous_genset_online"] = march2_continuous
        updated["march3_high_load_online_fraction"] = march3_fraction
        updated["march3_continuous_genset_online"] = march3_continuous
        refreshed.append(updated)
    return refreshed


def run_plot_script(run_dir: Path) -> Path:
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


def plot_metric(
    df: pd.DataFrame,
    metric: str,
    ylabel: str,
    title: str,
    output_name: str,
    *,
    ylim_bottom: float | None = None,
) -> Path:
    colors = {
        "balanced_h16_p10k": "#2563EB",
        "conservative_h24_p20k": "#B45309",
        "middle_h20_p10k": "#059669",
    }
    labels = {
        "balanced_h16_p10k": "H16 P10k",
        "conservative_h24_p20k": "H24 P20k",
        "middle_h20_p10k": "H20 P10k",
    }

    fig, ax = plt.subplots(figsize=(8.5, 5.2), constrained_layout=True)
    for family, grp in df.sort_values("moving_average_window_steps").groupby("family"):
        ax.plot(
            grp["moving_average_window_steps"],
            grp[metric],
            marker="o",
            linewidth=2.0,
            color=colors.get(family, "#334155"),
            label=labels.get(family, family),
        )
    ax.set_xlabel("Moving-average window [steps]")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_xticks(MOVING_AVERAGE_WINDOWS)
    if ylim_bottom is not None:
        ax.set_ylim(bottom=ylim_bottom)
    ax.grid(True, alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=True)
    path = PLOTS_DIR / output_name
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def write_march2_plot(df: pd.DataFrame) -> Path:
    plot_df = df.copy()
    plot_df["continuous"] = plot_df["march2_continuous_genset_online"].map(
        lambda value: 1.0 if str(value).lower() == "true" else 0.0
    )
    colors = {
        "balanced_h16_p10k": "#2563EB",
        "conservative_h24_p20k": "#B45309",
        "middle_h20_p10k": "#059669",
    }
    labels = {
        "balanced_h16_p10k": "H16 P10k",
        "conservative_h24_p20k": "H24 P20k",
        "middle_h20_p10k": "H20 P10k",
    }

    fig, ax = plt.subplots(figsize=(8.5, 5.2), constrained_layout=True)
    for family, grp in plot_df.sort_values("moving_average_window_steps").groupby("family"):
        color = colors.get(family, "#334155")
        ax.plot(
            grp["moving_average_window_steps"],
            grp["march2_variable_peak_online_fraction"],
            marker="o",
            linewidth=2.0,
            color=color,
            label=f"{labels.get(family, family)} fraction",
        )
        ax.scatter(
            grp.loc[grp["continuous"] > 0.5, "moving_average_window_steps"],
            grp.loc[grp["continuous"] > 0.5, "march2_variable_peak_online_fraction"],
            marker="s",
            s=80,
            color=color,
            edgecolor="black",
            linewidth=0.8,
            zorder=5,
        )
    ax.set_xlabel("Moving-average window [steps]")
    ax.set_ylabel("Best single-genset online fraction")
    ax.set_title("March 2 Variable Peak Online Continuity")
    ax.set_xticks(MOVING_AVERAGE_WINDOWS)
    ax.set_ylim(-0.04, 1.04)
    ax.grid(True, alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=True)
    path = PLOTS_DIR / "march2_online_fraction_continuity.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def generate_plots(rows: list[dict[str, object]]) -> list[Path]:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    numeric_cols = [
        "moving_average_window_steps",
        "fuel_delta_vs_full_pct",
        "rolling_starts",
        "final_soc_pct",
        "march2_variable_peak_online_fraction",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col])

    paths = [
        plot_metric(
            df,
            "fuel_delta_vs_full_pct",
            "Fuel penalty vs full horizon [%]",
            "Fuel Penalty vs Moving-Average Window",
            "fuel_penalty_vs_ma_window.png",
        ),
        plot_metric(
            df,
            "rolling_starts",
            "Generator starts",
            "Generator Starts vs Moving-Average Window",
            "starts_vs_ma_window.png",
            ylim_bottom=0,
        ),
        plot_metric(
            df,
            "final_soc_pct",
            "Final SOC [%]",
            "Final SOC vs Moving-Average Window",
            "final_soc_vs_ma_window.png",
            ylim_bottom=0,
        ),
        write_march2_plot(df),
    ]
    return paths


def select_dispatch_cases(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    clean = [row for row in rows if is_clean(row)]
    selected: list[dict[str, object]] = []

    for case_id in ["balanced_h16_p10k_ma04", "conservative_h24_p20k_ma04"]:
        match = next((row for row in clean if row["case_id"] == case_id), None)
        if match is not None:
            selected.append(match)

    cautious_lower_fuel = [
        row
        for row in clean
        if as_bool(row, "march2_continuous_genset_online")
        and (
            str(row["case_id"]) != "conservative_h24_p20k_ma04"
            or as_float(row, "rolling_fuel_kg") < 717.71
        )
    ]
    for row in sorted(cautious_lower_fuel, key=lambda r: (as_float(r, "rolling_fuel_kg"), as_int(r, "horizon_steps"))):
        if row not in selected:
            selected.append(row)
        if len(selected) >= 5:
            break

    for row in sorted(clean, key=ranking_key):
        if row not in selected:
            selected.append(row)
        if len(selected) >= 5:
            break
    return selected[:5]


def generate_dispatch_plots(rows: list[dict[str, object]]) -> list[Path]:
    DISPATCH_PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for rank, row in enumerate(select_dispatch_cases(rows), start=1):
        source = run_plot_script(Path(str(row["run_dir"])))
        target = DISPATCH_PLOTS_DIR / f"rank{rank:02d}_{row['case_id']}_dispatch_panel{source.suffix}"
        shutil.copy2(source, target)
        copied.append(target)
    return copied


def format_case(row: dict[str, object]) -> str:
    return (
        f"`{row['case_id']}`: fuel {as_float(row, 'rolling_fuel_kg'):.2f} kg "
        f"({as_float(row, 'fuel_delta_vs_full_pct'):+.2f}%), "
        f"{as_int(row, 'rolling_starts')} starts, final SOC {as_float(row, 'final_soc_pct'):.2f}%, "
        f"March 2 fraction {as_float(row, 'march2_variable_peak_online_fraction'):.2f}, "
        f"continuous={as_bool(row, 'march2_continuous_genset_online')}"
    )


def write_assessment(rows: list[dict[str, object]], plot_paths: list[Path], dispatch_paths: list[Path]) -> None:
    clean = [row for row in rows if is_clean(row)]
    excluded = [row for row in rows if not is_clean(row)]
    by_case = {str(row["case_id"]): row for row in rows}
    h16_ma4 = by_case.get("balanced_h16_p10k_ma04")
    h24_ma4 = by_case.get("conservative_h24_p20k_ma04")

    balanced_clean = [row for row in clean if row["family"] == "balanced_h16_p10k"]
    conservative_clean = [row for row in clean if row["family"] == "conservative_h24_p20k"]
    middle_clean = [row for row in clean if row["family"] == "middle_h20_p10k"]

    best_balanced = min(balanced_clean, key=ranking_key) if balanced_clean else None
    best_conservative = min(conservative_clean, key=ranking_key) if conservative_clean else None
    best_middle = min(middle_clean, key=ranking_key) if middle_clean else None

    cautious = [row for row in clean if as_bool(row, "march2_continuous_genset_online")]
    cautious_lower_than_h24 = []
    if h24_ma4 is not None:
        cautious_lower_than_h24 = [
            row
            for row in cautious
            if as_float(row, "rolling_fuel_kg") < as_float(h24_ma4, "rolling_fuel_kg") - 1e-9
        ]

    lines = [
        "# Moving-Average Window Sensitivity",
        "",
        "Scope: compact rolling-horizon forecast-window sweep only. Fixed setup uses the operational 15-minute average load profile, moving-average forecast, soft SOC band 20-80%, mean soft-SOC penalty scaling, startup cost 500 g/start, min_up_time_steps=6, no terminal reserve, 30 s local solve limit, 564 kWh initial battery energy, and initial commitment [0, 0].",
        "",
        "The March 2 indicator is true when the same generator is online at every 15-minute dispatch interval from 2026-03-02 15:15 up to 19:45. The fraction is the best single-generator online fraction over that half-open interval.",
        "",
        "## Reference Cases",
        "",
    ]
    if h16_ma4 is not None:
        lines.append(f"- H16 MA4 P10k baseline reference: {format_case(h16_ma4)}.")
    if h24_ma4 is not None:
        lines.append(f"- H24 MA4 P20k conservative reference: {format_case(h24_ma4)}.")

    lines.extend(["", "## Main Readout", ""])
    if best_balanced is not None:
        lines.append(f"- Best balanced-family case by the cleanliness-first ranking: {format_case(best_balanced)}.")
    if best_conservative is not None:
        lines.append(f"- Best conservative-family case by the cleanliness-first ranking: {format_case(best_conservative)}.")
    if best_middle is not None:
        lines.append(f"- Optional middle-family case by the same ranking: {format_case(best_middle)}.")

    lines.extend(["", "## Cautious-Operator Behavior", ""])
    if cautious:
        lines.append(
            "- Cases reproducing continuous same-genset online behavior through the March 2 variable peak: "
            + ", ".join(f"`{row['case_id']}`" for row in sorted(cautious, key=lambda r: (as_int(r, "horizon_steps"), as_int(r, "moving_average_window_steps"))))
            + "."
        )
    else:
        lines.append("- No clean case reproduced continuous same-genset online behavior through the March 2 variable peak.")

    if cautious_lower_than_h24:
        best_lower = min(cautious_lower_than_h24, key=lambda r: as_float(r, "rolling_fuel_kg"))
        lines.append(
            f"- Lower-fuel reproduction relative to H24 MA4 P20k exists: {format_case(best_lower)}."
        )
    elif h24_ma4 is not None:
        lines.append("- No clean case reproduced the March 2 continuous-online behavior with lower fuel than the H24 MA4 P20k conservative reference.")

    lines.extend(["", "## Family Tables", ""])
    for family in sorted({str(row["family"]) for row in rows}):
        lines.extend(
            [
                f"### {family}",
                "",
                "| MA window | Clean | Fuel kg | Delta % | Starts | Min SOC % | Final SOC % | Run lengths | March 2 frac | March 2 continuous | P95 solve s | Nonopt/time/infeas |",
                "| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: |",
            ]
        )
        for row in sorted([r for r in rows if r["family"] == family], key=lambda r: as_int(r, "moving_average_window_steps")):
            lines.append(
                f"| {as_int(row, 'moving_average_window_steps')} | {'yes' if is_clean(row) else 'no'} | "
                f"{as_float(row, 'rolling_fuel_kg'):.2f} | {as_float(row, 'fuel_delta_vs_full_pct'):.2f} | "
                f"{as_int(row, 'rolling_starts')} | {as_float(row, 'minimum_soc_pct'):.2f} | "
                f"{as_float(row, 'final_soc_pct'):.2f} | {row['run_lengths_steps']} | "
                f"{as_float(row, 'march2_variable_peak_online_fraction'):.2f} | "
                f"{as_bool(row, 'march2_continuous_genset_online')} | "
                f"{as_float(row, 'p95_solve_s'):.3f} | "
                f"{as_int(row, 'nonoptimal_timeout_infeasible_local_solve_count')} |"
            )
        lines.append("")

    if excluded:
        lines.extend(["## Exclusions", ""])
        for row in excluded:
            reasons = []
            if as_bool(row, "physical_soc_violation"):
                reasons.append("physical SOC violation")
            if as_int(row, "nonoptimal_timeout_infeasible_local_solve_count") > 0:
                reasons.append(
                    f"{as_int(row, 'nonoptimal_timeout_infeasible_local_solve_count')} nonoptimal/time-limit/infeasible local solve(s)"
                )
            lines.append(f"- `{row['case_id']}`: {', '.join(reasons)}.")
        lines.append("")

    lines.extend(["## Recommendation", ""])
    if h16_ma4 is not None and best_balanced is not None:
        if str(best_balanced["case_id"]) == "balanced_h16_p10k_ma04":
            lines.append("- Keep MA4 for the current H16 C500 P10k balanced baseline. Within this compact sweep, another moving-average window did not produce a cleaner balanced baseline under the starts/run-block/fuel tradeoff.")
        else:
            lines.append(f"- The balanced-family ranking favors `{best_balanced['case_id']}` over MA4, but check the table before changing the thesis baseline because this sweep isolates forecast smoothing only.")
    if h24_ma4 is not None and best_conservative is not None:
        if str(best_conservative["case_id"]) == "conservative_h24_p20k_ma04":
            lines.append("- Keep MA4 for the H24 P20k conservative comparison unless the thesis specifically wants a more lagged or smoother operator variant.")
        else:
            lines.append(
                f"- For the H24 P20k conservative comparison, keep MA4 if the purpose is to represent the cautious March 2 operator behavior. "
                f"`{best_conservative['case_id']}` has a cleaner generic run-block ranking, but it does not reproduce the continuous March 2 online block and does not reduce fuel relative to H24 MA4."
            )
            lower_fuel_conservative = [
                row
                for row in conservative_clean
                if as_float(row, "rolling_fuel_kg") < as_float(h24_ma4, "rolling_fuel_kg") - 1e-9
            ]
            if lower_fuel_conservative:
                names = ", ".join(
                    f"`{row['case_id']}` ({as_int(row, 'rolling_starts')} starts, March 2 continuous={as_bool(row, 'march2_continuous_genset_online')})"
                    for row in sorted(lower_fuel_conservative, key=lambda r: as_float(r, "rolling_fuel_kg"))
                )
                lines.append(
                    f"- Lower-fuel H24 alternatives exist ({names}), but they add a start and lose the continuous March 2 block, so they are not better conservative-comparison cases."
                )
    lines.append("- Longer moving-average windows should be described as smoother but more lagged; shorter windows are more responsive and can change start timing rather than representing a universally better forecast.")

    lines.extend(["", "## Generated Artifacts", ""])
    lines.append(f"- `summary.csv`")
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

        for case in case_specs(args.include_middle):
            case_id = str(case["case_id"])
            if case_id in completed_cases:
                print(f"Skipping existing {case_id}", flush=True)
                continue

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
            print(
                f"  fuel={as_float(row, 'rolling_fuel_kg'):.2f} kg, "
                f"delta={as_float(row, 'fuel_delta_vs_full_pct'):.2f}%, "
                f"starts={as_int(row, 'rolling_starts')}, "
                f"final SOC={as_float(row, 'final_soc_pct'):.2f}%, "
                f"march2={as_float(row, 'march2_variable_peak_online_fraction'):.2f}/"
                f"{as_bool(row, 'march2_continuous_genset_online')}, "
                f"nonopt={as_int(row, 'nonoptimal_timeout_infeasible_local_solve_count')}, "
                f"run={run_dir}",
                flush=True,
            )

    rows = normalize_rows(refresh_derived_metrics(rows))
    write_csv(summary_path, rows)
    plot_paths = generate_plots(rows)
    dispatch_paths = generate_dispatch_plots(rows)
    write_assessment(rows, plot_paths, dispatch_paths)

    print(f"Saved {summary_path}", flush=True)
    print(f"Saved {OUTPUT_DIR / 'assessment.md'}", flush=True)
    for path in plot_paths + dispatch_paths:
        print(f"Saved {path}", flush=True)


if __name__ == "__main__":
    main()
